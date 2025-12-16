"""
Build script for creating standalone executable.
Usage: python build.py
"""

import PyInstaller.__main__
import shutil
from pathlib import Path

def build():
    """Build the executable using PyInstaller."""
    print("Building OmniSearch Pro...")
    
    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # PyInstaller options
    PyInstaller.__main__.run([
        'src/main.py',
        '--name=OmniSearch Pro',
        '--onefile',
        '--windowed',
        '--icon=assets/icon.ico',  # Add your icon
        '--add-data=LICENSE;.',
        '--hidden-import=customtkinter',
        '--hidden-import=sqlite3',
        '--clean',
        '--noconfirm',
    ])
    
    print("\nBuild complete! Executable located in dist/ directory.")

if __name__ == "__main__":
    build()