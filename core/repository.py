"""
Repository Pattern for Data Access.

Provides a clean interface between ViewModels and the database layer.
This abstraction allows ViewModels to NOT know about SQLite directly.

Pattern: Repository
├─ ProjectRepository: Handles Project CRUD operations
├─ BoardRepository: Handles Board CRUD operations
└─ KnotRepository: Handles Knot CRUD operations

"""

import sqlite3
from functools import wraps
from typing import List, Optional
from core.database import DatabaseManager
from mvvm.models import Project, Board, Knot
from core.exceptions import DatabaseError, DuplicateEntityError, ForeignKeyError


def handle_db_errors(func):
    """Decorator to catch SQLite errors and raise custom LocalKnot exceptions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.IntegrityError as e:
            error_msg = str(e).upper()
            if "UNIQUE" in error_msg:
                raise DuplicateEntityError("This element already exists in the database.") from e
            if "FOREIGN KEY" in error_msg:
                raise ForeignKeyError("Invalid operation: reference to a non-existent element.") from e
            raise DatabaseError("Data integrity error in the database.") from e
        except sqlite3.Error as e:
            raise DatabaseError(f"Database error: {str(e)}") from e
    return wrapper


class ProjectRepository:
    """
    Repository for Project data operations.

    Provides CRUD interface for Project entities.
    Abstracts SQLite operations away from ViewModel.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    @handle_db_errors
    def get_all_projects(self) -> List[Project]:
        """
        Get all projects from database.

        Returns:
            List[Project]: List of all projects
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_project, species FROM project")
            rows = cursor.fetchall()
            return [Project(name=row[0], species=row[1]) for row in rows]

    @handle_db_errors
    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """
        Get a specific project by ID.

        Args:
            project_id: Project ID to retrieve

        Returns:
            Optional[Project]: Project if found, None otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_project, species FROM project WHERE id_project = ?", (project_id,))
            row = cursor.fetchone()
            if row:
                return Project(name=row[0], species=row[1])
            return None

    @handle_db_errors
    def add_project(self, project: Project) -> bool:
        """
        Add a new project to database.
        Ensures species exists in the species table first.

        Args:
            project: Project instance to add

        Returns:
            bool: True if successful, False otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure species exists
            cursor.execute("INSERT OR IGNORE INTO species (name) VALUES (?)", (project.species,))
            
            cursor.execute(
                "INSERT INTO project (id_project, species) VALUES (?, ?)",
                (project.name, project.species)
            )
            conn.commit()
        return True

    @handle_db_errors
    def update_project(self, old_project_name: str, project: Project) -> bool:
        """
        Update an existing project and cascade renaming if necessary.
        Ensures species exists in the species table first.

        Args:
            old_project_name: The original name of the project
            project: Project instance with updated data

        Returns:
            bool: True if successful, False otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            if old_project_name != project.name:
                # Foreign keys must be disabled before ANY DML statement starts the transaction
                cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Ensure species exists
            cursor.execute("INSERT OR IGNORE INTO species (name) VALUES (?)", (project.species,))

            if old_project_name != project.name:
                # Rename project and manually cascade to boards and knots
                
                cursor.execute(
                    "UPDATE project SET id_project = ?, species = ? WHERE id_project = ?",
                    (project.name, project.species, old_project_name)
                )
                cursor.execute(
                    "UPDATE board SET id_project = ? WHERE id_project = ?",
                    (project.name, old_project_name)
                )
                cursor.execute(
                    "UPDATE knot SET id_project = ? WHERE id_project = ?",
                    (project.name, old_project_name)
                )
                
                cursor.execute("PRAGMA foreign_keys = ON")
            else:
                # Just update species
                cursor.execute(
                    "UPDATE project SET species = ? WHERE id_project = ?",
                    (project.species, old_project_name)
                )
            conn.commit()
        return True

    @handle_db_errors
    def get_all_species(self) -> List[str]:
        """Get all species names from the species table."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM species ORDER BY name ASC")
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    @handle_db_errors
    def add_species(self, species_name: str) -> bool:
        """Add a new species to the species table."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO species (name) VALUES (?)", (species_name,))
            conn.commit()
        return True

    @handle_db_errors
    def update_species(self, old_name: str, new_name: str) -> bool:
        """
        Rename a species and update all projects using it.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Update species table
            cursor.execute("UPDATE species SET name = ? WHERE name = ?", (new_name, old_name))
            # 2. Update project table (manual cascade if not in schema)
            cursor.execute("UPDATE project SET species = ? WHERE species = ?", (new_name, old_name))
            conn.commit()
        return True

    @handle_db_errors
    def delete_species(self, species_name: str) -> bool:
        """
        Delete a species. 
        Note: foreign key constraints might prevent this if projects still use it.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM species WHERE name = ?", (species_name,))
            conn.commit()
        return True

    @handle_db_errors
    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project (cascades to boards and knots).

        Args:
            project_id: Project ID to delete

        Returns:
            bool: True if successful, False otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM project WHERE id_project = ?", (project_id,))
            conn.commit()
        return True

    def project_exists(self, project_id: str) -> bool:
        """
        Check if a project exists.

        Args:
            project_id: Project ID to check

        Returns:
            bool: True if exists, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM project WHERE id_project = ? LIMIT 1", (project_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error:
            return False


class BoardRepository:
    """
    Repository for Board data operations.

    Provides CRUD interface for Board entities within a Project.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager

    @handle_db_errors
    def get_all_boards(self, project_id: str) -> List[Board]:
        """Get all boards for a specific project."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_board, id_project, height, base, length, testpos, comment FROM board WHERE id_project = ?", (project_id,))
            rows = cursor.fetchall()
            return [Board(board_no=row[0], height=int(row[2]), base=int(row[3]), length=row[4], test_position=row[5], comment=row[6]) for row in rows]

    @handle_db_errors
    def get_board_by_id(self, board_id: str, project_id: str) -> Optional[Board]:
        """Get a specific board by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_board, id_project, height, base, length, testpos, comment FROM board WHERE id_board = ? AND id_project = ?", (board_id, project_id))
            row = cursor.fetchone()
            if row:
                return Board(board_no=row[0], height=int(row[2]), base=int(row[3]), length=row[4], test_position=row[5], comment=row[6])
            return None

    @handle_db_errors
    def add_board(self, board: Board, project_id: str) -> bool:
        """Add a new board to database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO board (id_board, id_project, height, base, length, testpos, comment) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (board.board_no, project_id, board.height, board.base, board.length, board.test_position, board.comment)
            )
            conn.commit()
        return True

    @handle_db_errors
    def update_board(self, board: Board, project_id: str) -> bool:
        """Update an existing board."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE board SET height = ?, base = ?, length = ?, testpos = ?, comment = ? WHERE id_board = ? AND id_project = ?",
                (board.height, board.base, board.length, board.test_position, board.comment, board.board_no, project_id)
            )
            conn.commit()
        return True

    @handle_db_errors
    def delete_board(self, board_id: str, project_id: str) -> bool:
        """Delete a board (cascades to knots)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM board WHERE id_board = ? AND id_project = ?", (board_id, project_id))
            conn.commit()
        return True

    def board_exists(self, board_id: str, project_id: str) -> bool:
        """Check if a board exists."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM board WHERE id_board = ? AND id_project = ? LIMIT 1", (board_id, project_id))
                return cursor.fetchone() is not None
        except sqlite3.Error:
            return False


class KnotRepository:
    """
    Repository for Knot data operations.

    Provides CRUD interface for Knot entities within a Board.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager

    @handle_db_errors
    def get_all_knots(self, board_id: str, project_id: str) -> List[Knot]:
        """Get all knots for a specific board."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_nodo, id_board, x, pith_z, pith_y, comment, pruned_knot, pruned_z1, pruned_y1, pruned_z2, pruned_y2, "
                "side1_z1, side1_z2, side1_dmin, side2_z1, side2_z2, side2_dmin, "
                "side3_z1, side3_z2, side3_dmin, side4_z1, side4_z2, side4_dmin "
                "FROM knot WHERE id_board = ? AND id_project = ?", 
                (board_id, project_id)
            )
            rows = cursor.fetchall()
            return [
                Knot(
                    knot_no=row[0], x=row[2], pith_z=row[3], pith_y=row[4], comment=row[5], is_pruned_knot=row[6],
                    pruned_z1=row[7], pruned_y1=row[8], pruned_z2=row[9], pruned_y2=row[10],
                    side1_z1=row[11], side1_z2=row[12], side1_dmin=row[13],
                    side2_z1=row[14], side2_z2=row[15], side2_dmin=row[16],
                    side3_z1=row[17], side3_z2=row[18], side3_dmin=row[19],
                    side4_z1=row[20], side4_z2=row[21], side4_dmin=row[22]
                ) for row in rows
            ]

    @handle_db_errors
    def get_knot_by_id(self, knot_id: str, board_id: str, project_id: str) -> Optional[Knot]:
        """Get a specific knot by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_nodo, id_board, x, pith_z, pith_y, comment, pruned_knot, pruned_z1, pruned_y1, pruned_z2, pruned_y2, "
                "side1_z1, side1_z2, side1_dmin, side2_z1, side2_z2, side2_dmin, "
                "side3_z1, side3_z2, side3_dmin, side4_z1, side4_z2, side4_dmin "
                "FROM knot WHERE id_nodo = ? AND id_board = ? AND id_project = ?", 
                (knot_id, board_id, project_id)
            )
            row = cursor.fetchone()
            if row:
                return Knot(
                    knot_no=row[0], x=row[2], pith_z=row[3], pith_y=row[4], comment=row[5], is_pruned_knot=row[6],
                    pruned_z1=row[7], pruned_y1=row[8], pruned_z2=row[9], pruned_y2=row[10],
                    side1_z1=row[11], side1_z2=row[12], side1_dmin=row[13],
                    side2_z1=row[14], side2_z2=row[15], side2_dmin=row[16],
                    side3_z1=row[17], side3_z2=row[18], side3_dmin=row[19],
                    side4_z1=row[20], side4_z2=row[21], side4_dmin=row[22]
                )
            return None

    @handle_db_errors
    def add_knot(self, knot: Knot, board_id: str, project_id: str) -> bool:
        """Add a new knot."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO knot (id_nodo, id_board, id_project, x, pith_z, pith_y, comment, pruned_knot, pruned_z1, pruned_y1, pruned_z2, pruned_y2, "
                "side1_z1, side1_z2, side1_dmin, side2_z1, side2_z2, side2_dmin, "
                "side3_z1, side3_z2, side3_dmin, side4_z1, side4_z2, side4_dmin) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (knot.knot_no, board_id, project_id, knot.x, knot.pith_z, knot.pith_y, knot.comment, knot.is_pruned_knot, knot.pruned_z1, knot.pruned_y1, knot.pruned_z2, knot.pruned_y2,
                 knot.side1_z1, knot.side1_z2, knot.side1_dmin,
                 knot.side2_z1, knot.side2_z2, knot.side2_dmin,
                 knot.side3_z1, knot.side3_z2, knot.side3_dmin,
                 knot.side4_z1, knot.side4_z2, knot.side4_dmin)
            )
            conn.commit()
        return True

    @handle_db_errors
    def update_knot(self, knot: Knot, board_id: str, project_id: str) -> bool:
        """Update an existing knot."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE knot SET x = ?, pith_z = ?, pith_y = ?, comment = ?, pruned_knot = ?, pruned_z1 = ?, pruned_y1 = ?, pruned_z2 = ?, pruned_y2 = ?, "
                "side1_z1 = ?, side1_z2 = ?, side1_dmin = ?, "
                "side2_z1 = ?, side2_z2 = ?, side2_dmin = ?, "
                "side3_z1 = ?, side3_z2 = ?, side3_dmin = ?, "
                "side4_z1 = ?, side4_z2 = ?, side4_dmin = ? "
                "WHERE id_nodo = ? AND id_board = ? AND id_project = ?",
                (knot.x, knot.pith_z, knot.pith_y, knot.comment, knot.is_pruned_knot, knot.pruned_z1, knot.pruned_y1, knot.pruned_z2, knot.pruned_y2,
                 knot.side1_z1, knot.side1_z2, knot.side1_dmin,
                 knot.side2_z1, knot.side2_z2, knot.side2_dmin,
                 knot.side3_z1, knot.side3_z2, knot.side3_dmin,
                 knot.side4_z1, knot.side4_z2, knot.side4_dmin,
                 knot.knot_no, board_id, project_id)
            )
            conn.commit()
        return True

    @handle_db_errors
    def delete_knot(self, knot_id: str, board_id: str, project_id: str) -> bool:
        """Delete a knot."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knot WHERE id_nodo = ? AND id_board = ? AND id_project = ?", (knot_id, board_id, project_id))
            conn.commit()
        return True

    def knot_exists(self, knot_id: str, board_id: str, project_id: str) -> bool:
        """Check if a knot exists."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM knot WHERE id_nodo = ? AND id_board = ? AND id_project = ? LIMIT 1", (knot_id, board_id, project_id))
                return cursor.fetchone() is not None
        except sqlite3.Error:
            return False

    @handle_db_errors
    def rename_knot_id(self, old_id: str, new_id: str, board_id: str, project_id: str) -> bool:
        """Rename a knot's id_nodo (used for renumbering after deletion)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE knot SET id_nodo = ? WHERE id_nodo = ? AND id_board = ? AND id_project = ?",
                (new_id, old_id, board_id, project_id)
            )
            conn.commit()
        return True

