# Building Windows Executable from Linux

This guide explains how to create a Windows .exe file for the POS System from a Linux environment.

## Method 1: Using Wine (Recommended)

Wine allows you to run Windows applications on Linux. This method provides the most compatible Windows executables.

### Prerequisites

1. **Install Wine:**
```bash
sudo apt-get update
sudo apt-get install wine wine32 wine64 winbind
```

2. **Install Windows Python in Wine:**
```bash
# Download Windows Python installer
wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe

# Install Python using Wine (follow the installer prompts)
wine python-3.10.11-amd64.exe
```

3. **Set up Wine Python environment:**
```bash
# Add Wine Python to PATH
export WINEPYTHON="$HOME/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python310/python.exe"

# Verify installation
wine "$WINEPYTHON" --version
```

4. **Install required packages in Wine Python:**
```bash
wine "$WINEPYTHON" -m pip install --upgrade pip
wine "$WINEPYTHON" -m pip install pyinstaller
wine "$WINEPYTHON" -m pip install pillow reportlab qrcode bcrypt python-dateutil
```

### Building the Executable

1. **Navigate to the POS system directory:**
```bash
cd "/home/eshare/wordpress-6.8.1/simple pos"
```

2. **Create the Windows executable:**
```bash
wine "$WINEPYTHON" -m PyInstaller \
    --onefile \
    --windowed \
    --name "POS_System" \
    --add-data "*.py;." \
    --hidden-import tkinter \
    --hidden-import PIL \
    --hidden-import reportlab \
    --hidden-import qrcode \
    --hidden-import bcrypt \
    main.py
```

3. **The executable will be created in:** `dist/POS_System.exe`

## Method 2: Using PyInstaller with Docker

This method uses a Windows Docker container for true Windows compilation.

### Prerequisites

1. **Install Docker:**
```bash
sudo apt-get install docker.io
sudo systemctl start docker
sudo usermod -aG docker $USER
```

2. **Create Dockerfile:**
```dockerfile
# Use Windows Server Core with Python
FROM mcr.microsoft.com/windows/servercore:ltsc2022

# Install Python
RUN powershell -Command \
    Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -OutFile python.exe; \
    Start-Process python.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait; \
    Remove-Item python.exe

# Install dependencies
RUN python -m pip install --upgrade pip
RUN python -m pip install pyinstaller pillow reportlab qrcode bcrypt python-dateutil

# Copy application
WORKDIR /app
COPY . .

# Build executable
RUN python -m PyInstaller --onefile --windowed --name POS_System main.py
```

3. **Build with Docker:**
```bash
docker build -t pos-builder-windows .
docker run --rm -v $(pwd)/output:/app/dist pos-builder-windows
```

## Method 3: Cross-compilation with PyInstaller (Simple but Limited)

This method directly uses PyInstaller on Linux to create a Windows executable. Note: This may have compatibility issues.

### Prerequisites

1. **Install PyInstaller:**
```bash
pip install pyinstaller
```

2. **Install Windows dependencies:**
```bash
pip install pyinstaller[encryption]
pip install pillow reportlab qrcode bcrypt python-dateutil
```

### Building the Executable

1. **Run the build script:**
```bash
python3 build_windows.py --force-pyinstaller
```

**Note:** This method may produce executables with compatibility issues. Wine or Docker methods are preferred.

## Method 4: Using GitHub Actions (CI/CD)

Create `.github/workflows/build.yml`:

```yaml
name: Build Windows Executable

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-windows:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build executable
      run: |
        pyinstaller --onefile --windowed --name POS_System main.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: POS_System_Windows
        path: dist/POS_System.exe
```

## Verifying the Build

After building, test the executable:

1. **On Linux (using Wine):**
```bash
wine dist/POS_System.exe
```

2. **On Windows:**
- Copy `POS_System.exe` to a Windows machine
- Double-click to run
- Check that all features work correctly

## Troubleshooting

### Common Issues and Solutions

1. **"Failed to execute script" error:**
   - Ensure all dependencies are included in the build
   - Use `--debug=all` flag with PyInstaller for detailed logs

2. **Missing DLL errors:**
   - Add missing DLLs with `--add-binary` flag
   - Example: `--add-binary "vcruntime140.dll;."`

3. **Tkinter not found:**
   - Explicitly include tkinter: `--hidden-import tkinter`
   - May need to copy tcl/tk files manually

4. **Large file size:**
   - Use UPX compression: `--upx-dir=/path/to/upx`
   - Exclude unnecessary modules: `--exclude-module matplotlib`

5. **Antivirus false positives:**
   - Sign the executable with a code certificate
   - Submit to antivirus vendors for whitelisting

## Distribution

Once built, create a distribution package:

```bash
# Create distribution folder
mkdir POS_System_v1.0_Windows
cd POS_System_v1.0_Windows

# Copy necessary files
cp ../dist/POS_System.exe .
cp ../README.md .
mkdir invoices

# Create installer script (optional)
echo "@echo off" > install.bat
echo "echo Installing POS System..." >> install.bat
echo "mkdir %APPDATA%\POSSystem" >> install.bat
echo "copy POS_System.exe %APPDATA%\POSSystem\" >> install.bat
echo "echo Installation complete!" >> install.bat

# Create ZIP archive
cd ..
zip -r POS_System_v1.0_Windows.zip POS_System_v1.0_Windows/
```

## Requirements File Update

Ensure your `requirements.txt` includes:
```
Pillow>=9.0.0
reportlab>=3.6.0
qrcode>=7.3.0
bcrypt>=3.2.0
python-dateutil>=2.8.0
```

## Tips for Production

1. **Code Signing:**
   - Purchase a code signing certificate
   - Sign the executable to prevent security warnings

2. **Auto-update:**
   - Implement auto-update functionality
   - Use services like Squirrel or WinSparkle

3. **Installer:**
   - Create MSI installer using WiX Toolset
   - Or use NSIS for a simpler installer

4. **Testing:**
   - Test on multiple Windows versions (10, 11)
   - Test on 32-bit and 64-bit systems
   - Verify all features work without Python installed

## Quick Start Commands

```bash
# Install Wine
sudo apt-get install wine wine32 wine64

# Download and install Windows Python
wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
wine python-3.10.11-amd64.exe

# Install PyInstaller in Wine
wine python -m pip install pyinstaller pillow reportlab qrcode bcrypt

# Build executable
wine python -m PyInstaller --onefile --windowed --name POS_System main.py

# Test the executable
wine dist/POS_System.exe
```

Your Windows executable is now ready for distribution!
