"""
View Model for Projects management.

Manages presentation state and handles user interactions.
"""

from PySide6.QtCore import QObject, Signal, Slot, Property
from typing import List, Optional
from core.repository import ProjectRepository
from mvvm.models import Project
from core.exceptions import LocalKnotError
from core.import_manager import ImportManager

class ProjectsViewModel(QObject):
    """
    ViewModel for Projects management.

    Exposes:
    - Properties: project_list, species_list, current_project_message, etc.
    - Signals: projectsChanged, speciesChanged, etc.
    - Slots: handleNewProject, handleSaveProject, handleAddSpecies, etc.
    """

    # ==================== SIGNALS ====================
    projects_changed = Signal(list)
    species_changed = Signal(list)
    project_editable_changed = Signal(bool)
    species_editable_changed = Signal(bool)
    hide_messages = Signal(bool)
    project_error = Signal(str)
    species_error = Signal(str)
    project_saved = Signal(str)
    species_added = Signal(str)
    current_species_changed = Signal(str)
    species_updated = Signal(str, str)
    current_project_changed = Signal(str)
    project_modify_mode = Signal(bool)
    species_enabled_changed = Signal(bool)
    species_normal_mode_changed = Signal(bool)
    species_add_enabled = Signal(bool)
    species_modify_enabled = Signal(bool)
    species_delete_enabled = Signal(bool)
    save_enabled_changed = Signal(bool)
    navigation_enabled_changed = Signal(bool)
    export_requested = Signal()
    export_error = Signal(str)
    export_success = Signal(str)
    import_success = Signal(str)
    import_error = Signal(str)

    # ==================== CONSTRUCTOR ====================

    def __init__(self, repository: ProjectRepository):
        """
        Initialize the ProjectsViewModel.

        Sets up internal state for projects and species management.
        """
        super().__init__()
        self.repo = repository
        self._import_manager = None

        # Internal state
        self._projects = []
        self._species = []
        self._current_project = ""
        self._current_species = ""
        self._species_editable = False
        self._project_editable = False
        
        self._is_modifying = False
        self._original_project_name = ""
        self._original_species_name = ""

        # Load initial data
        self._load_projects_from_db()
        self._load_species_from_db()
        
        # Initial states
        self.save_enabled_changed.emit(False)
        self.navigation_enabled_changed.emit(True)
        
        # Species management initialization
        self.species_normal_mode_changed.emit(True)
        self._update_species_actions_state()

    # ==================== PROPERTIES ====================

    @Property(list, notify=projects_changed)
    def project_list(self) -> List[str]:
        """
        Get the current list of projects (read-only property).

        Returns:
            List[str]: List of project names
        """
        return [p.name for p in self._projects]

    @Property(list, notify=species_changed)
    def species_list(self) -> List[str]:
        """
        Get the current list of species (read-only property).

        Returns:
            List[str]: List of species names
        """
        return self._species

    @Property(str, notify=current_project_changed)
    def current_project(self) -> str:
        """Get the currently selected project name."""
        return self._current_project

    @current_project.setter
    def current_project(self, value: str):
        """Set the current project (property setter)."""
        if self._current_project != value:
            self._current_project = value
            
            # Only auto-change associated items and emit signals if we are navigating normally
            if not self._project_editable:
                self.current_project_changed.emit(value)
                
                matching_project = next((p for p in self._projects if p.name == value), None)

                if matching_project:
                    self._current_species = matching_project.species
                    self.current_species_changed.emit(self._current_species)

    @Property(str, notify=current_species_changed)
    def current_species(self) -> str:
        """Get the currently selected species name."""
        return self._current_species

    @current_species.setter
    def current_species(self, value: str):
        """Set the current species (property setter)."""
        if self._current_species != value:
            self._current_species = value
            self.current_species_changed.emit(value)
            self._update_species_actions_state()

    @Property(bool)
    def species_editable(self) -> bool:
        """Get whether the species field should be editable."""
        return self._species_editable

    # ==================== SLOTS (User Actions) ====================

    @Slot()
    def handle_new_project(self):
        print("handling new project")
        """
        Slot called when user clicks 'New Project' button.

        Prepares UI for new project creation:
        - Clears input fields
        - Makes project combo editable
        - Hides previous messages
        """
        self._is_modifying = False
        self.navigation_enabled_changed.emit(False)

        # 1. Make editable FIRST so the UI accepts custom/empty text
        self._project_editable = True
        self.project_editable_changed.emit(self._project_editable)

        # Update species actions state (enables selection and + button)
        self._update_species_actions_state()
        self.save_enabled_changed.emit(True)

        # 2. Set internal state and emit changes to clear UI
        self._current_project = ""
        self.current_project_changed.emit("")

        self._current_species = ""
        self.current_species_changed.emit("")

        # 3. Trigger modify mode to restrict combo box dropdown
        self.project_modify_mode.emit(True)

    @Slot()
    def handle_save_project(self):
        print("handling save project")
        """
        Slot called when user clicks 'Save Project' button.
        """
        project_text = self._current_project.strip()
        species_text = self._current_species.strip()

        self.hide_messages.emit(True)

        # Validate project name
        if not project_text:
            self.project_error.emit("Project name cannot be empty!")
            return
            
        # Check duplicate name
        if self._is_modifying:
            if project_text != self._original_project_name and any(p.name == project_text for p in self._projects):
                self.project_error.emit("Project name already exists!")
                return
        else:
            if any(p.name == project_text for p in self._projects):
                self.project_error.emit("Project already exists!")
                return
                
        # Validate species
        if not species_text:
            self.species_error.emit("Species cannot be empty!")
            return

        # If we are NOT in species editable mode (normal mode), 
        # ensure the species actually exists in the list
        if not self._species_editable and species_text not in self._species:
            self.species_error.emit("Please select a valid species!")
            return

        try:
            # If we WERE in species edit mode (In-Line), we might need to finalize the species record first
            if self._species_editable:
                # This logic mimics handle_save_species_edit but integrated here
                old_name = self._original_species_name
                new_name = species_text
                
                if old_name and old_name != new_name:
                    if self.repo.update_species(old_name, new_name):
                        self._species = [new_name if s == old_name else s for s in self._species]
                        self._species.sort()
                        self.species_changed.emit(self._species)
                        for p in self._projects:
                            if p.species == old_name:
                                p.species = new_name
                elif not old_name and new_name not in self._species:
                    # Adding new species
                    if self.repo.add_species(new_name):
                        self._species.append(new_name)
                        self._species.sort()
                        self.species_changed.emit(self._species)

            # Create and save project
            project = Project(name=project_text, species=species_text)
            
            if self._is_modifying:
                if self.repo.update_project(self._original_project_name, project):
                    for p in self._projects:
                        if p.name == self._original_project_name:
                            p.name = project.name
                            p.species = project.species
                            break
                    self.project_saved.emit("Project modified successfully!")
            else:
                if self.repo.add_project(project):
                    self._projects.append(project)
                    self.project_saved.emit(f"{project_text} registered!")

            # Add species if it's new (fallback/safety)
            if species_text not in self._species:
                self._species.append(species_text)
                self._species.sort()
                self.species_changed.emit(self._species)
                self.species_added.emit(f"{species_text} registered!")

            # Emit signals
            self.projects_changed.emit(self.project_list)

            # Reset state
            self._is_modifying = False
            self.project_modify_mode.emit(False)
            
            self._project_editable = False
            self._species_editable = False
            self.project_editable_changed.emit(False)
            self.species_editable_changed.emit(False)
            self.species_normal_mode_changed.emit(True)
            
            self._update_species_actions_state()
            self.save_enabled_changed.emit(False)
            self.navigation_enabled_changed.emit(True)
            
            # Re-select the saved project and force update signals
            self._current_project = "" # Force setter to recognize change
            self.current_project = project.name

        except LocalKnotError as e:
            self.project_error.emit(str(e))
        except Exception as e:
            self.project_error.emit(f"Failed to save project: {str(e)}")

    @Slot()
    def handle_modify_species(self):
        """
        Slot called when user clicks 'Modify Species' button.
        This prepares the UI for renaming a species in In-Line mode.
        """
        if not self._current_species:
            return

        # Store the original name to know what we are renaming
        self._original_species_name = self._current_species

        # Prepare for modification
        self._species_editable = True
        self.species_normal_mode_changed.emit(False)
        self.species_editable_changed.emit(True)

    @Slot()
    def handle_add_species(self):
        """
        Slot called when user clicks 'Add Species' button.
        Prepares UI for adding a new species in In-Line mode.
        """
        self._original_species_name = ""  # New species mode
        self._species_editable = True
        self.species_normal_mode_changed.emit(False)
        self.species_editable_changed.emit(True)
        self.current_species = ""

    @Slot()
    def handle_cancel_species_edit(self):
        """
        Cancel the current species add/modify operation.
        """
        self._species_editable = False
        self.current_species = self._original_species_name
        self.species_normal_mode_changed.emit(True)
        self.species_editable_changed.emit(False)
        self._update_species_actions_state()

    @Slot()
    def handle_save_species_edit(self):
        """
        Save the current species add/modify operation from In-Line mode.
        """
        new_name = self._current_species.strip()
        old_name = self._original_species_name

        if not new_name:
            self.species_error.emit("Species name cannot be empty!")
            return

        # If it's a rename and name hasn't changed, just exit
        if old_name and old_name == new_name:
            self.handle_cancel_species_edit()
            return

        # If it's new and already exists, error
        if not old_name and new_name in self._species:
            self.species_error.emit("Species already exists!")
            return

        try:
            if not old_name:
                # Add new species
                if self.repo.add_species(new_name):
                    self._species.append(new_name)
                    self._species.sort()
                    self.species_changed.emit(self._species)
                    self.species_added.emit(f"Species {new_name} added!")
            else:
                # Update existing species
                if self.repo.update_species(old_name, new_name):
                    # Update internal species list
                    self._species = [new_name if s == old_name else s for s in self._species]
                    self._species.sort()
                    self.species_changed.emit(self._species)
                    
                    # Update current projects list (species name changed)
                    for p in self._projects:
                        if p.species == old_name:
                            p.species = new_name
                    
                    self.species_added.emit(f"Species renamed to {new_name}!")
            
            # Success: update current and exit edit mode
            self._current_species = new_name
            self.current_species_changed.emit(new_name)
            self._species_editable = False
            self.species_normal_mode_changed.emit(True)
            self.species_editable_changed.emit(False)
            self._update_species_actions_state()

        except LocalKnotError as e:
            self.species_error.emit(str(e))
        except Exception as e:
            self.species_error.emit(f"Error saving species: {str(e)}")

    @Slot(str, str)
    def handle_confirm_modify_species(self, old_name: str, new_name: str):
        """
        Actually perform the species renaming in the database.
        Called after user confirms the QMessageBox in the View.
        """
        if not new_name or old_name == new_name:
            self._species_editable = False
            self.species_editable_changed.emit(False)
            return

        try:
            if self.repo.update_species(old_name, new_name):
                # Update internal species list
                self._species = [new_name if s == old_name else s for s in self._species]
                self._species.sort()
                self.species_changed.emit(self._species)
                
                # Update current species if it was the one modified
                if self._current_species == old_name:
                    self._current_species = new_name
                    self.current_species_changed.emit(new_name)

                # Update internal projects list (species name changed)
                for p in self._projects:
                    if p.species == old_name:
                        p.species = new_name
                
                self.species_added.emit(f"Species renamed to {new_name}!")
                
                # Exit edit mode
                self._species_editable = False
                self.species_editable_changed.emit(False)
            else:
                self.species_error.emit("Failed to update species in database.")
        except LocalKnotError as e:
            self.species_error.emit(str(e))
        except Exception as e:
            self.species_error.emit(f"Error updating species: {str(e)}")

    @Slot()
    def handle_delete_project(self):
        """
        Slot called when user clicks 'Delete Project' button.
        Deletes the currently selected project.
        """
        project_to_delete = self._current_project
        if not project_to_delete:
            return

        try:
            if self.repo.delete_project(project_to_delete):
                # Update internal list
                self._projects = [p for p in self._projects if p.name != project_to_delete]
                self.projects_changed.emit(self.project_list)
                
                # Update current project selection
                if self._projects:
                    # Select the first available project
                    new_project = self._projects[0]
                    self.current_project = new_project.name
                    self.current_species = new_project.species
                else:
                    # No projects left
                    self.current_project = ""
                    self.current_species = ""
                
                self.project_saved.emit(f"Project {project_to_delete} deleted.")
        except LocalKnotError as e:
            self.project_error.emit(str(e))
        except Exception as e:
            self.project_error.emit(f"Failed to delete project: {str(e)}")

    @Slot()
    def handle_delete_species(self):
        """
        Slot called when user clicks 'Delete Species' button.
        Deletes the currently selected species if it's not used by any project.
        """
        species_to_delete = self._current_species
        if not species_to_delete:
            return

        # Check if used by any project
        if any(p.species == species_to_delete for p in self._projects):
            self.species_error.emit(f"Cannot delete {species_to_delete}: it is used by some projects.")
            return

        try:
            if self.repo.delete_species(species_to_delete):
                if species_to_delete in self._species:
                    self._species.remove(species_to_delete)
                    self.species_changed.emit(self._species)
                
                # Update selection
                if self._species:
                    self.current_species = self._species[0]
                else:
                    self.current_species = ""
                
                self.species_added.emit(f"Species {species_to_delete} deleted.")
                self._update_species_actions_state()
        except LocalKnotError as e:
            self.species_error.emit(str(e))
        except Exception as e:
            self.species_error.emit(f"Failed to delete species: {str(e)}")

    @Slot()
    def handle_modify_project(self):
        """
        Slot called when user clicks 'Modify Project' button.
        """
        if not self._current_project:
            self.project_error.emit("Please select a project to modify.")
            return

        self._is_modifying = True
        self._original_project_name = self._current_project

        # Trigger modify mode in view to restrict combo box dropdown
        self.project_modify_mode.emit(True)

        self._project_editable = True
        self.project_editable_changed.emit(True)

        # Update species actions state (enables selection and + button)
        self._update_species_actions_state()
        
        self.save_enabled_changed.emit(True)
        self.navigation_enabled_changed.emit(False)

    @Slot()
    def handle_previous_project(self):
        """Select the previous project in the list."""
        if not self._projects or not self._current_project:
            return
            
        current_index = -1
        for i, p in enumerate(self._projects):
            if p.name == self._current_project:
                current_index = i
                break
                
        if current_index > 0:
            new_project = self._projects[current_index - 1]
            self.current_project = new_project.name

    @Slot()
    def handle_next_project(self):
        """Select the next project in the list."""
        if not self._projects or not self._current_project:
            return
            
        current_index = -1
        for i, p in enumerate(self._projects):
            if p.name == self._current_project:
                current_index = i
                break
                
        if current_index >= 0 and current_index < len(self._projects) - 1:
            new_project = self._projects[current_index + 1]
            self.current_project = new_project.name

    @Slot()
    def handle_export_project(self):
        """
        Slot called when user clicks 'Export' button.
        Emits export_requested to be handled by the MainWindow where
        we can check the status of boards and knots viewmodels.
        """
        if not self._current_project:
            self.export_error.emit("No project selected to export.")
            return
        
        self.export_requested.emit()

    @Slot(object, object)
    def initialize_import_manager(self, board_repo, knot_repo):
        """Initialize the import manager with required repositories."""
        self._import_manager = ImportManager(self.repo, board_repo, knot_repo)
    def project_exists(self, name: str) -> bool:
        """Check if a project name already exists in the database."""
        return self.repo.project_exists(name)

    def is_valid_export_file(self, file_path: str) -> bool:
        """Check if the file is a valid KnotVision export."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if not lines:
                    return False
                
                # Check first line for old format, or third line for new format
                header_line = lines[0]
                if len(lines) > 2 and lines[0].startswith("ProjectName;") and lines[1].startswith("Species;"):
                    header_line = lines[2]
                    
                headers = [h.strip() for h in header_line.split(";")]
                if "No_Board" not in headers:
                    return False
            return True
        except Exception:
            return False

    def guess_species(self, file_path: str, project_name: str) -> Optional[str]:
        """
        Attempt to extract species from the file if it has the 'Species' column.
        If not found, falls back to parsing the project name for legacy projects.
        Returns None if both fail, triggering the UI prompt.
        """
        # 1. Try to get it from the file directly (new export format)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    if lines[1].startswith("Species;"):
                        return lines[1].split(";", 1)[1].strip()
                    
                    # Fallback for old check if it ever existed
                    header = lines[0].split(";")
                    if "Species" in header:
                        idx = header.index("Species")
                        first_data_row = lines[1].split(";")
                        if idx < len(first_data_row):
                            val = first_data_row[idx].strip()
                            if val:
                                return val
        except Exception:
            pass
            
        # 2. Fallback: Parse the project name (legacy format)
        # Format expects: ..._'codice specie'_...
        species_map = {
            "ctsv": "Castanea sativa",
            "pntd": "Pinus taeda",
            "pnnn": "Pinus nigra",
            "pnnl": "Pinus nigra laricio",
            "fasy": "Fagus sylvatica",
            "paul": "Paulonia",
            "psmn": "Pseudotsuga menziesii",
            "qcxe": "Quercia",
            "lasi": "Larice siberiano",
            "pnsy": "Pino silvestre"
        }
        
        parts = project_name.split("_")
        if len(parts) > 1:
            code = parts[1].strip().lower()
            if code in species_map:
                return species_map[code]
                
        return None
        
    @Slot(str, str, str)
    def execute_import(self, file_path: str, project_name: str, species: str):
        """
        Execute the import for a specific file.
        """
        if not self._import_manager:
            self.import_error.emit("Import Manager not initialized.")
            return
            
        try:
            success = self._import_manager.parse_and_import(file_path, project_name, species)
            if success:
                # Reload projects and species
                self._load_projects_from_db()
                self._load_species_from_db()
                self.import_success.emit(f"Successfully imported {project_name}.")
        except Exception as e:
            self.import_error.emit(str(e))

    # ==================== PRIVATE METHODS ====================

    def _update_species_actions_state(self):
        """Update the enabled state of species actions based on current selection and project state."""
        has_selection = bool(self._current_species)
        is_project_editing = self._project_editable
        
        # 1. Pencil (Modify) is always enabled if a species is selected
        self.species_modify_enabled.emit(has_selection)
        
        # 2. Add (+) and Delete (Trash) are enabled only during project editing
        self.species_add_enabled.emit(is_project_editing)
        self.species_delete_enabled.emit(is_project_editing and has_selection)
        
        # 3. ComboBox interaction is enabled only during project editing
        self.species_enabled_changed.emit(is_project_editing)

    def _load_projects_from_db(self):
        """Load projects from database."""
        try:
            self._projects = self.repo.get_all_projects()
            print(f"DEBUG: Loaded {len(self._projects)} projects from DB")
            for p in self._projects:
                print(f"DEBUG: Project: {p.name} ({p.species})")
            self.projects_changed.emit(self.project_list)
            
            # Synchronize initial state: select first project if none selected
            if self._projects and not self._current_project:
                first_project = self._projects[0].name
                self._current_project = first_project
                self.current_project_changed.emit(first_project)
                
                self._current_species = self._projects[0].species
                self.current_species_changed.emit(self._current_species)
                
        except LocalKnotError as e:
            print(f"DEBUG: Failed to load projects: {str(e)}")
            self.project_error.emit(str(e))
        except Exception as e:
            print(f"DEBUG: Failed to load projects: {str(e)}")
            self.project_error.emit(f"Failed to load projects: {str(e)}")

    def _load_species_from_db(self):
        """Load species from the dedicated species table."""
        try:
            self._species = self.repo.get_all_species()
            self.species_changed.emit(self._species)
        except LocalKnotError as e:
            self.species_error.emit(str(e))
        except Exception as e:
            self.species_error.emit(f"Failed to load species: {str(e)}")

    @Slot(str)
    def handle_add_species_direct(self, species_name: str):
        """
        Actually add a species to the database (called after validation).
        """
        try:
            if self.repo.add_species(species_name):
                if species_name not in self._species:
                    self._species.append(species_name)
                    self._species.sort()
                    self.species_changed.emit(self._species)
                    self.species_added.emit(f"Species {species_name} added!")
        except LocalKnotError as e:
            self.species_error.emit(str(e))
        except Exception as e:
            self.species_error.emit(f"Failed to add species: {str(e)}")
