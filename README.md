# 📷 Image Organizer - Organizador de Imágenes con IA

Un organizador de imágenes inteligente diseñado para funcionar en **Termux** y cualquier sistema con Python. Detecta rostros, texto, objetos y organiza automáticamente tus imágenes en carpetas.

## ✨ Características

- 🔍 **Detección de rostros** - Detecta y agrupa personas similares
- 📝 **Reconocimiento de texto** - Identifica imágenes con texto
- 📦 **Detección de objetos** - Clasifica imágenes por contenido
- 🖼️ **Búsqueda por imagen de ejemplo** - Encuentra imágenes similares
- 🔎 **Búsqueda por nombre** - Busca por nombre de archivo
- 📱 **Compatible con Termux** - Funciona en Android
- 🌐 **Modo offline y online** - Sin internet (OpenCV) o con IA (Gemini)

## 📁 Estructura de Organización

```
/tu_carpeta/
├── rostros/
│   ├── persona_1/
│   ├── persona_2/
│   └── ...
├── texto/
├── objetos/
├── sin_personas/
├── mixto/
└── similares_a_ejemplo/
```

## 🚀 Instalación

### En Termux (Android)

```bash
# Actualizar paquetes
pkg update && pkg upgrade

# Instalar Python
pkg install python python-pip

# Instalar dependencias
pip install opencv-python-headless pillow imagehash scikit-learn python-dotenv

# Descargar el script
# Copia image_organizer.py a tu dispositivo
```

### En Linux/Mac/Windows

```bash
pip install opencv-python-headless pillow imagehash scikit-learn python-dotenv
```

### Para modo online (Gemini Vision)

```bash
pip install emergentintegrations
# Configura EMERGENT_LLM_KEY en .env
```

## 📖 Uso

### Comandos Básicos

```bash
# Organizar imágenes (modo offline)
python image_organizer.py /ruta/carpeta --mode offline

# Organizar con IA online (Gemini)
python image_organizer.py /ruta/carpeta --mode online

# Modo interactivo
python image_organizer.py --interactive
```

### Búsqueda

```bash
# Buscar imágenes similares a una de ejemplo
python image_organizer.py /carpeta --example /ruta/imagen.jpg

# Buscar por nombre de archivo
python image_organizer.py /carpeta --name "vacaciones"

# Buscar y mover resultados
python image_organizer.py /carpeta --example foto.jpg --move-results

# Ajustar umbral de similitud (1-64, menor = más estricto)
python image_organizer.py /carpeta --example img.jpg --threshold 5
```

### Todas las Opciones

```bash
python image_organizer.py --help

Opciones:
  folder                    Carpeta con imágenes a analizar
  --mode, -m               Modo: offline, online, hybrid
  --example, -e            Imagen de ejemplo para búsqueda
  --name, -n               Patrón de nombre para búsqueda
  --threshold, -t          Umbral de similitud (1-64)
  --move-results, -r       Mover resultados a carpeta
  --interactive, -i        Modo interactivo
  --api-key, -k            API key para modo online
  --verbose, -v            Información detallada
```

## 🌐 Interfaz Web (Opcional)

También incluye una interfaz web para uso más visual:

```bash
# Iniciar servidor
cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 8001

# Abrir en navegador: http://localhost:8001
```

## ⚙️ Configuración

Crea un archivo `.env` en la carpeta del script:

```env
# Solo necesario para modo online
EMERGENT_LLM_KEY=tu_api_key_aqui
```

## 📊 Categorías

| Categoría | Descripción |
|-----------|-------------|
| `rostros` | Imágenes con rostros humanos (subagrupadas por persona) |
| `texto` | Imágenes con texto detectado |
| `objetos` | Imágenes con objetos (sin personas ni texto) |
| `sin_personas` | Paisajes, fondos, imágenes sin contenido específico |
| `mixto` | Imágenes con rostros Y texto |
| `desconocido` | No clasificadas |

## 🔧 Tecnologías

- **OpenCV** - Detección de rostros offline
- **ImageHash** - Comparación de imágenes por similitud
- **Gemini Vision** - Análisis avanzado online (opcional)
- **FastAPI** - API REST (interfaz web)
- **React** - Frontend web (opcional)

## 📱 Uso en Termux

1. Abre Termux
2. Navega a tu carpeta de fotos:
   ```bash
   cd /storage/emulated/0/DCIM/Camera
   ```
3. Ejecuta el organizador:
   ```bash
   python /data/data/com.termux/files/home/image_organizer.py . --mode offline
   ```

## ⚠️ Notas

- El modo offline usa Haar Cascades de OpenCV, funciona mejor con fotos reales que con dibujos
- El modo online (Gemini) requiere conexión a internet y API key
- Las imágenes se **mueven** (no copian) a las carpetas de categoría
- Para evitar duplicados, los archivos se renombran automáticamente si ya existen

## 📄 Licencia

MIT License - Usa libremente este proyecto.

---

Creado con ❤️ para Termux y organizadores de fotos
