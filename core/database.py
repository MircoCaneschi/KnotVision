import sqlite3
import sys
import os
import platform
from pathlib import Path
from core.path_utils import get_app_data_dir


class DatabaseManager:
    def __init__(self, db_name="LocalKnotData.db"):
        self.db_path = self._get_db_path(db_name)
        self.create_tables()

    @staticmethod
    def _get_db_path(db_name):
        """
        Determines the database path using a hybrid approach:
        1. Try to use a 'data' folder next to the executable / in the project root (Portable mode).
        2. Fall back to the system's standard AppData/Application Support if the local path isn't writable.
        """
        # 1. Try Local Portable Path
        try:
            if getattr(sys, 'frozen', False):
                # When frozen, store data next to the .exe for true portability
                portable_root = Path(sys.executable).resolve().parent
            else:
                portable_root = Path(__file__).resolve().parent.parent
                
            local_data_dir = portable_root / "data"
            
            # Ensure directory exists
            local_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Test writability by creating a temporary file
            test_file = local_data_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            return local_data_dir / db_name
            
        except (OSError, PermissionError):
            # 2. Fallback to System Standard Path (Standard Installation)
            app_dir = get_app_data_dir("KnotCalc")
            return app_dir / db_name

    def get_connection(self):
        # Use the dynamic path
        conn = sqlite3.connect(str(self.db_path))
        # # CRITICAL: Enable foreign keys, otherwise ON DELETE CASCADE will not work
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def create_tables(self):
        # with the "with" block, the code automatically commits or rollback the transaction, even if an error occurs
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # species table (NEW)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS species (
                    name TEXT PRIMARY KEY
                )
            ''')

            # project table (UPDATED with Foreign Key)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project (
                    id_project TEXT PRIMARY KEY,
                    species TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (species) REFERENCES species (name) ON UPDATE CASCADE
                )
            ''')

            # Check if we need to migrate existing species from project to species table
            cursor.execute("SELECT DISTINCT species FROM project")
            existing_species = cursor.fetchall()
            for row in existing_species:
                cursor.execute("INSERT OR IGNORE INTO species (name) VALUES (?)", (row[0],))

            # BOARD table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS board (
                    id_board INTEGER NOT NULL,
                    id_project TEXT NOT NULL,
                    height INTEGER NOT NULL,
                    base INTEGER NOT NULL,
                    length INTEGER NOT NULL,
                    testpos INTEGER ,
                    comment TEXT,
                    image_path TEXT,
                    PRIMARY KEY (id_board, id_project),
                    FOREIGN KEY (id_project) REFERENCES project (id_project) ON DELETE CASCADE
                )
            ''')

            # --- Migration: convert height/base from REAL to INTEGER if needed ---
            cursor.execute("PRAGMA table_info(board)")
            col_types = {row[1]: row[2] for row in cursor.fetchall()}
            if col_types.get('height', '').upper() == 'REAL' or col_types.get('base', '').upper() == 'REAL':
                cursor.execute("UPDATE board SET height = CAST(ROUND(height) AS INTEGER), "
                               "base = CAST(ROUND(base) AS INTEGER)")


            # KNOT table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knot (
                    id_nodo INTEGER NOT NULL,
                    id_board INTEGER NOT NULL,
                    id_project TEXT NOT NULL,
                    x INTEGER NOT NULL,
                    pith_z INTEGER,
                    pith_y INTEGER,
                    comment TEXT,
                    pruned_knot BOOLEAN,
                    pruned_z1 INTEGER,
                    pruned_y1 INTEGER,
                    pruned_z2 INTEGER,
                    pruned_y2 INTEGER,
                    
                    side1_z1 INTEGER,
                    side1_z2 INTEGER,
                    side1_dmin INTEGER,
                    
                    side2_z1 INTEGER,
                    side2_z2 INTEGER,
                    side2_dmin INTEGER,
                    
                    side3_z1 INTEGER,
                    side3_z2 INTEGER,
                    side3_dmin INTEGER,
                    
                    side4_z1 INTEGER,
                    side4_z2 INTEGER,
                    side4_dmin INTEGER,
                    PRIMARY KEY (id_nodo, id_board, id_project),
                    FOREIGN KEY (id_board, id_project) REFERENCES board (id_board, id_project) ON DELETE CASCADE
                )
            ''')
            conn.commit()

            # --- Migration: rename and add pruned fields ---
            cursor.execute("PRAGMA table_info(knot)")
            col_names = [row[1] for row in cursor.fetchall()]
            
            if 'pruned_z' in col_names:
                cursor.execute("ALTER TABLE knot RENAME COLUMN pruned_z TO pruned_z1")
            if 'pruned_y' in col_names:
                cursor.execute("ALTER TABLE knot RENAME COLUMN pruned_y TO pruned_y1")
                
            cursor.execute("PRAGMA table_info(knot)")
            col_names = [row[1] for row in cursor.fetchall()]
                
            if 'pruned_z1' not in col_names:
                cursor.execute("ALTER TABLE knot ADD COLUMN pruned_z1 INTEGER")
            if 'pruned_y1' not in col_names:
                cursor.execute("ALTER TABLE knot ADD COLUMN pruned_y1 INTEGER")
            if 'pruned_z2' not in col_names:
                cursor.execute("ALTER TABLE knot ADD COLUMN pruned_z2 INTEGER")
            if 'pruned_y2' not in col_names:
                cursor.execute("ALTER TABLE knot ADD COLUMN pruned_y2 INTEGER")
            conn.commit()



    #--------TRANSACTIONS---------

    def add_project_db(self, id_project, species, db_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO project (id_project, species) VALUES (?, ?)
            ''', (id_project, species))
            conn.commit()