import React, { useState, useCallback, useEffect } from 'react';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Progress } from './components/ui/progress';
import { Badge } from './components/ui/badge';
import { Slider } from './components/ui/slider';
import { Switch } from './components/ui/switch';
import { Label } from './components/ui/label';
import { Toaster, toast } from 'sonner';
import { 
  FolderOpen, 
  Search, 
  Image, 
  Users, 
  FileText, 
  Box, 
  Zap, 
  Wifi, 
  WifiOff,
  Play,
  Loader2,
  CheckCircle,
  XCircle,
  Terminal,
  Download,
  Eye,
  Move,
  RefreshCw
} from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

function App() {
  const [folderPath, setFolderPath] = useState('');
  const [mode, setMode] = useState('offline');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(null);
  const [results, setResults] = useState(null);
  const [folderInfo, setFolderInfo] = useState(null);
  
  // Search state
  const [searchType, setSearchType] = useState('name');
  const [searchQuery, setSearchQuery] = useState('');
  const [exampleImage, setExampleImage] = useState(null);
  const [threshold, setThreshold] = useState([10]);
  const [moveResults, setMoveResults] = useState(true);
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  
  // Single image analysis
  const [singleImage, setSingleImage] = useState(null);
  const [singleAnalysis, setSingleAnalysis] = useState(null);
  const [isAnalyzingSingle, setIsAnalyzingSingle] = useState(false);

  const [jobs, setJobs] = useState([]);

  // Poll for job status
  useEffect(() => {
    let interval;
    if (progress && progress.status === 'processing') {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_URL}/api/analyze/${progress.job_id}`);
          const data = await res.json();
          setProgress(prev => ({ ...prev, ...data }));
          
          if (data.status === 'completed') {
            setResults(data.results);
            setIsAnalyzing(false);
            toast.success('Análisis completado');
          } else if (data.status === 'error') {
            toast.error(`Error: ${data.error}`);
            setIsAnalyzing(false);
          }
        } catch (err) {
          console.error('Error polling:', err);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [progress]);

  const loadFolderInfo = async () => {
    if (!folderPath) return;
    try {
      const res = await fetch(`${API_URL}/api/folder/info?folder_path=${encodeURIComponent(folderPath)}`);
      if (res.ok) {
        const data = await res.json();
        setFolderInfo(data);
      } else {
        toast.error('Carpeta no encontrada');
      }
    } catch (err) {
      toast.error('Error cargando información de carpeta');
    }
  };

  const startAnalysis = async () => {
    if (!folderPath) {
      toast.error('Por favor ingresa una ruta de carpeta');
      return;
    }
    
    setIsAnalyzing(true);
    setResults(null);
    
    try {
      const formData = new FormData();
      formData.append('folder_path', folderPath);
      formData.append('mode', mode);
      
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        setProgress({ job_id: data.job_id, status: 'processing', progress: 0, total: 0 });
        toast.info('Análisis iniciado...');
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Error iniciando análisis');
        setIsAnalyzing(false);
      }
    } catch (err) {
      toast.error('Error de conexión');
      setIsAnalyzing(false);
    }
  };

  const handleSearch = async () => {
    if (!folderPath) {
      toast.error('Ingresa la ruta de la carpeta');
      return;
    }
    
    setIsSearching(true);
    setSearchResults(null);
    
    try {
      const body = {
        folder_path: folderPath,
        search_type: searchType,
        threshold: threshold[0],
        move_results: moveResults
      };
      
      if (searchType === 'name') {
        body.name_pattern = searchQuery;
      } else if (searchType === 'example' && exampleImage) {
        body.example_image = exampleImage;
      }
      
      const res = await fetch(`${API_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
        toast.success(`Encontradas ${data.total_found} imágenes`);
      } else {
        toast.error('Error en búsqueda');
      }
    } catch (err) {
      toast.error('Error de conexión');
    } finally {
      setIsSearching(false);
    }
  };

  const handleExampleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        setExampleImage(base64);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSingleImageAnalysis = async () => {
    if (!singleImage) {
      toast.error('Selecciona una imagen');
      return;
    }
    
    setIsAnalyzingSingle(true);
    setSingleAnalysis(null);
    
    try {
      const formData = new FormData();
      formData.append('file', singleImage);
      formData.append('mode', mode);
      
      const res = await fetch(`${API_URL}/api/analyze/single`, {
        method: 'POST',
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        setSingleAnalysis(data);
        toast.success('Imagen analizada');
      } else {
        toast.error('Error analizando imagen');
      }
    } catch (err) {
      toast.error('Error de conexión');
    } finally {
      setIsAnalyzingSingle(false);
    }
  };

  const loadJobs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/jobs`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
      }
    } catch (err) {
      console.error('Error loading jobs:', err);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  return (
    <div className="app-container" data-testid="app-container">
      <Toaster position="top-right" richColors />
      
      {/* Header */}
      <header className="app-header" data-testid="app-header">
        <div className="header-content">
          <div className="logo-section">
            <div className="logo-icon">
              <Image className="icon" />
            </div>
            <div>
              <h1>Image Organizer</h1>
              <p>Organizador de imágenes con IA</p>
            </div>
          </div>
          
          <div className="mode-toggle">
            <div className="mode-option">
              <WifiOff className={`mode-icon ${mode === 'offline' ? 'active' : ''}`} />
              <span>Offline</span>
            </div>
            <Switch
              data-testid="mode-switch"
              checked={mode === 'online'}
              onCheckedChange={(checked) => setMode(checked ? 'online' : 'offline')}
            />
            <div className="mode-option">
              <Wifi className={`mode-icon ${mode === 'online' ? 'active' : ''}`} />
              <span>Online</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Folder Input */}
        <Card className="folder-card" data-testid="folder-card">
          <CardContent className="folder-input-section">
            <div className="input-group">
              <FolderOpen className="input-icon" />
              <Input
                data-testid="folder-path-input"
                placeholder="Ruta de la carpeta (ej: /storage/emulated/0/DCIM)"
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                className="folder-input"
              />
              <Button 
                data-testid="load-folder-btn"
                variant="outline" 
                onClick={loadFolderInfo}
              >
                <RefreshCw className="btn-icon" />
                Cargar
              </Button>
            </div>
            
            {folderInfo && (
              <div className="folder-info" data-testid="folder-info">
                <Badge variant="secondary">{folderInfo.image_count} imágenes</Badge>
                {Object.entries(folderInfo.categories).map(([cat, count]) => (
                  <Badge key={cat} variant="outline">{cat}: {count}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="organize" className="main-tabs">
          <TabsList className="tabs-list" data-testid="tabs-list">
            <TabsTrigger value="organize" data-testid="tab-organize">
              <Box className="tab-icon" />
              Organizar
            </TabsTrigger>
            <TabsTrigger value="search" data-testid="tab-search">
              <Search className="tab-icon" />
              Buscar
            </TabsTrigger>
            <TabsTrigger value="analyze" data-testid="tab-analyze">
              <Eye className="tab-icon" />
              Analizar
            </TabsTrigger>
            <TabsTrigger value="cli" data-testid="tab-cli">
              <Terminal className="tab-icon" />
              CLI
            </TabsTrigger>
          </TabsList>

          {/* Organize Tab */}
          <TabsContent value="organize" data-testid="organize-content">
            <Card className="action-card">
              <CardHeader>
                <CardTitle>Organizar Imágenes</CardTitle>
                <CardDescription>
                  Analiza y organiza automáticamente tus imágenes en carpetas por categoría
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="categories-preview">
                  <div className="category-item">
                    <Users className="category-icon faces" />
                    <span>Rostros</span>
                  </div>
                  <div className="category-item">
                    <FileText className="category-icon text" />
                    <span>Texto</span>
                  </div>
                  <div className="category-item">
                    <Box className="category-icon objects" />
                    <span>Objetos</span>
                  </div>
                  <div className="category-item">
                    <Image className="category-icon no-people" />
                    <span>Sin personas</span>
                  </div>
                </div>

                {isAnalyzing && progress && (
                  <div className="progress-section" data-testid="progress-section">
                    <div className="progress-header">
                      <Loader2 className="spin" />
                      <span>Analizando: {progress.current_file}</span>
                    </div>
                    <Progress value={progress.total > 0 ? (progress.progress / progress.total) * 100 : 0} />
                    <span className="progress-text">{progress.progress} / {progress.total}</span>
                  </div>
                )}

                {results && (
                  <div className="results-section" data-testid="results-section">
                    <h4><CheckCircle className="success-icon" /> Completado</h4>
                    <div className="results-grid">
                      <div className="result-item">
                        <span className="result-label">Procesadas</span>
                        <span className="result-value">{results.processed}</span>
                      </div>
                      <div className="result-item">
                        <span className="result-label">Movidas</span>
                        <span className="result-value">{results.moved}</span>
                      </div>
                      <div className="result-item">
                        <span className="result-label">Errores</span>
                        <span className="result-value error">{results.errors}</span>
                      </div>
                    </div>
                    <div className="categories-results">
                      {Object.entries(results.categories || {}).map(([cat, count]) => (
                        <Badge key={cat} className={`category-badge ${cat}`}>
                          {cat}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
              <CardFooter>
                <Button 
                  data-testid="start-analysis-btn"
                  onClick={startAnalysis} 
                  disabled={isAnalyzing || !folderPath}
                  className="start-btn"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="btn-icon spin" />
                      Analizando...
                    </>
                  ) : (
                    <>
                      <Play className="btn-icon" />
                      Iniciar Análisis
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>

          {/* Search Tab */}
          <TabsContent value="search" data-testid="search-content">
            <Card className="action-card">
              <CardHeader>
                <CardTitle>Buscar Imágenes</CardTitle>
                <CardDescription>
                  Busca por imagen de ejemplo o por nombre de archivo
                </CardDescription>
              </CardHeader>
              <CardContent className="search-content">
                <div className="search-type-toggle">
                  <Button 
                    data-testid="search-by-name-btn"
                    variant={searchType === 'name' ? 'default' : 'outline'}
                    onClick={() => setSearchType('name')}
                  >
                    <FileText className="btn-icon" />
                    Por Nombre
                  </Button>
                  <Button 
                    data-testid="search-by-example-btn"
                    variant={searchType === 'example' ? 'default' : 'outline'}
                    onClick={() => setSearchType('example')}
                  >
                    <Image className="btn-icon" />
                    Por Ejemplo
                  </Button>
                </div>

                {searchType === 'name' ? (
                  <div className="search-input-group">
                    <Search className="input-icon" />
                    <Input
                      data-testid="search-query-input"
                      placeholder="Nombre o patrón (ej: vacaciones, IMG_202)"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                ) : (
                  <div className="example-upload">
                    <label className="upload-area" data-testid="example-upload-area">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleExampleImageUpload}
                        hidden
                      />
                      {exampleImage ? (
                        <div className="preview-container">
                          <img 
                            src={`data:image/jpeg;base64,${exampleImage}`} 
                            alt="Ejemplo" 
                            className="preview-image"
                          />
                          <span>Imagen cargada ✓</span>
                        </div>
                      ) : (
                        <>
                          <Image className="upload-icon" />
                          <span>Arrastra o selecciona imagen de ejemplo</span>
                        </>
                      )}
                    </label>
                    
                    <div className="threshold-slider">
                      <Label>Umbral de similitud: {threshold[0]}</Label>
                      <Slider
                        data-testid="threshold-slider"
                        value={threshold}
                        onValueChange={setThreshold}
                        min={1}
                        max={30}
                        step={1}
                      />
                      <span className="slider-hint">Menor = más estricto</span>
                    </div>
                  </div>
                )}

                <div className="search-options">
                  <div className="option-row">
                    <Switch
                      data-testid="move-results-switch"
                      checked={moveResults}
                      onCheckedChange={setMoveResults}
                    />
                    <Label>Mover resultados a carpeta</Label>
                  </div>
                </div>

                {searchResults && (
                  <div className="search-results" data-testid="search-results">
                    <h4>
                      <CheckCircle className="success-icon" />
                      {searchResults.total_found} imágenes encontradas
                      {searchResults.moved > 0 && ` (${searchResults.moved} movidas)`}
                    </h4>
                    <div className="results-list">
                      {searchResults.matches.slice(0, 20).map((match, i) => (
                        <div key={i} className="match-item">
                          <Image className="match-icon" />
                          <span className="match-name">{match.name || match.path.split('/').pop()}</span>
                          {match.similarity && (
                            <Badge variant="outline">{match.similarity.toFixed(1)}%</Badge>
                          )}
                        </div>
                      ))}
                      {searchResults.total_found > 20 && (
                        <span className="more-results">... y {searchResults.total_found - 20} más</span>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
              <CardFooter>
                <Button 
                  data-testid="search-btn"
                  onClick={handleSearch} 
                  disabled={isSearching || !folderPath}
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="btn-icon spin" />
                      Buscando...
                    </>
                  ) : (
                    <>
                      <Search className="btn-icon" />
                      Buscar
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>

          {/* Analyze Single Tab */}
          <TabsContent value="analyze" data-testid="analyze-content">
            <Card className="action-card">
              <CardHeader>
                <CardTitle>Analizar Imagen</CardTitle>
                <CardDescription>
                  Analiza una imagen individual para ver qué detecta
                </CardDescription>
              </CardHeader>
              <CardContent>
                <label className="upload-area large" data-testid="single-upload-area">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setSingleImage(e.target.files[0])}
                    hidden
                  />
                  {singleImage ? (
                    <div className="preview-container">
                      <img 
                        src={URL.createObjectURL(singleImage)} 
                        alt="Preview" 
                        className="preview-image large"
                      />
                      <span>{singleImage.name}</span>
                    </div>
                  ) : (
                    <>
                      <Eye className="upload-icon large" />
                      <span>Selecciona una imagen para analizar</span>
                    </>
                  )}
                </label>

                {singleAnalysis && (
                  <div className="analysis-results" data-testid="single-analysis-results">
                    <h4>Resultados del Análisis</h4>
                    <div className="analysis-grid">
                      <div className="analysis-item">
                        <Users className="analysis-icon" />
                        <div>
                          <span className="analysis-label">Rostros</span>
                          <span className="analysis-value">
                            {singleAnalysis.analysis?.faces?.face_count || 
                             singleAnalysis.analysis?.face_count || 0}
                          </span>
                        </div>
                      </div>
                      <div className="analysis-item">
                        <FileText className="analysis-icon" />
                        <div>
                          <span className="analysis-label">Texto</span>
                          <span className="analysis-value">
                            {singleAnalysis.analysis?.text?.has_text || 
                             singleAnalysis.analysis?.has_text ? 'Sí' : 'No'}
                          </span>
                        </div>
                      </div>
                      <div className="analysis-item">
                        <Box className="analysis-icon" />
                        <div>
                          <span className="analysis-label">Categoría</span>
                          <Badge>{singleAnalysis.analysis?.category || 'N/A'}</Badge>
                        </div>
                      </div>
                    </div>
                    {singleAnalysis.analysis?.description && (
                      <p className="analysis-description">{singleAnalysis.analysis.description}</p>
                    )}
                  </div>
                )}
              </CardContent>
              <CardFooter>
                <Button 
                  data-testid="analyze-single-btn"
                  onClick={handleSingleImageAnalysis}
                  disabled={isAnalyzingSingle || !singleImage}
                >
                  {isAnalyzingSingle ? (
                    <>
                      <Loader2 className="btn-icon spin" />
                      Analizando...
                    </>
                  ) : (
                    <>
                      <Zap className="btn-icon" />
                      Analizar Imagen
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>

          {/* CLI Tab */}
          <TabsContent value="cli" data-testid="cli-content">
            <Card className="action-card cli-card">
              <CardHeader>
                <CardTitle>
                  <Terminal className="title-icon" />
                  Uso en Terminal / Termux
                </CardTitle>
                <CardDescription>
                  Comandos para usar el organizador desde la línea de comandos
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="cli-section">
                  <h4>Instalación en Termux</h4>
                  <pre className="code-block">
{`# Actualizar paquetes
pkg update && pkg upgrade

# Instalar Python
pkg install python python-pip

# Instalar dependencias
pip install opencv-python-headless pillow imagehash scikit-learn

# Descargar el script
# (copiar image_organizer.py a tu dispositivo)`}
                  </pre>
                </div>

                <div className="cli-section">
                  <h4>Comandos Básicos</h4>
                  <pre className="code-block">
{`# Organizar imágenes (modo offline)
python image_organizer.py /sdcard/DCIM --mode offline

# Organizar con IA online (Gemini)
python image_organizer.py /sdcard/DCIM --mode online

# Modo interactivo
python image_organizer.py --interactive`}
                  </pre>
                </div>

                <div className="cli-section">
                  <h4>Búsqueda</h4>
                  <pre className="code-block">
{`# Buscar por imagen de ejemplo
python image_organizer.py /sdcard/DCIM --example /sdcard/foto.jpg

# Buscar por nombre
python image_organizer.py /sdcard/DCIM --name "vacaciones"

# Buscar y mover resultados
python image_organizer.py /sdcard/DCIM --example foto.jpg --move-results`}
                  </pre>
                </div>

                <div className="cli-section">
                  <h4>Opciones Avanzadas</h4>
                  <pre className="code-block">
{`# Ajustar umbral de similitud (1-64)
python image_organizer.py /carpeta --example img.jpg --threshold 5

# Ver ayuda completa
python image_organizer.py --help`}
                  </pre>
                </div>
              </CardContent>
              <CardFooter>
                <Button variant="outline" data-testid="download-script-btn">
                  <Download className="btn-icon" />
                  Descargar Script CLI
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Recent Jobs */}
        {jobs.length > 0 && (
          <Card className="jobs-card" data-testid="jobs-card">
            <CardHeader>
              <CardTitle>Trabajos Recientes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="jobs-list">
                {jobs.slice(0, 5).map((job) => (
                  <div key={job.id} className="job-item">
                    <div className="job-info">
                      <span className="job-path">{job.folder_path}</span>
                      <Badge variant={job.status === 'completed' ? 'default' : 'secondary'}>
                        {job.status}
                      </Badge>
                    </div>
                    {job.results && (
                      <span className="job-stats">
                        {job.results.moved} movidas / {job.results.processed} procesadas
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer" data-testid="app-footer">
        <p>Image Organizer v1.0 - Compatible con Termux</p>
        <p className="footer-hint">Modo {mode === 'online' ? 'Online (Gemini AI)' : 'Offline (OpenCV)'}</p>
      </footer>
    </div>
  );
}

export default App;
