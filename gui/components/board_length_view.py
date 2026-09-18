from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtCore import Qt, QRectF, QPointF

from mvvm.viewmodels.knots_viewmodel import KnotsViewModel

class BoardLengthView(QWidget):
    """
    Component that displays a horizontal rectangle representing the length of the board.
    It shows the position of the knots along the board relative to the length,
    and the board ID on the left.
    """
    def __init__(self, knots_vm: KnotsViewModel = None):
        super().__init__()
        self.knots_vm = knots_vm
        
        # Increase minimum height to make space for the drawing
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        
        if self.knots_vm:
            # self.update is inherited from QWidget and calls paintEvent
            self.knots_vm.knots_changed.connect(self.update)
            self.knots_vm.current_knot_changed.connect(self.update)
            self.knots_vm.knot_data_changed.connect(self.update)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background to match the "virtual board" white space
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        
        if not self.knots_vm or not self.knots_vm._current_board or not self.knots_vm.board_repo:
            return
            
        try:
            board = self.knots_vm.board_repo.get_board_by_id(
                self.knots_vm._current_board, 
                self.knots_vm._current_project
            )
        except Exception:
            return
            
        if not board:
            return
            
        board_length = board.length
        board_hight = getattr(board, 'height', 0)
        
        if board_length <= 0 or board_hight <= 0:
            return
        
        width = self.width()
        height = self.height()
        
        margin_x = 45  # Increased to make room for the label on the right
        margin_y = 15
        available_width = width - 2 * margin_x
        available_height = height - 2 * margin_y
        
        aspect_ratio = board_length / board_hight
        
        rect_width = available_height * aspect_ratio
        rect_height = available_height
        
        if rect_width > available_width:
            rect_width = available_width
            rect_height = rect_width / aspect_ratio
            
        start_x = margin_x + (available_width - rect_width) / 2.0
        start_y = margin_y + (available_height - rect_height) / 2.0
        
        # Draw the board length rectangle
        board_rect = QRectF(start_x, start_y, rect_width, rect_height)
        
        pen = QPen(Qt.GlobalColor.black, 1.5)
        painter.setPen(pen)
        # Using a slight wood-like color to match the other board drawing
        painter.setBrush(QBrush(QColor(240, 230, 210)))
        painter.drawRect(board_rect)
        
        # Draw testpos and the 4 section lines
        testpos = getattr(board, 'test_position', 0)
        if testpos is not None and testpos > 0:
            px_per_mm = rect_width / board_length
            
            def draw_v_line(x_mm, line_pen):
                if 0 <= x_mm <= board_length:
                    px_x = start_x + (x_mm * px_per_mm)
                    painter.setPen(line_pen)
                    painter.drawLine(QPointF(px_x, start_y), QPointF(px_x, start_y + rect_height))

            # Pen for the 4 space-delimiting lines (less evident)
            bound_pen = QPen(QColor(100, 100, 100, 150), 1, Qt.PenStyle.DashLine)
            
            # Draw the 4 lines that delimit the 3 spaces of 6*height
            draw_v_line(testpos - 9 * board_hight, bound_pen)
            draw_v_line(testpos - 3 * board_hight, bound_pen)
            draw_v_line(testpos + 3 * board_hight, bound_pen)
            draw_v_line(testpos + 9 * board_hight, bound_pen)
            
            # Pen for testpos (slightly more evident)
            testpos_pen = QPen(QColor(50, 50, 200, 200), 1.5, Qt.PenStyle.SolidLine)
            draw_v_line(testpos, testpos_pen)
        
        # Draw board_id on the left side
        painter.setPen(Qt.GlobalColor.black)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        
        board_id_text = f"{self.knots_vm._current_board}"
        painter.drawText(
            QRectF(start_x + 5, start_y, 100, rect_height),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            board_id_text
        )
        
        # Draw the +/- 150mm zone for the selected knot (drawn first so it's behind the dots)
        for knot in self.knots_vm._knots:
            if str(knot.knot_no) == str(self.knots_vm.current_knot_no):
                try:
                    knot_x = float(knot.x)
                    if 0 <= knot_x <= board_length:
                        relative_x = start_x + (knot_x / board_length) * rect_width
                        zone_mm = 150
                        px_per_mm = rect_width / board_length
                        zone_px_width = (zone_mm * 2) * px_per_mm
                        zone_px_x = relative_x - (zone_mm * px_per_mm)
                        
                        # Constrain to board bounds
                        if zone_px_x < start_x:
                            zone_px_width -= (start_x - zone_px_x)
                            zone_px_x = start_x
                        if zone_px_x + zone_px_width > start_x + rect_width:
                            zone_px_width = (start_x + rect_width) - zone_px_x
                        
                        if zone_px_width > 0:
                            painter.setBrush(QBrush(QColor(0, 150, 255, 60)))  # Semi-transparent blue
                            painter.setPen(Qt.PenStyle.NoPen)
                            painter.drawRect(QRectF(zone_px_x, start_y, zone_px_width, rect_height))
                except (TypeError, ValueError):
                    pass
                break
        
        # Draw knots
        for knot in self.knots_vm._knots:
            try:
                knot_x = float(knot.x)
            except (TypeError, ValueError):
                continue
                
            if knot_x < 0 or knot_x > board_length:
                continue
                
            # Calculate position relative to board length
            relative_x = start_x + (knot_x / board_length) * rect_width
            
            # Vertical position logic (distance from Side 4)
            # 0 = Side 4 (Top of rect), board_hight = Side 2 (Bottom of rect)
            dist_from_side4 = board_hight / 2.0
            
            if knot.side1_z1 is not None and knot.side1_z2 is not None:
                z_center = (knot.side1_z1 + knot.side1_z2) / 2.0
                dist_from_side4 = board_hight - z_center
            elif knot.side3_z1 is not None and knot.side3_z2 is not None:
                z_center = (knot.side3_z1 + knot.side3_z2) / 2.0
                dist_from_side4 = z_center
            elif knot.side4_z1 is not None or knot.side4_z2 is not None:
                dist_from_side4 = 0
            elif knot.side2_z1 is not None or knot.side2_z2 is not None:
                dist_from_side4 = board_hight
                
            dot_y = start_y + (dist_from_side4 / board_hight) * rect_height
            
            is_selected = str(knot.knot_no) == str(self.knots_vm.current_knot_no)
            
            if is_selected:
                painter.setBrush(QBrush(Qt.GlobalColor.red))
                painter.setPen(QPen(Qt.GlobalColor.darkRed, 1))
                radius = 4
            else:
                painter.setBrush(QBrush(QColor(255, 0, 0, 150)))
                painter.setPen(Qt.PenStyle.NoPen)
                radius = 2.5
                
            painter.drawEllipse(QPointF(relative_x, dot_y), radius, radius)

        # Draw a small vertical bar and "Side 1\nview" label on the right side
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        
        # Small vertical bar
        bar_x = start_x + rect_width + 5
        bar_y_center = start_y + rect_height / 2.0
        painter.drawLine(QPointF(bar_x, bar_y_center - 10), QPointF(bar_x, bar_y_center + 10))
        
        font = painter.font()
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        
        label_text = "Side 1\nview"
        painter.drawText(
            QRectF(bar_x + 5, start_y, margin_x - 10, rect_height),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label_text
        )
