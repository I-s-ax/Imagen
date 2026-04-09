#!/usr/bin/env python3
"""
Image Organizer CLI - Organizador de Imágenes con Reconocimiento Visual
Para Termux y sistemas Linux/Windows/Mac

Versión ligera compatible con Termux:
- Usa Pillow en lugar de OpenCV cuando no está disponible
- No requiere scikit-learn
- Detección de rostros y texto con métodos alternativos
"""

import os
import sys
import argparse
import shutil
import hashlib
import json
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importaciones básicas (siempre disponibles)
from PIL import Image, ImageFilter, ImageStat
import imagehash

# Intentar importar OpenCV (opcional)
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
    logger.info("OpenCV disponible - usando detección avanzada")
except ImportError:
    OPENCV_AVAILABLE = False
    logger.info("OpenCV no disponible - usando detección con Pillow")

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass  # dotenv es opcional

# Extensiones de imagen soportadas
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.tif'}


class ImageAnalyzer:
    """Analizador de imágenes con soporte offline y online."""
    
    def __init__(self, mode: str = 'offline', api_key: str = None):
        self.mode = mode
        self.api_key = api_key or os.environ.get('EMERGENT_LLM_KEY')
        self.face_cascade = None
        self.face_encodings_cache = {}
        
        # Cargar clasificador de rostros solo si OpenCV está disponible
        if OPENCV_AVAILABLE:
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                self.eye_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_eye.xml'
                )
            except Exception as e:
                logger.warning(f"No se pudo cargar Haar Cascade: {e}")
    
    def load_image_pil(self, image_path: str) -> Optional[Image.Image]:
        """Cargar imagen usando Pillow."""
        try:
            return Image.open(image_path).convert('RGB')
        except Exception as e:
            logger.error(f"Error cargando imagen {image_path}: {e}")
            return None
    
    def load_image_cv2(self, image_path: str):
        """Cargar imagen usando OpenCV (si está disponible)."""
        if not OPENCV_AVAILABLE:
            return None
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                # Fallback con PIL
                pil_img = Image.open(image_path).convert('RGB')
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return img
        except Exception as e:
            logger.error(f"Error cargando imagen con OpenCV {image_path}: {e}")
            return None
    
    def detect_faces_offline(self, image_path: str) -> Dict:
        """Detectar rostros - usa OpenCV si disponible, sino método alternativo."""
        
        # Método 1: OpenCV (más preciso)
        if OPENCV_AVAILABLE and self.face_cascade is not None:
            return self._detect_faces_opencv(image_path)
        
        # Método 2: Detección heurística con Pillow (fallback)
        return self._detect_faces_heuristic(image_path)
    
    def _detect_faces_opencv(self, image_path: str) -> Dict:
        """Detectar rostros usando OpenCV."""
        img = self.load_image_cv2(image_path)
        if img is None:
            return {'has_faces': False, 'face_count': 0, 'faces': []}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        # Detectar rostros
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(20, 20),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Intentar con cascade alternativo si no encuentra
        if len(faces) == 0:
            try:
                alt_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'
                )
                faces = alt_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20)
                )
            except:
                pass
        
        face_data = []
        for i, (x, y, w, h) in enumerate(faces):
            face_roi = gray[y:y+h, x:x+w]
            face_hash = self._compute_face_hash_cv2(face_roi)
            face_data.append({
                'id': i,
                'bbox': [int(x), int(y), int(w), int(h)],
                'hash': face_hash
            })
        
        return {
            'has_faces': len(faces) > 0,
            'face_count': int(len(faces)),
            'faces': face_data
        }
    
    def _detect_faces_heuristic(self, image_path: str) -> Dict:
        """Detección heurística de rostros usando Pillow (fallback)."""
        img = self.load_image_pil(image_path)
        if img is None:
            return {'has_faces': False, 'face_count': 0, 'faces': []}
        
        # Análisis de colores de piel típicos
        skin_pixels = 0
        total_pixels = 0
        
        # Reducir tamaño para análisis más rápido
        img_small = img.resize((100, 100))
        pixels = list(img_small.getdata())
        
        for r, g, b in pixels:
            total_pixels += 1
            # Rango de colores de piel (aproximado)
            if self._is_skin_color(r, g, b):
                skin_pixels += 1
        
        skin_ratio = skin_pixels / total_pixels if total_pixels > 0 else 0
        
        # Si hay suficiente color de piel, probablemente hay rostros
        has_faces = skin_ratio > 0.15
        face_count = 1 if has_faces else 0
        
        face_data = []
        if has_faces:
            face_hash = str(imagehash.phash(img))
            face_data.append({
                'id': 0,
                'bbox': [0, 0, img.width, img.height],
                'hash': face_hash
            })
        
        return {
            'has_faces': has_faces,
            'face_count': face_count,
            'faces': face_data,
            'method': 'heuristic',
            'skin_ratio': round(skin_ratio, 3)
        }
    
    def _is_skin_color(self, r: int, g: int, b: int) -> bool:
        """Determinar si un color RGB es tono de piel."""
        # Reglas para detectar tonos de piel (varios tonos)
        if r > 95 and g > 40 and b > 20:
            if max(r, g, b) - min(r, g, b) > 15:
                if abs(r - g) > 15 and r > g and r > b:
                    return True
        # Tonos más oscuros
        if r > 60 and g > 40 and b > 30:
            if r > g > b:
                return True
        return False
    
    def _compute_face_hash_cv2(self, face_roi) -> str:
        """Computar hash de rostro con OpenCV."""
        face_resized = cv2.resize(face_roi, (128, 128))
        pil_face = Image.fromarray(face_resized)
        return str(imagehash.phash(pil_face))
    
    def detect_text_offline(self, image_path: str) -> Dict:
        """Detectar si hay texto en la imagen."""
        
        if OPENCV_AVAILABLE:
            return self._detect_text_opencv(image_path)
        
        return self._detect_text_pillow(image_path)
    
    def _detect_text_opencv(self, image_path: str) -> Dict:
        """Detectar texto usando OpenCV."""
        img = self.load_image_cv2(image_path)
        if img is None:
            return {'has_text': False, 'confidence': 0}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Umbral adaptativo para resaltar texto
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Buscar contornos
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        text_like_contours = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = w / float(h) if h > 0 else 0
            area = cv2.contourArea(cnt)
            
            if 0.1 < aspect_ratio < 10 and 50 < area < 5000:
                text_like_contours += 1
        
        has_text = text_like_contours > 20
        confidence = min(text_like_contours / 100, 1.0)
        
        return {
            'has_text': has_text,
            'confidence': float(round(confidence, 3)),
            'text_regions': int(text_like_contours)
        }
    
    def _detect_text_pillow(self, image_path: str) -> Dict:
        """Detectar texto usando Pillow (análisis de contraste)."""
        img = self.load_image_pil(image_path)
        if img is None:
            return {'has_text': False, 'confidence': 0}
        
        # Convertir a escala de grises
        gray = img.convert('L')
        
        # Detectar bordes (texto tiene muchos bordes nítidos)
        edges = gray.filter(ImageFilter.FIND_EDGES)
        
        # Calcular estadísticas de la imagen de bordes
        stat = ImageStat.Stat(edges)
        edge_mean = stat.mean[0]
        edge_stddev = stat.stddev[0]
        
        # Alto contraste y muchos bordes = probablemente texto
        has_text = edge_mean > 30 and edge_stddev > 40
        confidence = min((edge_mean / 100) * (edge_stddev / 60), 1.0)
        
        return {
            'has_text': has_text,
            'confidence': float(round(confidence, 3)),
            'method': 'pillow',
            'edge_mean': float(round(edge_mean, 2)),
            'edge_stddev': float(round(edge_stddev, 2))
        }
    
    def analyze_image_content_offline(self, image_path: str) -> Dict:
        """Analizar contenido general de la imagen."""
        img = self.load_image_pil(image_path)
        if img is None:
            return {'category': 'unknown', 'features': []}
        
        features = []
        
        # Analizar colores dominantes
        img_small = img.resize((50, 50))
        colors = img_small.getcolors(2500)
        
        if colors:
            colors.sort(key=lambda x: x[0], reverse=True)
            total = sum(c[0] for c in colors)
            top_ratio = colors[0][0] / total if total > 0 else 0
            
            if top_ratio > 0.7:
                features.append('solid_color')
        
        # Detectar complejidad
        edges = img.convert('L').filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)
        complexity = stat.mean[0]
        
        if complexity > 50:
            features.append('complex_objects')
        elif complexity > 15:
            features.append('simple_objects')
        else:
            features.append('minimal_content')
        
        return {
            'features': features,
            'complexity': float(round(complexity, 2))
        }
    
    async def analyze_image_online(self, image_path: str) -> Dict:
        """Analizar imagen usando Gemini Vision (online)."""
        if not self.api_key:
            raise ValueError("API key requerida para modo online")
        
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
        
        ext = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"img-{hashlib.md5(image_path.encode()).hexdigest()[:8]}",
            system_message="""Analiza la imagen y responde SOLO en JSON:
{
    "has_faces": true/false,
    "face_count": número,
    "has_text": true/false,
    "has_people": true/false,
    "objects": ["lista"],
    "category": "rostros|texto|objetos|sin_personas|mixto",
    "description": "descripción breve"
}"""
        ).with_model("gemini", "gemini-2.5-flash")
        
        image_file = FileContentWithMimeType(
            file_path=str(image_path),
            mime_type=mime_type
        )
        
        response = await chat.send_message(UserMessage(
            text="Analiza esta imagen y devuelve el JSON.",
            file_contents=[image_file]
        ))
        
        try:
            response_text = response.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1]
                response_text = response_text.rsplit('```', 1)[0]
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {
                'has_faces': False, 'has_text': False, 'has_people': False,
                'objects': [], 'category': 'unknown',
                'description': response, 'raw_response': response
            }
    
    def compute_image_hash(self, image_path: str) -> str:
        """Computar hash perceptual de una imagen."""
        try:
            img = Image.open(image_path)
            return str(imagehash.phash(img))
        except Exception as e:
            logger.error(f"Error computando hash: {e}")
            return ""
    
    def compare_images(self, hash1: str, hash2: str, threshold: int = 10) -> bool:
        """Comparar dos imágenes por su hash perceptual."""
        if not hash1 or not hash2:
            return False
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return abs(h1 - h2) <= threshold
        except:
            return False


class ImageOrganizer:
    """Organizador principal de imágenes."""
    
    def __init__(self, source_dir: str, mode: str = 'offline', api_key: str = None):
        self.source_dir = Path(source_dir)
        self.mode = mode
        self.analyzer = ImageAnalyzer(mode=mode, api_key=api_key)
        self.results = {
            'processed': 0,
            'moved': 0,
            'errors': 0,
            'categories': {}
        }
        self.face_groups = {}
    
    def get_images(self) -> List[Path]:
        """Obtener todas las imágenes del directorio."""
        images = []
        for ext in IMAGE_EXTENSIONS:
            images.extend(self.source_dir.glob(f'*{ext}'))
            images.extend(self.source_dir.glob(f'*{ext.upper()}'))
        return sorted(images)
    
    def create_category_folders(self):
        """Crear carpetas de categorías."""
        categories = ['rostros', 'texto', 'objetos', 'sin_personas', 'mixto', 'desconocido']
        for cat in categories:
            folder = self.source_dir / cat
            folder.mkdir(exist_ok=True)
    
    def move_image(self, image_path: Path, category: str, subcategory: str = None) -> bool:
        """Mover imagen a la carpeta correspondiente."""
        try:
            dest_folder = self.source_dir / category
            if subcategory:
                dest_folder = dest_folder / subcategory
            dest_folder.mkdir(parents=True, exist_ok=True)
            
            dest_path = dest_folder / image_path.name
            
            counter = 1
            while dest_path.exists():
                stem = image_path.stem
                suffix = image_path.suffix
                dest_path = dest_folder / f"{stem}_{counter}{suffix}"
                counter += 1
            
            shutil.move(str(image_path), str(dest_path))
            logger.info(f"Movido: {image_path.name} -> {category}/{subcategory or ''}")
            return True
        except Exception as e:
            logger.error(f"Error moviendo {image_path}: {e}")
            return False
    
    def organize_offline(self, progress_callback=None):
        """Organizar imágenes usando análisis offline."""
        self.create_category_folders()
        images = self.get_images()
        total = len(images)
        
        logger.info(f"Procesando {total} imágenes en modo offline...")
        
        for i, img_path in enumerate(images):
            try:
                if progress_callback:
                    progress_callback(i + 1, total, img_path.name)
                
                face_result = self.analyzer.detect_faces_offline(str(img_path))
                text_result = self.analyzer.detect_text_offline(str(img_path))
                
                category = self._determine_category_offline(face_result, text_result)
                
                subcategory = None
                if category == 'rostros' and face_result.get('faces'):
                    subcategory = self._assign_face_group(face_result['faces'])
                
                if self.move_image(img_path, category, subcategory):
                    self.results['moved'] += 1
                    self.results['categories'][category] = self.results['categories'].get(category, 0) + 1
                
                self.results['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error procesando {img_path}: {e}")
                self.results['errors'] += 1
        
        return self.results
    
    async def organize_online(self, progress_callback=None):
        """Organizar imágenes usando análisis online (Gemini)."""
        self.create_category_folders()
        images = self.get_images()
        total = len(images)
        
        logger.info(f"Procesando {total} imágenes en modo online...")
        
        for i, img_path in enumerate(images):
            try:
                if progress_callback:
                    progress_callback(i + 1, total, img_path.name)
                
                result = await self.analyzer.analyze_image_online(str(img_path))
                
                category = result.get('category', 'desconocido')
                if category not in ['rostros', 'texto', 'objetos', 'sin_personas', 'mixto']:
                    category = 'desconocido'
                
                subcategory = None
                if category == 'rostros' and result.get('face_count', 0) > 0:
                    face_data = self.analyzer.detect_faces_offline(str(img_path))
                    if face_data.get('faces'):
                        subcategory = self._assign_face_group(face_data['faces'])
                
                if self.move_image(img_path, category, subcategory):
                    self.results['moved'] += 1
                    self.results['categories'][category] = self.results['categories'].get(category, 0) + 1
                
                self.results['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error procesando {img_path}: {e}")
                self.results['errors'] += 1
        
        return self.results
    
    def _determine_category_offline(self, face_result: Dict, text_result: Dict) -> str:
        """Determinar categoría basada en análisis offline."""
        has_faces = face_result.get('has_faces', False)
        has_text = text_result.get('has_text', False) and text_result.get('confidence', 0) > 0.3
        
        if has_faces and has_text:
            return 'mixto'
        elif has_faces:
            return 'rostros'
        elif has_text:
            return 'texto'
        else:
            return 'sin_personas'
    
    def _assign_face_group(self, faces: List[Dict]) -> str:
        """Asignar grupo de rostro basado en similitud."""
        if not faces:
            return "persona_desconocida"
        
        face_hash = faces[0].get('hash', '')
        if not face_hash:
            return "persona_desconocida"
        
        for group_name, group_hash in self.face_groups.items():
            if self.analyzer.compare_images(face_hash, group_hash, threshold=15):
                return group_name
        
        group_num = len(self.face_groups) + 1
        group_name = f"persona_{group_num}"
        self.face_groups[group_name] = face_hash
        return group_name
    
    def search_by_example(self, example_path: str, threshold: int = 10) -> List[Tuple[Path, int]]:
        """Buscar imágenes similares a una imagen de ejemplo."""
        example_hash = self.analyzer.compute_image_hash(example_path)
        if not example_hash:
            logger.error("No se pudo computar hash de la imagen de ejemplo")
            return []
        
        images = self.get_images()
        matches = []
        
        logger.info(f"Buscando imágenes similares a {example_path}...")
        
        for img_path in images:
            img_hash = self.analyzer.compute_image_hash(str(img_path))
            if img_hash:
                try:
                    h1 = imagehash.hex_to_hash(example_hash)
                    h2 = imagehash.hex_to_hash(img_hash)
                    distance = abs(h1 - h2)
                    if distance <= threshold:
                        matches.append((img_path, int(distance)))
                except:
                    continue
        
        matches.sort(key=lambda x: x[1])
        return matches
    
    def search_by_name(self, pattern: str) -> List[Path]:
        """Buscar imágenes por nombre de archivo."""
        images = self.get_images()
        matches = []
        pattern_lower = pattern.lower()
        
        for img_path in images:
            if pattern_lower in img_path.name.lower():
                matches.append(img_path)
        
        return matches
    
    def move_search_results(self, matches: List, dest_folder: str = 'similares'):
        """Mover resultados de búsqueda a una carpeta."""
        dest = self.source_dir / dest_folder
        dest.mkdir(exist_ok=True)
        
        moved = 0
        for item in matches:
            if isinstance(item, tuple):
                img_path, _ = item
            else:
                img_path = item
            
            try:
                dest_path = dest / img_path.name
                counter = 1
                while dest_path.exists():
                    stem = img_path.stem
                    suffix = img_path.suffix
                    dest_path = dest / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                shutil.move(str(img_path), str(dest_path))
                moved += 1
                logger.info(f"Movido: {img_path.name} -> {dest_folder}/")
            except Exception as e:
                logger.error(f"Error moviendo {img_path}: {e}")
        
        return moved


def progress_bar(current: int, total: int, filename: str):
    """Mostrar barra de progreso en terminal."""
    percent = current * 100 // total
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f'\r[{bar}] {percent}% ({current}/{total}) - {filename[:30]}', end='', flush=True)


def main():
    """Función principal CLI."""
    parser = argparse.ArgumentParser(
        description='📷 Image Organizer - Organizador de Imágenes (Compatible con Termux)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Organizar carpeta en modo offline
  python image_organizer.py /ruta/carpeta --mode offline
  
  # Organizar con IA online (Gemini)
  python image_organizer.py /ruta/carpeta --mode online
  
  # Buscar imágenes similares a una de ejemplo
  python image_organizer.py /ruta/carpeta --example /ruta/imagen.jpg
  
  # Buscar por nombre de archivo
  python image_organizer.py /ruta/carpeta --name "vacaciones"
  
  # Modo interactivo
  python image_organizer.py --interactive

Dependencias mínimas (Termux):
  pip install pillow imagehash
  
Dependencias opcionales (mejor detección):
  pip install opencv-python
        """
    )
    
    parser.add_argument('folder', nargs='?', help='Carpeta con imágenes a analizar')
    parser.add_argument('--mode', '-m', choices=['offline', 'online', 'hybrid'],
                        default='offline', help='Modo de análisis (default: offline)')
    parser.add_argument('--example', '-e', help='Imagen de ejemplo para búsqueda por similitud')
    parser.add_argument('--name', '-n', help='Patrón de nombre para búsqueda')
    parser.add_argument('--threshold', '-t', type=int, default=10,
                        help='Umbral de similitud (0-64, menor=más estricto, default: 10)')
    parser.add_argument('--move-results', '-r', action='store_true',
                        help='Mover resultados de búsqueda a carpeta')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Modo interactivo')
    parser.add_argument('--api-key', '-k', help='API key para modo online')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Mostrar información detallada')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Mostrar info de dependencias
    print(f"\n📦 OpenCV: {'✅ Disponible' if OPENCV_AVAILABLE else '❌ No disponible (usando Pillow)'}")
    
    if args.interactive:
        run_interactive_mode()
        return
    
    if not args.folder:
        parser.print_help()
        print("\n❌ Error: Debes especificar una carpeta")
        sys.exit(1)
    
    folder = Path(args.folder)
    if not folder.exists():
        print(f"❌ Error: La carpeta '{folder}' no existe")
        sys.exit(1)
    
    organizer = ImageOrganizer(
        source_dir=str(folder),
        mode=args.mode,
        api_key=args.api_key
    )
    
    # Búsqueda por imagen de ejemplo
    if args.example:
        print(f"\n🔍 Buscando imágenes similares a: {args.example}")
        matches = organizer.search_by_example(args.example, threshold=args.threshold)
        
        if matches:
            print(f"\n✅ Encontradas {len(matches)} imágenes similares:\n")
            for img_path, distance in matches:
                similarity = 100 - (distance * 100 / 64)
                print(f"  📷 {img_path.name} (similitud: {similarity:.1f}%)")
            
            if args.move_results:
                moved = organizer.move_search_results(matches, 'similares_a_ejemplo')
                print(f"\n📁 Movidas {moved} imágenes a 'similares_a_ejemplo/'")
        else:
            print("❌ No se encontraron imágenes similares")
        return
    
    # Búsqueda por nombre
    if args.name:
        print(f"\n🔍 Buscando imágenes con nombre: '{args.name}'")
        matches = organizer.search_by_name(args.name)
        
        if matches:
            print(f"\n✅ Encontradas {len(matches)} imágenes:\n")
            for img_path in matches:
                print(f"  📷 {img_path}")
            
            if args.move_results:
                moved = organizer.move_search_results(matches, f'busqueda_{args.name}')
                print(f"\n📁 Movidas {moved} imágenes a 'busqueda_{args.name}/'")
        else:
            print("❌ No se encontraron imágenes con ese nombre")
        return
    
    # Organizar imágenes
    print(f"\n📷 Image Organizer - Modo: {args.mode.upper()}")
    print(f"📁 Carpeta: {folder.absolute()}")
    print("-" * 50)
    
    if args.mode == 'online' or args.mode == 'hybrid':
        import asyncio
        results = asyncio.run(organizer.organize_online(progress_callback=progress_bar))
    else:
        results = organizer.organize_offline(progress_callback=progress_bar)
    
    print("\n\n" + "=" * 50)
    print("📊 RESUMEN:")
    print(f"  Total procesadas: {results['processed']}")
    print(f"  Movidas: {results['moved']}")
    print(f"  Errores: {results['errors']}")
    print("\n📁 Por categoría:")
    for cat, count in results['categories'].items():
        print(f"  {cat}: {count}")
    print("=" * 50)


def run_interactive_mode():
    """Ejecutar en modo interactivo."""
    print("\n" + "=" * 50)
    print("  📷 IMAGE ORGANIZER - Modo Interactivo")
    print("=" * 50)
    
    while True:
        print("\n¿Qué deseas hacer?")
        print("  1. Organizar imágenes por categoría")
        print("  2. Buscar por imagen de ejemplo")
        print("  3. Buscar por nombre de archivo")
        print("  4. Salir")
        
        choice = input("\nOpción (1-4): ").strip()
        
        if choice == '1':
            folder = input("📁 Carpeta a analizar: ").strip()
            if not Path(folder).exists():
                print("❌ La carpeta no existe")
                continue
            
            print("\nModo de análisis:")
            print("  1. Offline (rápido, sin internet)")
            print("  2. Online (preciso, requiere internet)")
            mode_choice = input("Opción (1-2): ").strip()
            mode = 'online' if mode_choice == '2' else 'offline'
            
            organizer = ImageOrganizer(folder, mode=mode)
            
            if mode == 'online':
                import asyncio
                results = asyncio.run(organizer.organize_online(progress_callback=progress_bar))
            else:
                results = organizer.organize_offline(progress_callback=progress_bar)
            
            print(f"\n\n✅ Completado: {results['moved']} imágenes organizadas")
            
        elif choice == '2':
            folder = input("📁 Carpeta donde buscar: ").strip()
            example = input("🖼️  Imagen de ejemplo: ").strip()
            
            if not Path(folder).exists() or not Path(example).exists():
                print("❌ Carpeta o imagen no existe")
                continue
            
            threshold = input("Umbral de similitud (1-64, default 10): ").strip()
            threshold = int(threshold) if threshold else 10
            
            organizer = ImageOrganizer(folder)
            matches = organizer.search_by_example(example, threshold=threshold)
            
            if matches:
                print(f"\n✅ Encontradas {len(matches)} imágenes similares:")
                for img, dist in matches[:20]:
                    print(f"  📷 {img.name} (distancia: {dist})")
                
                move = input("\n¿Mover a carpeta 'similares'? (s/n): ").strip().lower()
                if move == 's':
                    organizer.move_search_results(matches)
                    print("✅ Imágenes movidas")
            else:
                print("❌ No se encontraron imágenes similares")
                
        elif choice == '3':
            folder = input("📁 Carpeta donde buscar: ").strip()
            pattern = input("🔍 Patrón de nombre: ").strip()
            
            if not Path(folder).exists():
                print("❌ La carpeta no existe")
                continue
            
            organizer = ImageOrganizer(folder)
            matches = organizer.search_by_name(pattern)
            
            if matches:
                print(f"\n✅ Encontradas {len(matches)} imágenes:")
                for img in matches[:20]:
                    print(f"  📷 {img}")
                
                move = input(f"\n¿Mover a carpeta 'busqueda_{pattern}'? (s/n): ").strip().lower()
                if move == 's':
                    organizer.move_search_results(matches, f'busqueda_{pattern}')
                    print("✅ Imágenes movidas")
            else:
                print("❌ No se encontraron imágenes")
                
        elif choice == '4':
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida")


if __name__ == '__main__':
    main()
