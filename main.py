"""
MVVM Architecture Application Entry Point.

This is the main entry point for the LocalKnot application.
It creates a QApplication, applies styling, and launches MainWindow.

MainWindow handles all MVVM component initialization:
- Database setup (DatabaseManager)
- Repository creation (ProjectRepository, BoardRepository, KnotRepository)
- ViewModel instantiation (ProjectsViewModel, BoardsViewModel, KnotsViewModel)
- View creation and Signal/Slot binding (ProjectsView, BoardsView, KnotsView)
"""

import sys
import os
import ctypes
from pathlib import Path

# Add the project root directory to the Python path
if getattr(sys, 'frozen', False):
    project_root = Path(sys._MEIPASS)
else:
    project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from core.path_utils import get_resource_path, get_project_root
project_root = get_project_root()
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QFile, QTextStream, QIODevice
from gui.main_window import MainWindow
import resources_rc

def main():
    """Application entry point - MVVM Architecture."""
    
    if os.name == 'nt':
        myappid = 'LocalKnot.WoodKnotAnalyzer.App.1'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    icon_file = get_resource_path("imgs/logo_DEMO.ico")
    if not icon_file.exists():
        icon_file = get_resource_path("imgs/LOGPCNR.svg")
        
    app_icon = QIcon(str(icon_file))
    app.setWindowIcon(app_icon)

    # Apply global stylesheet directly from the filesystem
    qss_file_path = get_resource_path("styles/style.qss")
    qss_file = QFile(str(qss_file_path))
    if qss_file.open(QIODevice.ReadOnly | QIODevice.Text):
        stream = QTextStream(qss_file)
        qss_content = stream.readAll()
        
        # Inject the absolute images path into the QSS
        imgs_path = str(get_resource_path("imgs")).replace("\\", "/")
        qss_content = qss_content.replace("{{IMGS_PATH}}", imgs_path)
        
        app.setStyleSheet(qss_content)
        qss_file.close()

    # Create and show main window
    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()