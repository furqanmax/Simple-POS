#!/usr/bin/env python3
"""
Build script for creating Windows executable from Linux
This script uses PyInstaller to create a standalone Windows .exe file
"""

import os
import sys
import shutil
import subprocess

def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")
    
    # Check for PyInstaller
    try:
        import PyInstaller
        print("✓ PyInstaller found")
    except ImportError:
        print("✗ PyInstaller not found. Install with: pip install pyinstaller")
        return False
    
    return True

def create_spec_file():
    """Create PyInstaller spec file for Windows build"""
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files
added_files = [
    ('*.py', '.'),
    ('requirements.txt', '.'),
    ('README.md', '.'),
]

# Collect all required packages
hiddenimports = [
    'tkinter',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'reportlab',
    'reportlab.lib',
    'reportlab.platypus',
    'reportlab.pdfgen',
    'qrcode',
    'bcrypt',
    'sqlite3',
    'json',
    'logging',
    'datetime',
    'decimal',
    'os',
    'sys',
    'io',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='POS_System',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='pos_icon.ico' if os.path.exists('pos_icon.ico') else None,
)
"""
    
    with open('pos_system_windows.spec', 'w') as f:
        f.write(spec_content)
    print("✓ Spec file created: pos_system_windows.spec")

def build_windows_exe():
    """Build Windows executable using PyInstaller"""
    print("\n" + "="*60)
    print("Building Windows executable...")
    print("="*60 + "\n")
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
        print("✓ Cleaned previous build directory")
    
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("✓ Cleaned previous dist directory")
    
    # Create spec file
    create_spec_file()
    
    # Build with PyInstaller
    print("\nRunning PyInstaller...")
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'pos_system_windows.spec'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Build completed successfully!")
            print(f"✓ Executable created: dist/POS_System.exe")
            
            # Create distribution folder
            dist_folder = "POS_System_Windows"
            if os.path.exists(dist_folder):
                shutil.rmtree(dist_folder)
            os.makedirs(dist_folder)
            
            # Copy executable and necessary files
            shutil.copy("dist/POS_System.exe", dist_folder)
            shutil.copy("README.md", dist_folder)
            shutil.copy("requirements.txt", dist_folder)
            
            # Create default invoices folder
            os.makedirs(os.path.join(dist_folder, "invoices"), exist_ok=True)
            
            print(f"\n✓ Distribution folder created: {dist_folder}/")
            print(f"  - POS_System.exe (Main executable)")
            print(f"  - README.md (Documentation)")
            print(f"  - requirements.txt (Dependencies list)")
            print(f"  - invoices/ (Default invoice folder)")
            
            return True
        else:
            print("✗ Build failed!")
            print("Error output:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Build failed with error: {e}")
        return False

def build_with_wine():
    """Build Windows executable using Wine and Windows Python (for Linux systems)"""
    print("\n" + "="*60)
    print("Building Windows executable using Wine (Linux -> Windows)")
    print("="*60 + "\n")
    
    print("Prerequisites for Wine build:")
    print("1. Install Wine: sudo apt-get install wine wine32 wine64")
    print("2. Install Windows Python in Wine:")
    print("   wget https://www.python.org/ftp/python/3.10.11/python-3.10.11.exe")
    print("   wine python-3.10.11.exe")
    print("3. Install PyInstaller in Wine Python:")
    print("   wine python.exe -m pip install pyinstaller pillow reportlab qrcode bcrypt")
    print("\nThen run:")
    print("   wine python.exe build_windows.py")

def main():
    print("="*60)
    print("POS System - Windows Executable Builder")
    print("="*60)
    
    if not check_dependencies():
        print("\n✗ Missing dependencies. Please install them first.")
        return 1
    
    if sys.platform == "win32":
        # Native Windows build
        if build_windows_exe():
            print("\n✓ Windows executable built successfully!")
            return 0
        else:
            return 1
    else:
        # Cross-platform build from Linux/Mac
        print("\nDetected non-Windows platform: " + sys.platform)
        print("\nOptions for creating Windows executable from Linux:")
        print("\n1. Using PyInstaller directly (may have compatibility issues):")
        print("   python3 build_windows.py --force-pyinstaller")
        print("\n2. Using Wine (recommended for true Windows compatibility):")
        build_with_wine()
        print("\n3. Using Docker with Windows container:")
        print("   See build_docker_windows.sh")
        
        if "--force-pyinstaller" in sys.argv:
            if build_windows_exe():
                print("\n⚠ Note: This executable was built on Linux.")
                print("  It may have compatibility issues on Windows.")
                print("  For best results, build on Windows or use Wine.")
            return 0
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
