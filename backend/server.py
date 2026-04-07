from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import shutil
import asyncio
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Import image organizer
from image_organizer import ImageOrganizer, ImageAnalyzer, IMAGE_EXTENSIONS

# Create the main app
app = FastAPI(title="Image Organizer API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Storage for job progress
job_progress: Dict[str, Dict] = {}

# Models
class AnalysisJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    folder_path: str
    mode: str = "offline"
    status: str = "pending"
    progress: int = 0
    total: int = 0
    current_file: str = ""
    results: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class SearchRequest(BaseModel):
    folder_path: str
    search_type: str  # "example" or "name"
    example_image: Optional[str] = None  # base64 encoded
    name_pattern: Optional[str] = None
    threshold: int = 10
    move_results: bool = True

class SearchResult(BaseModel):
    matches: List[Dict]
    total_found: int
    moved: int = 0

class FolderInfo(BaseModel):
    path: str
    image_count: int
    categories: Dict[str, int]

# Routes
@api_router.get("/")
async def root():
    return {"message": "Image Organizer API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@api_router.post("/analyze")
async def start_analysis(
    background_tasks: BackgroundTasks,
    folder_path: str = Form(...),
    mode: str = Form("offline")
):
    """Iniciar análisis de carpeta de imágenes."""
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Carpeta no encontrada: {folder_path}")
    
    job_id = str(uuid.uuid4())
    job = AnalysisJob(
        id=job_id,
        folder_path=folder_path,
        mode=mode,
        status="processing"
    )
    
    # Save job to database
    job_dict = job.model_dump()
    job_dict['created_at'] = job_dict['created_at'].isoformat()
    await db.analysis_jobs.insert_one(job_dict)
    
    # Initialize progress
    job_progress[job_id] = {
        "status": "processing",
        "progress": 0,
        "total": 0,
        "current_file": ""
    }
    
    # Run analysis in background
    background_tasks.add_task(run_analysis, job_id, folder_path, mode)
    
    return {"job_id": job_id, "status": "processing"}

async def run_analysis(job_id: str, folder_path: str, mode: str):
    """Ejecutar análisis en segundo plano."""
    try:
        organizer = ImageOrganizer(folder_path, mode=mode)
        images = organizer.get_images()
        total = len(images)
        
        job_progress[job_id]["total"] = total
        
        def update_progress(current, total, filename):
            job_progress[job_id]["progress"] = current
            job_progress[job_id]["total"] = total
            job_progress[job_id]["current_file"] = filename
        
        if mode == "online":
            results = await organizer.organize_online(progress_callback=update_progress)
        else:
            results = organizer.organize_offline(progress_callback=update_progress)
        
        job_progress[job_id]["status"] = "completed"
        job_progress[job_id]["results"] = results
        
        # Update database
        await db.analysis_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "results": results,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Error in analysis job {job_id}: {e}")
        job_progress[job_id]["status"] = "error"
        job_progress[job_id]["error"] = str(e)
        
        await db.analysis_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "error": str(e)}}
        )

@api_router.get("/analyze/{job_id}")
async def get_analysis_status(job_id: str):
    """Obtener estado del análisis."""
    if job_id in job_progress:
        return job_progress[job_id]
    
    # Check database
    job = await db.analysis_jobs.find_one({"id": job_id}, {"_id": 0})
    if job:
        return job
    
    raise HTTPException(status_code=404, detail="Job no encontrado")

@api_router.post("/search", response_model=SearchResult)
async def search_images(request: SearchRequest):
    """Buscar imágenes por ejemplo o nombre."""
    folder = Path(request.folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    organizer = ImageOrganizer(str(folder))
    matches = []
    moved = 0
    
    if request.search_type == "example" and request.example_image:
        # Decode base64 image and save temporarily
        temp_path = Path("/tmp") / f"example_{uuid.uuid4()}.jpg"
        try:
            image_data = base64.b64decode(request.example_image)
            with open(temp_path, "wb") as f:
                f.write(image_data)
            
            results = organizer.search_by_example(str(temp_path), threshold=request.threshold)
            matches = [{"path": str(p), "distance": int(d), "similarity": float(100 - (d * 100 / 64))} 
                      for p, d in results]
            
            if request.move_results and results:
                moved = organizer.move_search_results(results, "similares_a_ejemplo")
        finally:
            if temp_path.exists():
                temp_path.unlink()
                
    elif request.search_type == "name" and request.name_pattern:
        results = organizer.search_by_name(request.name_pattern)
        matches = [{"path": str(p), "name": p.name} for p in results]
        
        if request.move_results and results:
            moved = organizer.move_search_results(results, f"busqueda_{request.name_pattern}")
    
    return SearchResult(
        matches=matches,
        total_found=len(matches),
        moved=moved
    )

@api_router.get("/folder/info")
async def get_folder_info(folder_path: str):
    """Obtener información de una carpeta."""
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    # Count images
    images = []
    for ext in IMAGE_EXTENSIONS:
        images.extend(folder.glob(f"*{ext}"))
        images.extend(folder.glob(f"*{ext.upper()}"))
    
    # Count by category (existing folders)
    categories = {}
    for subdir in folder.iterdir():
        if subdir.is_dir():
            count = sum(1 for _ in subdir.glob("*") if _.is_file())
            if count > 0:
                categories[subdir.name] = count
    
    return FolderInfo(
        path=str(folder.absolute()),
        image_count=len(images),
        categories=categories
    )

@api_router.get("/folder/images")
async def list_images(folder_path: str, limit: int = 50, offset: int = 0):
    """Listar imágenes de una carpeta."""
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    images = []
    for ext in IMAGE_EXTENSIONS:
        images.extend(folder.glob(f"*{ext}"))
        images.extend(folder.glob(f"*{ext.upper()}"))
    
    images = sorted(images)
    total = len(images)
    images = images[offset:offset + limit]
    
    return {
        "total": total,
        "images": [{"name": img.name, "path": str(img)} for img in images]
    }

@api_router.post("/analyze/single")
async def analyze_single_image(file: UploadFile = File(...), mode: str = Form("offline")):
    """Analizar una imagen individual."""
    # Save uploaded file temporarily
    temp_path = Path("/tmp") / f"upload_{uuid.uuid4()}_{file.filename}"
    
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        analyzer = ImageAnalyzer(mode=mode)
        
        result = {
            "filename": file.filename,
            "mode": mode
        }
        
        if mode == "online":
            analysis = await analyzer.analyze_image_online(str(temp_path))
            result["analysis"] = analysis
        else:
            # Offline analysis
            faces = analyzer.detect_faces_offline(str(temp_path))
            text = analyzer.detect_text_offline(str(temp_path))
            content_analysis = analyzer.analyze_image_content_offline(str(temp_path))
            
            result["analysis"] = {
                "faces": faces,
                "text": text,
                "content": content_analysis,
                "category": "rostros" if faces["has_faces"] else 
                           "texto" if text["has_text"] else "sin_personas"
            }
        
        return result
        
    finally:
        if temp_path.exists():
            temp_path.unlink()

@api_router.get("/jobs")
async def list_jobs(limit: int = 20):
    """Listar trabajos de análisis recientes."""
    jobs = await db.analysis_jobs.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"jobs": jobs}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
