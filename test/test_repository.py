import pytest
from core.database import DatabaseManager
from core.repository import ProjectRepository, BoardRepository, KnotRepository
from core.exceptions import DuplicateEntityError
from mvvm.models import Project, Board, Knot

@pytest.fixture
def db_manager(tmp_path):
    db_file = tmp_path / "test_local_knot.db"
    return DatabaseManager(db_name=str(db_file))

####### --project-- #######

def test_add_and_get_project(db_manager):
    repo = ProjectRepository(db_manager)
    proj = Project(name = "project1", species = "species1")

    result = repo.add_project(proj)
    assert result is True

    projects = repo.get_all_projects()
    assert len(projects) == 1

    retrieved_proj = projects[0]
    assert retrieved_proj.name == proj.name
    assert retrieved_proj.species == proj.species

    searched_project = repo.get_project_by_id("project1")
    assert searched_project is not None
    assert searched_project.name == proj.name
    assert searched_project.species == proj.species

    
def test_update_project(db_manager):
    repo = ProjectRepository(db_manager)
    proj = Project(name = "project1", species = "species1")

    repo.add_project(proj)

    updated_proj = Project(name = "project1", species = "species2")

    repo.update_project("project1", updated_proj)

    retrieved_proj = repo.get_project_by_id("project1")
    assert retrieved_proj is not None
    assert retrieved_proj.name == updated_proj.name
    assert retrieved_proj.species == updated_proj.species

def test_delete_and_exists_project(db_manager):
    repo = ProjectRepository(db_manager)
    proj = Project(name = "project1", species = "species1")

    repo.add_project(proj)
    assert repo.project_exists("project1") is True

    repo.delete_project("project1")
    
    retrieved_proj = repo.get_project_by_id("project1")
    assert retrieved_proj is None

    assert repo.project_exists("project1") is False
    

####### --board-- #######

@pytest.fixture
def sample_project(db_manager):
    proj_repo = ProjectRepository(db_manager)
    proj = Project("project1", "species1")
    proj_repo.add_project(proj)
    return proj

def test_add_and_get_boards(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board = Board(board_no = 1, height = 10, base = 10, length = 10)
    board_repo.add_board(board, sample_project.name)

    boards = board_repo.get_all_boards(sample_project.name)
    assert len(boards) == 1

    retrieved_board = boards[0]
    assert retrieved_board.board_no == board.board_no
    assert retrieved_board.height == board.height
    assert retrieved_board.base == board.base
    assert retrieved_board.length == board.length

def test_get_board_by_id(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board = Board(board_no = 1, height = 10, base = 10, length = 10)
    board_repo.add_board(board, sample_project.name)

    retrieved_board = board_repo.get_board_by_id(1, sample_project.name)

    assert retrieved_board.board_no == board.board_no
    assert retrieved_board.height == board.height
    assert retrieved_board.base == board.base
    assert retrieved_board.length == board.length

    retrieved_board = board_repo.get_board_by_id(2, sample_project.name)
    assert retrieved_board is None


def test_update_board(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board = Board(board_no=1, height=10, base=10, length=10)
    board_repo.add_board(board, sample_project.name)

    updated_board = Board(board_no=1, height=20, base=15, length=100)
    board_repo.update_board(updated_board, sample_project.name)

    retrieved_board = board_repo.get_board_by_id(1, sample_project.name)
    assert retrieved_board is not None
    assert retrieved_board.height == updated_board.height
    assert retrieved_board.base == updated_board.base
    assert retrieved_board.length == updated_board.length


def test_delete_and_exists_board(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board = Board(board_no=1, height=10, base=10, length=10)

    assert board_repo.board_exists(1, sample_project.name) is False

    board_repo.add_board(board, sample_project.name)
    assert board_repo.board_exists(1, sample_project.name) is True

    board_repo.delete_board(1, sample_project.name)

    retrieved_board = board_repo.get_board_by_id(1, sample_project.name)
    assert retrieved_board is None

    assert board_repo.board_exists(1, sample_project.name) is False

####### --knots-- #######

@pytest.fixture
def sample_board(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board = Board(board_no = 1, height = 10, base = 10, length = 10)
    board_repo.add_board(board, sample_project.name)
    return board


def test_add_and_get_knots(db_manager, sample_board, sample_project):
    knot_repo = KnotRepository(db_manager)
    knot = Knot(knot_no = 1, x = 10, pith_z = 10, pith_y = 10, is_pruned_knot = False, pruned_z1 = 10, pruned_y1 = 10, pruned_z2 = 10, pruned_y2 = 10, comment = "", side1_z1 = 10, side1_z2 = 10, side1_dmin = 10, side2_z1 = 10, side2_z2 = 10, side2_dmin = 10, side3_z1 = 10, side3_z2 = 10, side3_dmin = 10, side4_z1 = 10, side4_z2 = 10, side4_dmin = 10)
    knot_repo.add_knot(knot, sample_board.board_no, sample_project.name)

    knots = knot_repo.get_all_knots(sample_board.board_no, sample_project.name)
    assert len(knots) == 1

    retrieved_knot = knots[0]
    assert retrieved_knot.knot_no == knot.knot_no
    assert retrieved_knot.x == knot.x
    assert retrieved_knot.pith_z == knot.pith_z
    assert retrieved_knot.pith_y == knot.pith_y
    assert retrieved_knot.is_pruned_knot == knot.is_pruned_knot
    assert retrieved_knot.pruned_z1 == knot.pruned_z1
    assert retrieved_knot.pruned_y1 == knot.pruned_y1
    assert retrieved_knot.pruned_z2 == knot.pruned_z2
    assert retrieved_knot.pruned_y2 == knot.pruned_y2
    assert retrieved_knot.comment == knot.comment
    assert retrieved_knot.side1_z1 == knot.side1_z1
    assert retrieved_knot.side1_z2 == knot.side1_z2
    assert retrieved_knot.side1_dmin == knot.side1_dmin
    assert retrieved_knot.side2_z1 == knot.side2_z1
    assert retrieved_knot.side2_z2 == knot.side2_z2
    assert retrieved_knot.side2_dmin == knot.side2_dmin
    assert retrieved_knot.side3_z1 == knot.side3_z1
    assert retrieved_knot.side3_z2 == knot.side3_z2
    assert retrieved_knot.side3_dmin == knot.side3_dmin
    assert retrieved_knot.side4_z1 == knot.side4_z1
    assert retrieved_knot.side4_z2 == knot.side4_z2
    assert retrieved_knot.side4_dmin == knot.side4_dmin

def test_get_knot_by_id(db_manager, sample_board, sample_project):
    knot_repo = KnotRepository(db_manager)
    knot = Knot(knot_no = 1, x = 10, pith_z = 10, pith_y = 10, is_pruned_knot = False, pruned_z1 = 10, pruned_y1 = 10, pruned_z2 = 10, pruned_y2 = 10, comment = "", side1_z1 = 10, side1_z2 = 10, side1_dmin = 10, side2_z1 = 10, side2_z2 = 10, side2_dmin = 10, side3_z1 = 10, side3_z2 = 10, side3_dmin = 10, side4_z1 = 10, side4_z2 = 10, side4_dmin = 10)
    knot_repo.add_knot(knot, sample_board.board_no, sample_project.name)

    retrieved_knot = knot_repo.get_knot_by_id(1, sample_board.board_no, sample_project.name)
    assert retrieved_knot.knot_no == knot.knot_no
    assert retrieved_knot.x == knot.x
    assert retrieved_knot.pith_z == knot.pith_z
    assert retrieved_knot.pith_y == knot.pith_y
    assert retrieved_knot.is_pruned_knot == knot.is_pruned_knot
    assert retrieved_knot.pruned_z1 == knot.pruned_z1
    assert retrieved_knot.pruned_y1 == knot.pruned_y1
    assert retrieved_knot.pruned_z2 == knot.pruned_z2
    assert retrieved_knot.pruned_y2 == knot.pruned_y2
    assert retrieved_knot.comment == knot.comment
    assert retrieved_knot.side1_z1 == knot.side1_z1
    assert retrieved_knot.side1_z2 == knot.side1_z2
    assert retrieved_knot.side1_dmin == knot.side1_dmin
    assert retrieved_knot.side2_z1 == knot.side2_z1
    assert retrieved_knot.side2_z2 == knot.side2_z2
    assert retrieved_knot.side2_dmin == knot.side2_dmin
    assert retrieved_knot.side3_z1 == knot.side3_z1
    assert retrieved_knot.side3_z2 == knot.side3_z2
    assert retrieved_knot.side3_dmin == knot.side3_dmin
    assert retrieved_knot.side4_z1 == knot.side4_z1
    assert retrieved_knot.side4_z2 == knot.side4_z2
    assert retrieved_knot.side4_dmin == knot.side4_dmin

def test_update_knot(db_manager, sample_board, sample_project):
    knot_repo = KnotRepository(db_manager)
    knot = Knot(knot_no = 1, x = 10, pith_z = 10, pith_y = 10, is_pruned_knot = False, pruned_z1 = 10, pruned_y1 = 10, pruned_z2 = 10, pruned_y2 = 10, comment = "", side1_z1 = 10, side1_z2 = 10, side1_dmin = 10, side2_z1 = 10, side2_z2 = 10, side2_dmin = 10, side3_z1 = 10, side3_z2 = 10, side3_dmin = 10, side4_z1 = 10, side4_z2 = 10, side4_dmin = 10)
    knot_repo.add_knot(knot, sample_board.board_no, sample_project.name)

    updated_knot = Knot(knot_no = 1, x = 20, pith_z = 20, pith_y = 20, is_pruned_knot = True, pruned_z1 = 20, pruned_y1 = 20, pruned_z2 = 20, pruned_y2 = 20, comment = "", side1_z1 = 20, side1_z2 = 20, side1_dmin = 20, side2_z1 = 20, side2_z2 = 20, side2_dmin = 20, side3_z1 = 20, side3_z2 = 20, side3_dmin = 20, side4_z1 = 20, side4_z2 = 20, side4_dmin = 20)
    knot_repo.update_knot(updated_knot, sample_board.board_no, sample_project.name)

    retrieved_knot = knot_repo.get_knot_by_id(1, sample_board.board_no, sample_project.name)
    assert retrieved_knot.knot_no == updated_knot.knot_no
    assert retrieved_knot.x == updated_knot.x
    assert retrieved_knot.pith_z == updated_knot.pith_z
    assert retrieved_knot.pith_y == updated_knot.pith_y
    assert retrieved_knot.is_pruned_knot == updated_knot.is_pruned_knot
    assert retrieved_knot.pruned_z1 == updated_knot.pruned_z1
    assert retrieved_knot.pruned_y1 == updated_knot.pruned_y1
    assert retrieved_knot.pruned_z2 == updated_knot.pruned_z2
    assert retrieved_knot.pruned_y2 == updated_knot.pruned_y2
    assert retrieved_knot.comment == updated_knot.comment
    assert retrieved_knot.side1_z1 == updated_knot.side1_z1
    assert retrieved_knot.side1_z2 == updated_knot.side1_z2
    assert retrieved_knot.side1_dmin == updated_knot.side1_dmin
    assert retrieved_knot.side2_z1 == updated_knot.side2_z1
    assert retrieved_knot.side2_z2 == updated_knot.side2_z2
    assert retrieved_knot.side2_dmin == updated_knot.side2_dmin
    assert retrieved_knot.side3_z1 == updated_knot.side3_z1
    assert retrieved_knot.side3_z2 == updated_knot.side3_z2
    assert retrieved_knot.side3_dmin == updated_knot.side3_dmin
    assert retrieved_knot.side4_z1 == updated_knot.side4_z1
    assert retrieved_knot.side4_z2 == updated_knot.side4_z2
    assert retrieved_knot.side4_dmin == updated_knot.side4_dmin

def test_delete_and_exists_knot(db_manager, sample_board, sample_project):
    knot_repo = KnotRepository(db_manager)
    knot = Knot(knot_no = 1, x = 10, pith_z = 10, pith_y = 10, is_pruned_knot = False, pruned_z1 = 10, pruned_y1 = 10, pruned_z2 = 10, pruned_y2 = 10, comment = "", side1_z1 = 10, side1_z2 = 10, side1_dmin = 10, side2_z1 = 10, side2_z2 = 10, side2_dmin = 10, side3_z1 = 10, side3_z2 = 10, side3_dmin = 10, side4_z1 = 10, side4_z2 = 10, side4_dmin = 10)
    knot_repo.add_knot(knot, sample_board.board_no, sample_project.name)
    assert knot_repo.knot_exists(1, sample_board.board_no, sample_project.name) is True

    knot_repo.delete_knot(1, sample_board.board_no, sample_project.name)
    retrieved_knot = knot_repo.get_knot_by_id(1, sample_board.board_no, sample_project.name)
    assert retrieved_knot is None

    assert knot_repo.knot_exists(1, sample_board.board_no, sample_project.name) is False

##-----------------##

def test_cascade_deletion(db_manager, sample_project, sample_board):
    knot_repo = KnotRepository(db_manager)
    proj_repo = ProjectRepository(db_manager)
    board_repo = BoardRepository(db_manager)

    knot = Knot(knot_no=1, x=10)
    knot_repo.add_knot(knot, sample_board.board_no, sample_project.name)

    proj_repo.delete_project(sample_project.name)

    assert board_repo.board_exists(sample_board.board_no, sample_project.name) is False
    assert knot_repo.knot_exists(1, sample_board.board_no, sample_project.name) is False
