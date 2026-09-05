import sys
import os
import platform
from pathlib import Path
from typing import Union, Optional
import numpy as np
import cv2


def get_project_root() -> Path:
    """
    Returns the root directory of the project.
    - If running in a PyInstaller bundle (frozen), returns Path(sys._MEIPASS).
    - If running in development, returns the directory containing main.py.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS).resolve()
    # core/path_utils.py -> parent is core -> parent is project root
    return Path(__file__).resolve().parent.parent


def get_resource_path(relative_path: Union[str, Path]) -> Path:
    """
    Resolves a resource path cross-platform in both development and bundled environments.
    
    Search priority:
    1. If relative_path is already absolute and exists -> return it directly.
    2. If running as a frozen executable (PyInstaller):
       a. Check inside PyInstaller internal bundle (sys._MEIPASS / relative_path)
       b. Check next to the executable (executable_dir / relative_path)
    3. If running in normal Python development:
       a. Check inside project_root / relative_path
       b. Check inside current working directory (Path.cwd() / relative_path)
    4. Fallback to (project_root / relative_path) or (sys._MEIPASS / relative_path).
    """
    path_obj = Path(relative_path)
    
    # 1. Absolute path check
    if path_obj.is_absolute() and path_obj.exists():
        return path_obj

    # 2. Frozen check (PyInstaller)
    if getattr(sys, 'frozen', False):
        # 2a. Inside bundle (_internal / sys._MEIPASS)
        bundle_path = Path(sys._MEIPASS).resolve() / path_obj
        if bundle_path.exists():
            return bundle_path
            
        # 2b. Beside the executable
        exe_dir = Path(sys.executable).resolve().parent
        exe_beside_path = exe_dir / path_obj
        if exe_beside_path.exists():
            return exe_beside_path
            
        # Default fallback in frozen mode
        return bundle_path

    # 3. Development check
    root = get_project_root()
    dev_path = root / path_obj
    if dev_path.exists():
        return dev_path

    cwd_path = Path.cwd() / path_obj
    if cwd_path.exists():
        return cwd_path

    # Default fallback in dev mode
    return dev_path


def get_app_data_dir(app_name: str = "LocalKnot") -> Path:
    """
    Returns the standard cross-platform application data directory:
    - Windows: %LOCALAPPDATA%/<app_name>
    - macOS: ~/Library/Application Support/<app_name>
    - Linux: $XDG_DATA_HOME/<app_name> or ~/.local/share/<app_name>
    """
    system = platform.system()
    if system == "Windows":
        base_dir = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~")))
    elif system == "Darwin":
        base_dir = Path(os.path.expanduser("~/Library/Application Support"))
    else:  # Linux / Unix
        xdg_data = os.getenv("XDG_DATA_HOME")
        if xdg_data:
            base_dir = Path(xdg_data)
        else:
            base_dir = Path(os.path.expanduser("~/.local/share"))

    app_dir = base_dir / app_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def safe_read_image(image_path: Union[str, Path]) -> Optional[np.ndarray]:
    """
    Reads an image using OpenCV in a cross-platform manner that supports
    Unicode/accented file paths (e.g. paths containing non-ASCII characters on Windows).
    
    Returns the BGR numpy array or None if the image cannot be read.
    """
    p = Path(image_path)
    if not p.exists() or not p.is_file():
        return None
        
    try:
        # np.fromfile + cv2.imdecode bypasses Windows C++ std::fopen ASCII limitations
        img_bytes = np.fromfile(str(p), dtype=np.uint8)
        if img_bytes.size == 0:
            return None
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        return img
    except Exception:
        # Fallback to standard cv2.imread if fromfile fails
        try:
            return cv2.imread(str(p))
        except Exception:
            return None
