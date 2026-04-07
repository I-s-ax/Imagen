#!/usr/bin/env python3
"""
Script de instalación para Termux
Ejecutar: python setup_termux.py
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
    is_termux = 'com.termux' in os.environ.get('PREFIX', '')
    
    if is_termux:
        print("\n📱 Detectado: Termux")
        
        # Actualizar paquetes
        run_command("pkg update -y", "Actualizando paquetes")
        run_command("pkg upgrade -y", "Actualizando sistema")
        
        # Instalar dependencias del sistema
        run_command("pkg install -y python python-pip", "Instalando Python")
        run_command("pkg install -y opencv-python", "Instalando OpenCV")
        run_command("pkg install -y libjpeg-turbo libpng", "Instalando bibliotecas de imagen")
        
    else:
        print("\n💻 Detectado: Sistema estándar (Linux/Mac/Windows)")
    
    # Instalar dependencias de Python
    print("\n📦 Instalando dependencias de Python...")
    
    packages = [
        "opencv-python-headless",
        "pillow",
        "numpy",
        "scikit-learn",
        "imagehash",
        "python-dotenv",
        "emergentintegrations"
    ]
    
    for pkg in packages:
        run_command(f"{sys.executable} -m pip install {pkg} --quiet", f"Instalando {pkg}")
    
    # Verificar instalación
    print("\n🔍 Verificando instalación...")
    
    try:
        import cv2
        print(f"   ✅ OpenCV: {cv2.__version__}")
    except ImportError:
        print("   ❌ OpenCV no instalado")
    
    try:
        from PIL import Image
        import PIL
        print(f"   ✅ Pillow: {PIL.__version__}")
    except ImportError:
        print("   ❌ Pillow no instalado")
    
    try:
        import imagehash
        print("   ✅ imagehash instalado")
    except ImportError:
        print("   ❌ imagehash no instalado")
    
    try:
        import numpy as np
        print(f"   ✅ NumPy: {np.__version__}")
    except ImportError:
        print("   ❌ NumPy no instalado")
    
    print("\n" + "=" * 50)
    print("  ✅ INSTALACIÓN COMPLETADA")
    print("=" * 50)
    print("\nUso básico:")
    print("  python image_organizer.py /ruta/carpeta --mode offline")
    print("  python image_organizer.py --interactive")
    print("\nPara más ayuda:")
    print("  python image_organizer.py --help")


if __name__ == '__main__':
    main()
