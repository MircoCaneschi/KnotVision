from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QGroupBox, QLabel, QFrame, QStyle
)
from PySide6.QtCore import Qt, QSize, Property
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPixmap, QIcon

from core.path_utils import get_resource_path

class FlaredTabButton(QPushButton):
    """A custom button that draws an outward-flared tab shape at the top.
    
    Colors are controlled via QSS custom properties:
        qproperty-normalColor
        qproperty-hoverColor
        qproperty-pressedColor
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default colors — overridden by QSS qproperty-* declarations
        self._normal_color = QColor("#824300")
        self._hover_color = QColor("#A85C0A")
        self._pressed_color = QColor("#A85C0A")

    # --- normalColor property ---
    def _get_normal_color(self): return self._normal_color
    def _set_normal_color(self, color): self._normal_color = QColor(color); self.update()
    normalColor = Property(QColor, _get_normal_color, _set_normal_color)

    # --- hoverColor property ---
    def _get_hover_color(self): return self._hover_color
    def _set_hover_color(self, color): self._hover_color = QColor(color); self.update()
    hoverColor = Property(QColor, _get_hover_color, _set_hover_color)

    # --- pressedColor property ---
    def _get_pressed_color(self): return self._pressed_color
    def _set_pressed_color(self, color): self._pressed_color = QColor(color); self.update()
    pressedColor = Property(QColor, _get_pressed_color, _set_pressed_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        w = self.width()
        h = self.height()
        r = 10  # bottom inward radius
        f = 12  # top outward flare radius
        
        path.moveTo(0, 0)
        # Top-left outward curve
        path.quadTo(f, 0, f, f)
        # Left straight edge
        path.lineTo(f, h - r)
        # Bottom-left inward curve
        path.quadTo(f, h, f + r, h)
        # Bottom straight edge
        path.lineTo(w - f - r, h)
        # Bottom-right inward curve
        path.quadTo(w - f, h, w - f, h - r)
        # Right straight edge
        path.lineTo(w - f, f)
        # Top-right outward curve
        path.quadTo(w - f, 0, w, 0)
        # Close path
        path.lineTo(0, 0)
        
        if self.isDown():
            color = self._pressed_color
        elif self.underMouse():
            color = self._hover_color
        else:
            color = self._normal_color
            
        painter.fillPath(path, color)
        
        # Draw the text and icon vertically stacked
        painter.setPen(QColor(Qt.GlobalColor.white))
        font_metrics = painter.fontMetrics()
        text_rect = font_metrics.boundingRect(self.text())
        
        icon = self.icon()
        # Force a larger icon size for better visibility
        icon_size = QSize(24, 24)
            
        # Spacing between text and icon (was 4, set to 0 to bring them closer)
        # Using negative spacing because the SVG itself has empty margins
        spacing = -6
        total_height = text_rect.height() + icon_size.height() + spacing
        start_y = (h - total_height) // 2
        
        icon_x = (w - icon_size.width()) // 2
        text_x = (w - text_rect.width()) // 2
        
        # Tint icon to pure white
        pixmap = icon.pixmap(icon_size)
        if not pixmap.isNull():
            tinted = QPixmap(pixmap.size())
            tinted.setDevicePixelRatio(pixmap.devicePixelRatio())
            tinted.fill(Qt.GlobalColor.transparent)
            p2 = QPainter(tinted)
            p2.drawPixmap(0, 0, pixmap)
            p2.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p2.fillRect(tinted.rect(), QColor(Qt.GlobalColor.white))
            p2.end()
            pixmap = tinted
            
        if "Show" in self.text():
            # Text above, icon below
            text_y = start_y + font_metrics.ascent()
            painter.drawText(text_x, text_y, self.text())
            icon_y = start_y + text_rect.height() + spacing
            if not pixmap.isNull():
                painter.drawPixmap(icon_x, icon_y, pixmap)
        else:
            # Icon above, text below
            icon_y = start_y
            if not pixmap.isNull():
                painter.drawPixmap(icon_x, icon_y, pixmap)
            text_y = start_y + icon_size.height() + spacing + font_metrics.ascent()
            painter.drawText(text_x, text_y, self.text())

    def sizeHint(self):
        # Provide a reasonable default size for the vertical layout
        return QSize(160, 45)

from mvvm.viewmodels.virtual_board_vm import VirtualBoardViewModel

class KnotResultsView(QWidget):
    """
    View component to display the calculated parameters of the knot.
    Can be expanded/collapsed.
    """
    def __init__(self, view_model: VirtualBoardViewModel):
        super().__init__()
        self.view_model = view_model
        
        self.setup_ui()
        self.bind_view_model()
        
    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(9, 0, 18, 0)
        main_layout.setSpacing(0) # No spacing between divider and button
        
        # Horizontal divider line
        self.divider = QFrame()
        self.divider.setObjectName("ResultsDivider")
        main_layout.addWidget(self.divider)
        
        # Group with data (initially hidden)
        self.results_group = QGroupBox("Knot Parameters")
        group_layout = QGridLayout(self.results_group)
        
        # Create placeholder labels for results
        self.result_labels = {}
        parameters = ["tKnot", "mKnot", "tKAR", "mKAR_L", "mKAR_R", "mKAR", "DEB", "DAB", "DEK", "EEB", "EAB"]
        
        row, col = 0, 0
        for param in parameters:
            name_lbl = QLabel(f"<b>{param}:</b>")
            val_lbl = QLabel("-")
            
            form = QHBoxLayout()
            form.addWidget(name_lbl)
            form.addWidget(val_lbl)
            form.addStretch()
            
            group_layout.addLayout(form, row, col)
            self.result_labels[param] = val_lbl
            
            col += 1
            if col > 5:  # 6 columns to not make it too tall
                col = 0
                row += 1
                
        main_layout.addWidget(self.results_group)
        self.results_group.hide()  # Hide at startup
        
        # Button layout to center it and make it narrow
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        # Button to show/hide results
        self.toggle_results_btn = FlaredTabButton("Show parameters")
        self.toggle_results_btn.setObjectName("ResultsToggleBtn")
        self.toggle_results_btn.setFixedWidth(160)
        icon_down = QIcon(str(get_resource_path("imgs/arrow_down.svg")))
        self.toggle_results_btn.setIcon(icon_down)
        self.toggle_results_btn.clicked.connect(self._toggle_results)
        
        btn_layout.addWidget(self.toggle_results_btn)
        btn_layout.addStretch()
        
        main_layout.addLayout(btn_layout)
        


    def _toggle_results(self):
        """Shows or hides the results panel with a smooth slide animation."""
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        
        # Initialize animation object if it doesn't exist
        if not hasattr(self, 'anim'):
            self.anim = QPropertyAnimation(self.results_group, b"maximumHeight")
            self.anim.setDuration(300)
            self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.anim.finished.connect(self._on_animation_finished)
            self._is_collapsing = False
            
        if self.results_group.isVisible():
            # Setup collapse animation
            self._is_collapsing = True
            self.anim.setStartValue(self.results_group.height())
            self.anim.setEndValue(0)
            self.anim.start()
            
            self.toggle_results_btn.setText("Show parameters")
            icon_down = QIcon(str(get_resource_path("imgs/arrow_down.svg")))
            self.toggle_results_btn.setIcon(icon_down)
        else:
            # Setup expand animation
            self._is_collapsing = False
            self.results_group.show()
            
            # Reset max height temporarily to get accurate size hint
            self.results_group.setMaximumHeight(16777215)
            target_height = self.results_group.sizeHint().height()
            
            self.results_group.setMaximumHeight(0)
            self.anim.setStartValue(0)
            self.anim.setEndValue(target_height)
            self.anim.start()
            
            self.toggle_results_btn.setText("Hide parameters")
            icon_up = QIcon(str(get_resource_path("imgs/arrow_up.svg")))
            self.toggle_results_btn.setIcon(icon_up)

    def _on_animation_finished(self):
        """Handle cleanup after animation completes."""
        if self._is_collapsing:
            self.results_group.hide()
        # Reset maximum height so the layout can resize naturally if the window is resized
        self.results_group.setMaximumHeight(16777215)

    def bind_view_model(self):
        # Connect the view_model signal to update the labels
        self.view_model.results_updated.connect(self._update_results)
        pass
        
    def _update_results(self, results_dict):
        """Updates the labels with calculated results."""
        for param, val in results_dict.items():
            if param in self.result_labels:
                self.result_labels[param].setText(str(val))
