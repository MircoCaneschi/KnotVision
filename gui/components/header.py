from PySide6.QtWidgets import QFrame, QLabel, QGridLayout, QWidget, QSizePolicy
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtSvg import QSvgRenderer
from core.path_utils import get_resource_path

class SvgLogoWidget(QWidget):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.renderer = QSvgRenderer(path)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(40)

    def sizeHint(self):
        if self.renderer.isValid():
            default_size = self.renderer.defaultSize()
            if default_size.height() > 0:
                aspect = default_size.width() / default_size.height()
                return QSize(int(50 * aspect), 50)
        return QSize(150, 50)

    def paintEvent(self, event):
        if not self.renderer.isValid():
            return
        
        painter = QPainter(self)
        default_size = self.renderer.defaultSize()
        if default_size.height() == 0:
            return
        
        aspect_ratio = default_size.width() / default_size.height()
        target_height = self.height()
        target_width = int(target_height * aspect_ratio)
        
        if target_width > self.width():
            target_width = self.width()
            target_height = int(target_width / aspect_ratio)
            
        # Disegna l'SVG allineato a sinistra (x=0) e centrato verticalmente
        rect = QRect(0, (self.height() - target_height) // 2, target_width, target_height)
        self.renderer.render(painter, rect)

class HeaderWidget(QFrame):
    """
    Main application header.
    Contains the logo, application name, and space for future elements.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppHeader")
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(18, 5, 5, 5)
        
        # Insert the path to your vector image (.svg) here
        # Since it is not yet compiled into resources, we use the absolute path from disk!
        icon_path = str(get_resource_path("imgs/LOGPCNR.svg"))
        logo_widget = SvgLogoWidget(icon_path)
        
        title_label = QLabel("KnotVision")
        # Assign ObjectName to be styled via QSS
        title_label.setObjectName("HeaderTitle")
        
        # Center the title perfectly and keep logo on the left
        # We don't use alignment on logo_widget so it can expand and use our custom paintEvent positioning
        layout.addWidget(logo_widget, 0, 0)
        layout.addWidget(title_label, 0, 0, alignment=Qt.AlignCenter)
