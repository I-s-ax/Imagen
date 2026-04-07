#!/usr/bin/env python3
"""
Image Organizer CLI - Organizador de Imágenes con Reconocimiento Visual
Para Termux y sistemas Linux/Windows/Mac

Características:
- Detección de rostros (offline con OpenCV, online con Gemini)
- Reconocimiento de texto OCR
- Detección de objetos
- Búsqueda por imagen de ejemplo
- Búsqueda por nombre de archivo
- Modo offline y online
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
from concurrent.futures import ThreadPoolExecutor
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importaciones para procesamiento de imágenes
try:
    import cv2
    import numpy as np
    from PIL import Image
    import imagehash
    from sklearn.cluster import DBSCAN
    OFFLINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Modo offline limitado: {e}")
    OFFLINE_AVAILABLE = False

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

# Extensiones de imagen soportadas
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.tif'}


class ImageAnalyzer:
    """Analizador de imágenes con soporte offline y online."""
    
    def __init__(self, mode: str = 'offline', api_key: str = None):
        self.mode = mode
        self.api_key = api_key or os.environ.get('EMERGENT_LLM_KEY')
        self.face_cascade = None
        self.face_encodings_cache = {}
        
        if OFFLINE_AVAILABLE:
            # Cargar clasificador de rostros Haar Cascade
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Clasificador de ojos para mejor detección
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
    
    def load_image(self, image_path: str) -> Optional[np.ndarray]:
        """Cargar imagen usando OpenCV."""
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                # Intentar con PIL para formatos no soportados directamente
                pil_img = Image.open(image_path).convert('RGB')
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return img
        except Exception as e:
            logger.error(f"Error cargando imagen {image_path}: {e}")
            return None
    
    def detect_faces_offline(self, image_path: str) -> Dict:
        """Detectar rostros usando OpenCV (offline)."""
        img = self.load_image(image_path)
        if img is None:
            return {'has_faces': False, 'face_count': 0, 'faces': []}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detectar rostros
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        face_data = []
        for i, (x, y, w, h) in enumerate(faces):
            # Extraer región del rostro para crear encoding
            face_roi = gray[y:y+h, x:x+w]
            face_hash = self._compute_face_hash(face_roi)
            face_data.append({
                'id': i,
                'bbox': (x, y, w, h),
                'hash': face_hash
            })
        
        return {
            'has_faces': len(faces) > 0,
            'face_count': int(len(faces)),
            'faces': face_data
        }
    
    def _compute_face_hash(self, face_roi: np.ndarray) -> str:
        """Computar hash único para un rostro."""
        # Normalizar tamaño
        face_resized = cv2.resize(face_roi, (128, 128))
        # Crear hash basado en características
        pil_face = Image.fromarray(face_resized)
        return str(imagehash.phash(pil_face))
    
    def detect_text_offline(self, image_path: str) -> Dict:
        """Detectar si hay texto en la imagen (método heurístico)."""
        img = self.load_image(image_path)
        if img is None:
            return {'has_text': False, 'confidence': 0}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Aplicar umbral adaptativo para resaltar texto
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Buscar contornos que podrían ser texto
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filtrar contornos por características de texto
        text_like_contours = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = w / float(h) if h > 0 else 0
            area = cv2.contourArea(cnt)
            
            # Características típicas de caracteres de texto
            if 0.1 < aspect_ratio < 10 and 50 < area < 5000:
                text_like_contours += 1
        
        # Umbral para considerar que hay texto
        has_text = text_like_contours > 20
        confidence = min(text_like_contours / 100, 1.0)
        
        return {
            'has_text': has_text,
            'confidence': float(confidence),
            'text_regions': int(text_like_contours)
        }
    
    def analyze_image_content_offline(self, image_path: str) -> Dict:
        """Analizar contenido general de la imagen (offline)."""
        img = self.load_image(image_path)
        if img is None:
            return {'category': 'unknown', 'features': []}
        
        features = []
        
        # Analizar colores dominantes
        pixels = img.reshape(-1, 3)
        colors, counts = np.unique(pixels, axis=0, return_counts=True)
        dominant_colors = colors[counts.argsort()[-5:]]
        
        # Detectar si es mayormente un color (imagen simple)
        total_pixels = len(pixels)
        max_color_ratio = counts.max() / total_pixels
        
        if max_color_ratio > 0.7:
            features.append('solid_color')
        
        # Detectar bordes para objetos
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.count_nonzero(edges) / edges.size
        
        if edge_ratio > 0.1:
            features.append('complex_objects')
        elif edge_ratio > 0.02:
            features.append('simple_objects')
        else:
            features.append('minimal_content')
        
        return {
            'features': features,
            'edge_complexity': float(edge_ratio),
            'color_uniformity': float(max_color_ratio)
        }
    
    async def analyze_image_online(self, image_path: str) -> Dict:
        """Analizar imagen usando Gemini Vision (online)."""
        if not self.api_key:
            raise ValueError("API key requerida para modo online")
        
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
        
        # Determinar mime type
        ext = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')
        
        # Crear chat con Gemini
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"img-analysis-{hashlib.md5(image_path.encode()).hexdigest()[:8]}",
            system_message="""Eres un analizador de imágenes. Analiza la imagen y responde SOLO en formato JSON con esta estructura exacta:
{
    "has_faces": true/false,
    "face_count": número,
    "has_text": true/false,
    "text_content": "texto detectado o null",
    "has_people": true/false,
    "objects": ["lista", "de", "objetos"],
    "category": "rostros|texto|objetos|sin_personas|mixto",
    "description": "descripción breve"
}"""
        ).with_model("gemini", "gemini-2.5-flash")
        
        # Preparar imagen
        image_file = FileContentWithMimeType(
            file_path=str(image_path),
            mime_type=mime_type
        )
        
        # Enviar mensaje
        response = await chat.send_message(UserMessage(
            text="Analiza esta imagen y devuelve el JSON.",
            file_contents=[image_file]
        ))
        
        # Parsear respuesta JSON
        try:
            # Limpiar respuesta de markdown si existe
            response_text = response.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1]
                response_text = response_text.rsplit('```', 1)[0]
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {
                'has_faces': False,
                'has_text': False,
                'has_people': False,
                'objects': [],
                'category': 'unknown',
                'description': response,
                'raw_response': response
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
        self.face_groups = {}  # Agrupar rostros similares
    
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
            
            # Manejar nombres duplicados
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
                
                # Analizar rostros
                face_result = self.analyzer.detect_faces_offline(str(img_path))
                
                # Analizar texto
                text_result = self.analyzer.detect_text_offline(str(img_path))
                
                # Determinar categoría
                category = self._determine_category_offline(face_result, text_result)
                
                # Si hay rostros, agrupar por persona
                subcategory = None
                if category == 'rostros' and face_result['faces']:
                    subcategory = self._assign_face_group(face_result['faces'])
                
                # Mover imagen
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
                
                # Analizar con Gemini
                result = await self.analyzer.analyze_image_online(str(img_path))
                
                # Determinar categoría
                category = result.get('category', 'desconocido')
                if category not in ['rostros', 'texto', 'objetos', 'sin_personas', 'mixto']:
                    category = 'desconocido'
                
                # Si hay rostros, crear subcarpeta
                subcategory = None
                if category == 'rostros' and result.get('face_count', 0) > 0:
                    # Usar hash de imagen para agrupar
                    face_data = self.analyzer.detect_faces_offline(str(img_path))
                    if face_data['faces']:
                        subcategory = self._assign_face_group(face_data['faces'])
                
                # Mover imagen
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
            # Si no hay rostros, es sin_personas u objetos
            return 'sin_personas'
    
    def _assign_face_group(self, faces: List[Dict]) -> str:
        """Asignar grupo de rostro basado en similitud."""
        if not faces:
            return "persona_desconocida"
        
        # Usar el hash del primer rostro
        face_hash = faces[0].get('hash', '')
        if not face_hash:
            return "persona_desconocida"
        
        # Buscar grupo existente similar
        for group_name, group_hash in self.face_groups.items():
            if self.analyzer.compare_images(face_hash, group_hash, threshold=15):
                return group_name
        
        # Crear nuevo grupo
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
                        matches.append((img_path, distance))
                except:
                    continue
        
        # Ordenar por similitud (menor distancia = más similar)
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
        description='📷 Image Organizer - Organizador de Imágenes con IA',
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
    
    # Modo interactivo
    if args.interactive:
        run_interactive_mode()
        return
    
    if not args.folder:
        parser.print_help()
        print("\n❌ Error: Debes especificar una carpeta")
        sys.exit(1)
    
    # Verificar que la carpeta existe
    folder = Path(args.folder)
    if not folder.exists():
        print(f"❌ Error: La carpeta '{folder}' no existe")
        sys.exit(1)
    
    # Crear organizador
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
                for img, dist in matches[:20]:  # Mostrar máximo 20
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
