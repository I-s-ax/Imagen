# 📷 Image Organizer - Organizador de Imágenes para Termux

Un organizador de imágenes inteligente diseñado para funcionar en **Termux** con dependencias mínimas. Detecta rostros, texto, objetos y organiza automáticamente tus imágenes en carpetas.

## ✨ Características

- 🔍 **Detección de rostros** - Detecta y agrupa personas similares
- 📝 **Reconocimiento de texto** - Identifica imágenes con texto
- 📦 **Detección de objetos** - Clasifica imágenes por contenido
- 🖼️ **Búsqueda por imagen de ejemplo** - Encuentra imágenes similares
- 🔎 **Búsqueda por nombre** - Busca por nombre de archivo
- 📱 **100% Compatible con Termux** - Solo necesita Pillow e imagehash
- 🌐 **Modo offline y online** - Sin internet (Pillow/OpenCV) o con IA (Gemini)

## 📦 Dependencias

### Mínimas (siempre funcionan en Termux):
```bash
pip install pillow imagehash
```

### Opcionales (mejor detección si se pueden instalar):
```bash
pip install opencv-python  # Para detección avanzada de rostros
pip install python-dotenv  # Para cargar variables de entorno
```

## 🚀 Instalación en Termux

```bash
# Actualizar paquetes
pkg update && pkg upgrade

# Instalar Python
pkg install python

# Instalar dependencias mínimas
pip install pillow imagehash

# Opcional: instalar OpenCV (puede fallar en algunos dispositivos)
pip install opencv-python

# Descargar el script
# Copia image_organizer.py a tu dispositivo
```

O ejecuta el script de instalación:
```bash
python setup_termux.py
```

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

## 📖 Uso

### Comandos Básicos

```bash
# Organizar imágenes (modo offline)
python image_organizer.py /sdcard/DCIM --mode offline

# Organizar con IA online (requiere API key)
python image_organizer.py /sdcard/DCIM --mode online

# Modo interactivo (recomendado para principiantes)
python image_organizer.py --interactive
```

### Búsqueda

```bash
# Buscar imágenes similares a una foto
python image_organizer.py /sdcard/DCIM --example /sdcard/foto.jpg

# Buscar por nombre de archivo
python image_organizer.py /sdcard/DCIM --name "vacaciones"

# Buscar y mover resultados automáticamente
python image_organizer.py /sdcard/DCIM --example foto.jpg --move-results

# Ajustar precisión de búsqueda (1-64, menor = más estricto)
python image_organizer.py /sdcard/DCIM --example foto.jpg --threshold 5
```

### Todas las Opciones

```
python image_organizer.py --help

Opciones:
  folder                 Carpeta con imágenes a analizar
  --mode, -m            Modo: offline, online, hybrid
  --example, -e         Imagen de ejemplo para búsqueda
  --name, -n            Patrón de nombre para búsqueda
  --threshold, -t       Umbral de similitud (1-64)
  --move-results, -r    Mover resultados a carpeta
  --interactive, -i     Modo interactivo
  --api-key, -k         API key para modo online
  --verbose, -v         Información detallada
```

## 📱 Ejemplo de Uso en Termux

```bash
# 1. Abrir Termux

# 2. Navegar a tu carpeta de fotos
cd /storage/emulated/0/DCIM/Camera

# 3. Ejecutar el organizador
python ~/image_organizer.py . --mode offline

# 4. Ver resultados
ls -la
```

## 📊 Categorías

| Categoría | Descripción |
|-----------|-------------|
| `rostros` | Imágenes con rostros humanos (subagrupadas por persona) |
| `texto` | Imágenes con texto detectado |
| `objetos` | Imágenes con objetos (sin personas ni texto) |
| `sin_personas` | Paisajes, fondos, imágenes sin contenido específico |
| `mixto` | Imágenes con rostros Y texto |

## ⚙️ Configuración para Modo Online

Para usar análisis con IA (Gemini Vision), crea un archivo `.env`:

```env
EMERGENT_LLM_KEY=tu_api_key_aqui
```

O pasa la key directamente:
```bash
python image_organizer.py /carpeta --mode online --api-key tu_key
```

## 🔧 Solución de Problemas

### "No module named 'cv2'"
Es normal, el programa funciona sin OpenCV usando Pillow como alternativa.

### "Permission denied"
En Termux necesitas dar permisos de almacenamiento:
```bash
termux-setup-storage
```

### Detección de rostros no funciona bien
- Sin OpenCV: usa detección por color de piel (menos precisa)
- Con OpenCV: usa Haar Cascades (más precisa)
- Modo online: usa Gemini Vision (más precisa pero necesita internet)

## 📄 Licencia

MIT License - Usa libremente este proyecto.

---

Creado con ❤️ para usuarios de Termux
