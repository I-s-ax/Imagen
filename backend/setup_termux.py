#!/usr/bin/env python3
"""
Script de instalación para Termux
Ejecutar: python setup_termux.py

Dependencias MÍNIMAS (funciona sin OpenCV):
  - pillow
  - imagehash

Dependencias OPCIONALES (mejor detección):
  - opencv-python (si se puede instalar)
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Ejecutar comando y mostrar resultado."""
    print(f"\n📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {description} - Completado")
            return True
        else:
            print(f"   ⚠️ {description} - Advertencia: {result.stderr[:100]}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 50)
    print("  🔧 INSTALACIÓN IMAGE ORGANIZER PARA TERMUX")
    print("=" * 50)
    
    # Detectar si estamos en Termux
    is_termux = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')
    
    if is_termux:
        print("\n📱 Detectado: Termux")
        
        # Actualizar paquetes
        run_command("pkg update -y", "Actualizando paquetes")
        run_command("pkg upgrade -y", "Actualizando sistema")
        
        # Instalar Python y pip
        run_command("pkg install -y python", "Instalando Python")
        
        # Instalar dependencias del sistema para Pillow
        run_command("pkg install -y libjpeg-turbo libpng", "Instalando bibliotecas de imagen")
        
    else:
        print("\n💻 Detectado: Sistema estándar (Linux/Mac/Windows)")
    
    # Instalar dependencias MÍNIMAS de Python (siempre funcionan)
    print("\n📦 Instalando dependencias mínimas...")
    
    minimal_packages = [
        "pillow",
        "imagehash",
    ]
    
    for pkg in minimal_packages:
        run_command(f"{sys.executable} -m pip install {pkg} --quiet", f"Instalando {pkg}")
    
    # Intentar instalar OpenCV (opcional)
    print("\n📦 Intentando instalar OpenCV (opcional)...")
    opencv_installed = run_command(
        f"{sys.executable} -m pip install opencv-python --quiet",
        "Instalando opencv-python"
    )
    
    if not opencv_installed:
        print("   ℹ️ OpenCV no se pudo instalar - el programa funcionará con Pillow")
    
    # Intentar instalar python-dotenv (opcional)
    run_command(f"{sys.executable} -m pip install python-dotenv --quiet", "Instalando python-dotenv")
    
    # Verificar instalación
    print("\n" + "=" * 50)
    print("🔍 Verificando instalación...")
    print("=" * 50)
    
    # Verificar Pillow
    try:
        from PIL import Image
        import PIL
        print(f"   ✅ Pillow: {PIL.__version__}")
    except ImportError:
        print("   ❌ Pillow NO instalado - REQUERIDO")
        return
    
    # Verificar imagehash
    try:
        import imagehash
        print("   ✅ imagehash: instalado")
    except ImportError:
        print("   ❌ imagehash NO instalado - REQUERIDO")
        return
    
    # Verificar OpenCV (opcional)
    try:
        import cv2
        print(f"   ✅ OpenCV: {cv2.__version__} (detección avanzada)")
    except ImportError:
        print("   ⚠️ OpenCV: No disponible (usando detección básica con Pillow)")
    
    print("\n" + "=" * 50)
    print("  ✅ INSTALACIÓN COMPLETADA")
    print("=" * 50)
    print("\n📝 Dependencias instaladas:")
    print("   - pillow (requerido) ✅")
    print("   - imagehash (requerido) ✅")
    print("   - opencv-python (opcional)")
    
    print("\n🚀 Uso básico:")
    print("   python image_organizer.py /ruta/carpeta --mode offline")
    print("   python image_organizer.py --interactive")
    print("\n📖 Ayuda completa:")
    print("   python image_organizer.py --help")


if __name__ == '__main__':
    main()
