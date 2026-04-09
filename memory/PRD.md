# PRD: Image Organizer - Organizador de Imágenes con IA

## Problema Original
Crear un proyecto ejecutable por Termux que pueda reconocer rostros, objetos, caras de personas, textos, imágenes sin personas, y que conforme lo detecte lo esté moviendo a carpetas según lo que encuentre. También que se pueda poner la dirección de la carpeta para analizar, una imagen de ejemplo para buscar similares, y reconocer por nombres de archivo. Modo offline y online.

## Elecciones del Usuario
- **Tipo**: CLI (línea de comandos) para Termux
- **Categorías**: rostros (distinguiendo personas), objetos, texto, sin_personas
- **Búsqueda**: Por imagen de ejemplo (similares + misma persona) y por nombre
- **Modo**: Offline (OpenCV) y Online (Gemini Vision gratuito)
- **Resultados**: Mover a subcarpetas dentro de la carpeta analizada

## Arquitectura

### Backend (Python/FastAPI)
- `image_organizer.py` - Script CLI principal
- `server.py` - API REST opcional para interfaz web
- OpenCV + Haar Cascades para detección offline
- ImageHash para comparación de similitud
- Gemini Vision para análisis online

### Frontend (React - Opcional)
- Interfaz web para uso visual
- Pestañas: Organizar, Buscar, Analizar, CLI
- Toggle Offline/Online

## Lo Implementado (Abril 2026)

### CLI (image_organizer.py) - Versión Ligera para Termux
- [x] **Dependencias mínimas**: Solo requiere `pillow` e `imagehash`
- [x] **OpenCV opcional**: Funciona con o sin OpenCV
- [x] Organización por categorías (rostros, texto, objetos, sin_personas, mixto)
- [x] Agrupación de rostros similares en subcarpetas persona_1, persona_2...
- [x] Detección de texto heurística (sin Tesseract)
- [x] Detección de rostros con Pillow (fallback si no hay OpenCV)
- [x] Búsqueda por imagen de ejemplo con umbral configurable
- [x] Búsqueda por nombre de archivo
- [x] Modo interactivo
- [x] Modo offline (Pillow/OpenCV) y online (Gemini)
- [x] Barra de progreso en terminal
- [x] Eliminado scikit-learn (no necesario)

### API REST
- [x] POST /api/analyze - Iniciar análisis en segundo plano
- [x] GET /api/analyze/{job_id} - Estado del análisis
- [x] POST /api/search - Búsqueda por ejemplo o nombre
- [x] GET /api/folder/info - Información de carpeta
- [x] POST /api/analyze/single - Analizar imagen individual
- [x] GET /api/jobs - Listar trabajos recientes

### Interfaz Web
- [x] Diseño oscuro moderno con acentos cyan
- [x] Toggle Offline/Online
- [x] 4 pestañas funcionales
- [x] Visualización de progreso y resultados
- [x] Documentación CLI integrada

## Backlog

### P0 (Crítico)
- Ninguno pendiente

### P1 (Importante)
- [ ] Mejorar detección de rostros con modelos DNN de OpenCV
- [ ] Agregar Tesseract OCR para extracción de texto real
- [ ] Búsqueda recursiva en subcarpetas

### P2 (Mejoras)
- [ ] Exportar resultados a JSON/CSV
- [ ] Vista previa de imágenes en web
- [ ] Historial de análisis persistente
- [ ] Soporte para videos (extraer frames)
- [ ] Detección de duplicados exactos

## Personas de Usuario

1. **Usuario Termux**: Necesita organizar fotos del móvil sin apps pesadas
2. **Fotógrafo amateur**: Quiere clasificar miles de fotos por contenido
3. **Usuario técnico**: Prefiere CLI sobre interfaces gráficas

## Métricas de Éxito
- Análisis offline funcional sin dependencias pesadas
- Tiempo de procesamiento < 1 segundo por imagen (offline)
- Precisión de categorización > 85% en fotos reales

## Próximos Pasos
1. Probar con fotos reales de rostros humanos
2. Considerar agregar face_recognition library si OpenCV no es suficiente
3. Implementar Tesseract para OCR real
