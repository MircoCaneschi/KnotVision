from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QGraphicsView, QGraphicsScene,
                               QSizePolicy, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt

from core.database import DatabaseManager
from core.repository import ProjectRepository, BoardRepository, KnotRepository
from mvvm.viewmodels import ProjectsViewModel, BoardsViewModel, KnotsViewModel
from gui.components.data_panel.projects_view_mvvm import ProjectsView
from gui.components.data_panel.boards_view_mvvm import BoardsView
from gui.components.data_panel.knots_view_mvvm import KnotsView
from gui.components.header import HeaderWidget

from core.board_calculator import BoardCalculator
from mvvm.viewmodels.virtual_board_vm import VirtualBoardViewModel
from gui.components.virtual_board_view import VirtualBoardView
from gui.components.knot_results_view import KnotResultsView
from core.export_manager import ExportManager
from PySide6.QtWidgets import QFileDialog, QScrollBar

class FloatingScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.floating_scrollbar = QScrollBar(Qt.Orientation.Vertical, self)
        

        real_sb = self.verticalScrollBar()
        real_sb.rangeChanged.connect(self.floating_scrollbar.setRange)
        real_sb.valueChanged.connect(self.floating_scrollbar.setValue)
        self.floating_scrollbar.valueChanged.connect(real_sb.setValue)
        
        # Sync pageStep so the scrollbar handle has the correct proportional size
        def sync_page_step(*args):
            self.floating_scrollbar.setPageStep(real_sb.pageStep())
            
        real_sb.rangeChanged.connect(sync_page_step)
        sync_page_step()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        sb_width = self.floating_scrollbar.sizeHint().width()
        if sb_width <= 0:
            sb_width = 14  # fallback
        self.floating_scrollbar.setGeometry(
            self.width() - sb_width,
            0,
            sb_width,
            self.height()
        )
        self.floating_scrollbar.raise_()
import sys
import ctypes

class MainWindow(QMainWindow):
    """Main application window with MVVM architecture."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LocalKnot - MVVM Architecture")

        from PySide6.QtGui import QIcon
        from core.path_utils import get_resource_path
        icon_file = get_resource_path("imgs/logo_DEMO.ico")
        if not icon_file.exists():
            icon_file = get_resource_path("imgs/LOGPCNR.svg")
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        self.resize(1000, 700)
        self._set_custom_titlebar_color()
        self._setup_ui()

    def _set_custom_titlebar_color(self):
        from gui.theme_utils import set_custom_titlebar_color
        set_custom_titlebar_color(self)
        
    def _setup_ui(self):
        self.scroll_area = FloatingScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        central_widget = QWidget()
        self.scroll_area.setWidget(central_widget)
        self.setCentralWidget(self.scroll_area)

        # Main vertical layout
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ==================== Setup MVVM Components ====================

        # Setup Database and Repositories
        self.db = DatabaseManager()
        self.project_repo = ProjectRepository(self.db)
        self.board_repo = BoardRepository(self.db)
        self.knot_repo = KnotRepository(self.db)

        # Create ViewModels
        self.projects_vm = ProjectsViewModel(self.project_repo)
        self.boards_vm = BoardsViewModel(self.board_repo, self.knot_repo)
        self.knots_vm = KnotsViewModel(self.knot_repo, self.board_repo)

        # Initialize ImportManager in ProjectsViewModel
        self.projects_vm.initialize_import_manager(self.board_repo, self.knot_repo)

        # Create Views
        self.projects_view = ProjectsView(self.projects_vm)
        self.boards_view = BoardsView(self.boards_vm)
        self.knots_view = KnotsView(self.knots_vm)

        # ==================== Add to Layout ====================
        
        # Header Layout
        self.header = HeaderWidget()
        self.main_layout.addWidget(self.header)

        # Toolbar with toggle button
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(9, 0, 18, 5)
        self.toggle_panel_btn = QPushButton("Toggle Data Panel")
        self.toggle_panel_btn.setObjectName("ToggleDataPanelBtn")
        self.toggle_panel_btn.clicked.connect(self._toggle_data_panel)
        toolbar_layout.addWidget(self.toggle_panel_btn)
        self.main_layout.addLayout(toolbar_layout)

        # Data panel container
        self.data_panel_container = QWidget()
        self.data_panel_layout = QHBoxLayout(self.data_panel_container)
        self.data_panel_layout.setContentsMargins(9, 9, 18, 9)

        # Add all views to their QGroupBox
        self.project_group = QGroupBox(f"PROJECTS [{self.projects_view.combo_box_projects.count()}]")
        self.board_group = QGroupBox(f"BOARDS[{self.boards_view.board_no_combo.count()}]")
        self.knot_group = QGroupBox(f"KNOTS[{self.knots_view.knot_no_combo.count()}]")

        self.project_group.setLayout(self.projects_view.main_layout)
        self.board_group.setLayout(self.boards_view.main_layout)
        self.knot_group.setLayout(self.knots_view.main_layout)

        # Add groups to the layout
        self.data_panel_layout.addWidget(self.project_group)
        self.data_panel_layout.addWidget(self.board_group)
        self.data_panel_layout.addWidget(self.knot_group)

        self.main_layout.addWidget(self.data_panel_container)

        # Connect signals for cross-viewModel communication and UI updates
        self.projects_vm.projects_changed.connect(self._update_project_counter)
        self.projects_vm.export_requested.connect(self._handle_export)
        self.boards_vm.boards_changed.connect(self._update_board_counter)
        self.knots_vm.knots_changed.connect(self._update_knot_counter)
        
        # VERY IMPORTANT ORDER: Update knots_vm with new project FIRST, 
        # so when boards_vm selects the first board and emits current_board_changed, 
        # knots_vm already knows the correct project context.
        self.projects_vm.current_project_changed.connect(self.knots_vm.handle_project_changed)
        self.projects_vm.current_project_changed.connect(self.boards_vm.handle_project_changed)
        
        self.boards_vm.current_board_changed.connect(self.knots_vm.handle_board_changed)
        # When a board is saved, notify KnotsVM so it re-verifies board existence and unlocks
        self.boards_vm.board_saved.connect(lambda msg: self.knots_vm.handle_board_changed(self.boards_vm.current_board_no))

        # Hidden panel (compact view)
        self.hidden_data_panel_container = QWidget()
        self.hidden_data_panel_layout = QHBoxLayout(self.hidden_data_panel_container)
        self.hidden_data_panel_layout.setContentsMargins(9, 9, 18, 9)

        # Hidden groupBox
        self.hidden_project_group = QGroupBox(f"PROJECTS[{self.projects_view.combo_box_projects.count()}]")
        self.hidden_board_group = QGroupBox(f"BOARDS[{self.boards_view.board_no_combo.count()}]")
        self.hidden_knot_group = QGroupBox(f"KNOTS[{self.knots_view.knot_no_combo.count()}]")

        self.hidden_project_group.setLayout(self.projects_view.hidden_main_layout)
        self.hidden_board_group.setLayout(self.boards_view.hidden_main_layout)
        self.hidden_knot_group.setLayout(self.knots_view.hidden_main_layout)

        # Add hidden views
        if hasattr(self.projects_view, 'hidden_main_layout') and self.projects_view.hidden_main_layout:
            self.hidden_data_panel_layout.addWidget(self.hidden_project_group, 1)
        if hasattr(self.boards_view, 'hidden_main_layout') and self.boards_view.hidden_main_layout:
            self.hidden_data_panel_layout.addWidget(self.hidden_board_group, 1)
        if hasattr(self.knots_view, 'hidden_main_layout') and self.knots_view.hidden_main_layout:
            self.hidden_data_panel_layout.addWidget(self.hidden_knot_group, 1)

        #self.hidden_data_panel_layout.addStretch()
        self.main_layout.addWidget(self.hidden_data_panel_container)
        self.hidden_data_panel_container.hide()

        # Virtual Board area
        self.board_calculator = BoardCalculator()
        self.virtual_board_vm = VirtualBoardViewModel(self.board_calculator, self.knot_repo)
        
        # Results panel (between data panel and virtual board)
        self.knot_results_view = KnotResultsView(self.virtual_board_vm)
        self.main_layout.addWidget(self.knot_results_view)
        
        self.virtual_board_view = VirtualBoardView(self.virtual_board_vm, self.knots_vm)
        self.virtual_board_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout.addWidget(self.virtual_board_view, stretch=1)

        # ==================== AI Analysis Section ====================
        from core.ai.adapters.sam2_analyzer import Sam2Analyzer
        from mvvm.viewmodels.ai_analysis_vm import AiAnalysisViewModel
        from gui.components.ai_analysis_view import AiAnalysisView

        self.ai_analyzer = Sam2Analyzer()
        self.ai_analysis_vm = AiAnalysisViewModel(self.ai_analyzer, self.boards_vm, self.knots_vm)
        self.ai_analysis_view = AiAnalysisView(self.ai_analysis_vm)
        
        # Add to the layout with a smaller stretch factor to give more room to VirtualBoard initially if needed
        # Or no stretch so it takes its natural height (min 400px)
        self.main_layout.addWidget(self.ai_analysis_view, stretch=0)
        
        # Redraw the virtual board when board/knot/project data changes or is saved/deleted
        self.boards_vm.board_saved.connect(self.virtual_board_view._redraw_board)
        self.boards_vm.board_data_changed.connect(self.virtual_board_view._redraw_board)
        self.boards_vm.boards_changed.connect(self.virtual_board_view._redraw_board)
        self.knots_vm.knot_saved.connect(self.virtual_board_view._redraw_board)
        self.knots_vm.knots_changed.connect(self.virtual_board_view._redraw_board)
        self.projects_vm.projects_changed.connect(self.virtual_board_view._redraw_board)

        # Trigger knot parameter recalculation
        self.boards_vm.board_saved.connect(self._update_knot_results)
        self.boards_vm.boards_changed.connect(self._update_knot_results)
        self.boards_vm.current_board_changed.connect(self._update_knot_results)
        
        self.knots_vm.knot_saved.connect(self._update_knot_results)
        self.knots_vm.knots_changed.connect(self._update_knot_results)
        self.knots_vm.current_knot_changed.connect(self._update_knot_results)
        
        self.projects_vm.projects_changed.connect(self._update_knot_results)
        self.projects_vm.current_project_changed.connect(self._update_knot_results)

        # Trigger initial data load now that UI is fully initialized
        self.knots_vm.handle_project_changed(self.projects_vm.current_project)
        self.boards_vm.handle_project_changed(self.projects_vm.current_project)

        self.showMaximized()

    def _update_knot_results(self, *args, **kwargs):
        """Fetches the current state and triggers a recalculation of the parameters."""
        board_no = self.boards_vm.current_board_no
        board = next((b for b in self.boards_vm._boards if str(b.board_no) == board_no), None)
        
        knot_no = self.knots_vm.current_knot_no
        current_knot = next((k for k in self.knots_vm._knots if str(k.knot_no) == knot_no), None)
        
        knots = self.knots_vm._knots

        self.virtual_board_vm.update_results(board, knots, current_knot)

    def _handle_export(self):
        """Handle the export request by validating state and opening file dialog."""
        # Validate that we are not in editing mode anywhere by checking if save buttons are enabled
        is_project_editing = self.projects_view.save_btn.isEnabled()
        is_board_editing = self.boards_view.save_btn.isEnabled()
        is_knot_editing = self.knots_view.save_btn.isEnabled()

        # If knot is editing but there are no knots and fields are default, ignore it (forced new mode)
        if is_knot_editing and not self.knots_vm._knots:
            if (self.knots_vm.x == 0 and 
                self.knots_vm.pith_z is None and 
                self.knots_vm.pith_y is None and 
                self.knots_vm.comment == "" and 
                not self.knots_vm.is_pruned_knot):
                is_knot_editing = False

        if is_project_editing or is_board_editing or is_knot_editing:
            self.projects_vm.export_error.emit("Cannot export. Please save all changes first.")
            return

        project_id = self.projects_vm.current_project
        if not project_id:
            self.projects_vm.export_error.emit("No project selected to export.")
            return

        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Project Data",
            f"{project_id}_export.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        # Perform the export
        try:
            exporter = ExportManager(self.project_repo, self.board_repo, self.knot_repo)
            success = exporter.export_project(project_id, file_path)
            if success:
                self.projects_vm.export_success.emit("Project exported successfully!")
            else:
                self.projects_vm.export_error.emit("Export failed.")
        except Exception as e:
            self.projects_vm.export_error.emit(f"Export Error: {str(e)}")

    def _toggle_data_panel(self):
        """Manages the visibility of the top data panel with a smooth animation."""
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
        
        # Initialize animation group if it doesn't exist
        if not hasattr(self, 'panel_anim_group'):
            self.panel_anim_group = QParallelAnimationGroup(self)
            
            self.anim_main = QPropertyAnimation(self.data_panel_container, b"maximumHeight")
            self.anim_main.setDuration(300)
            self.anim_main.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            self.anim_hidden = QPropertyAnimation(self.hidden_data_panel_container, b"maximumHeight")
            self.anim_hidden.setDuration(300)
            self.anim_hidden.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            self.panel_anim_group.addAnimation(self.anim_main)
            self.panel_anim_group.addAnimation(self.anim_hidden)
            self.panel_anim_group.finished.connect(self._on_panel_animation_finished)
            self._is_main_panel_collapsing = False

        if self.data_panel_container.isVisible():
            # Setup for collapsing main panel and expanding hidden panel
            self._is_main_panel_collapsing = True
            
            # Show the hidden container to allow animation
            self.hidden_data_panel_container.show()
            
            # Calculate target height for the hidden panel
            self.hidden_data_panel_container.setMaximumHeight(16777215)
            hidden_target = self.hidden_data_panel_container.sizeHint().height()
            
            # Start values and end values
            self.anim_main.setStartValue(self.data_panel_container.height())
            self.anim_main.setEndValue(0)
            
            self.anim_hidden.setStartValue(0)
            self.anim_hidden.setEndValue(hidden_target)
            
            self.panel_anim_group.start()
        else:
            # Setup for expanding main panel and collapsing hidden panel
            self._is_main_panel_collapsing = False
            
            # Show the main container to allow animation
            self.data_panel_container.show()
            
            # Calculate target height for the main panel
            self.data_panel_container.setMaximumHeight(16777215)
            main_target = self.data_panel_container.sizeHint().height()
            
            # Start values and end values
            self.anim_main.setStartValue(0)
            self.anim_main.setEndValue(main_target)
            
            self.anim_hidden.setStartValue(self.hidden_data_panel_container.height())
            self.anim_hidden.setEndValue(0)
            
            self.panel_anim_group.start()

    def _on_panel_animation_finished(self):
        """Cleanup after the panel animation finishes."""
        if self._is_main_panel_collapsing:
            self.data_panel_container.hide()
            self.hidden_data_panel_container.setMaximumHeight(16777215)
        else:
            self.hidden_data_panel_container.hide()
            self.data_panel_container.setMaximumHeight(16777215)

    def _update_project_counter(self, projects: list):
        """Update the counter in the project group box title."""
        count = len(projects)
        self.project_group.setTitle(f"PROJECTS [{count}]")
        self.hidden_project_group.setTitle(f"PROJECTS [{count}]")

    def _update_board_counter(self, boards: list):
        """Update the counter in the board group box title."""
        count = len(boards)
        self.board_group.setTitle(f"BOARDS [{count}]")
        self.hidden_board_group.setTitle(f"BOARDS [{count}]")

    def _update_knot_counter(self, knots: list):
        """Update the counter in the knot group box title."""
        count = len(knots)
        self.knot_group.setTitle(f"KNOTS [{count}]")
        self.hidden_knot_group.setTitle(f"KNOTS [{count}]")
