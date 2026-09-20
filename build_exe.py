"""
Build script for KnotVision executable.
Runs PyInstaller using KnotVision.spec and validates the output.
Usage:
    python build_exe.py
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parent
    spec_file = project_root / "KnotVision.spec"
    
    if not spec_file.exists():
        print(f"Error: Spec file not found at {spec_file}")
        sys.exit(1)
        
    print("=" * 60)
    print("Starting KnotVision Build with PyInstaller...")
    print(f"Project root: {project_root}")
    print(f"Using spec file: {spec_file.name}")
    print("=" * 60)

    # Run PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    print(f"Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=str(project_root))
    if result.returncode != 0:
        print(f"\n[ERROR] PyInstaller failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    # Validate output
    dist_dir = project_root / "dist" / "KnotVision"
    exe_file = dist_dir / "KnotVision.exe"
    internal_model = dist_dir / "_internal" / "models" / "sam2.1_hiera_small.pt"
    
    print("\n" + "=" * 60)
    print("Validating build output...")
    print("=" * 60)
    
    all_ok = True
    if not exe_file.exists():
        print(f"[FAIL] Executable not found: {exe_file}")
        all_ok = False
    else:
        print(f"[OK] Executable generated: {exe_file.name} ({exe_file.stat().st_size // (1024*1024)} MB)")

    if not internal_model.exists():
        print(f"[FAIL] Model file missing: {internal_model}")
        all_ok = False
    else:
        print(f"[OK] AI Model bundled: {internal_model.name} ({internal_model.stat().st_size // (1024*1024)} MB)")

    # Also place a copy next to the exe for maximum compatibility
    beside_model_dir = dist_dir / "models"
    beside_model_dir.mkdir(exist_ok=True)
    beside_model = beside_model_dir / "sam2.1_hiera_small.pt"
    if not beside_model.exists() and internal_model.exists():
        shutil.copy2(internal_model, beside_model)
        print(f"[OK] Model mirrored beside executable: {beside_model}")

    if all_ok:
        print("\n" + "*" * 60)
        print("BUILD SUCCESSFUL! The application is ready in:")
        print(f"  {dist_dir}")
        print("*" * 60)
    else:
        print("\n[ERROR] Build validation failed. Check messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
