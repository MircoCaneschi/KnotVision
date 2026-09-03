import pytest
from core.board_calculator import BoardCalculator
from core.database import DatabaseManager
from core.repository import ProjectRepository, BoardRepository, KnotRepository
from mvvm.models import Project, Board, Knot
from mvvm.viewmodels.projects_viewmodel import ProjectsViewModel
from mvvm.viewmodels.boards_viewmodel import BoardsViewModel
from mvvm.viewmodels.knots_viewmodel import KnotsViewModel
from mvvm.viewmodels.virtual_board_vm import VirtualBoardViewModel
from core.ai.ai_models import Point2D
from mvvm.viewmodels.ai_analysis_vm import AiAnalysisViewModel

@pytest.fixture
def db_manager(tmp_path):
    """Crea un database temporaneo pulito per ogni test."""
    db_file = tmp_path / "test_vm.db"
    return DatabaseManager(db_name=str(db_file))

## -- project_viewmodel -- ##

def test_projects_viewmodel_initial_loading(db_manager):
    repo = ProjectRepository(db_manager)
    repo.add_project(Project(name="project1", species="species1"))
    repo.add_project(Project(name="project2", species="species2"))

    vm = ProjectsViewModel(repository=repo)
    
    assert len(vm.project_list) == 2
    assert vm.project_list == ["project1", "project2"]
    assert vm.species_list == ["species1", "species2"]

def test_project_save_with_existing_species(db_manager):
    repo = ProjectRepository(db_manager)
    repo.add_species("species1")
    vm = ProjectsViewModel(repository=repo)

    vm.handle_new_project()
    vm.current_project = "new_project"
    vm.current_species = "species1"
    vm.handle_save_project()

    assert "new_project" in vm.project_list
    assert "species1" in vm.species_list
    assert repo.project_exists("new_project") is True
    assert repo.get_project_by_id("new_project").species == "species1"

def test_project_save_with_new_species(db_manager):
    repo = ProjectRepository(db_manager)
    vm = ProjectsViewModel(repository=repo)
    #click on new
    vm.handle_new_project()
    vm.current_project = "new_project"
    #click on + (species)
    vm.handle_add_species()
    vm.current_species = "species2"
    #click on save
    vm.handle_save_project()

    assert "new_project" in vm.project_list
    assert "species2" in vm.species_list
    assert repo.project_exists("new_project") is True
    assert repo.get_project_by_id("new_project").species == "species2"

def test_project_delete(db_manager):
    repo = ProjectRepository(db_manager)
    repo.add_project(Project(name="project1", species="species1"))
    vm = ProjectsViewModel(repository=repo)
    
    #select project
    vm.current_project = "project1"
    #click on trash (delete)
    vm.handle_delete_project()

    assert "project1" not in vm.project_list
    assert repo.project_exists("project1") is False

def test_project_modify(db_manager):
    repo = ProjectRepository(db_manager)
    repo.add_project(Project(name="project1", species="species1"))
    repo.add_species("species2")
    vm = ProjectsViewModel(repository=repo)
    
    #select project
    vm.current_project = "project1"
    #click on modify (pencil)
    vm.handle_modify_project()
    vm.current_project = "project2"
    vm.current_species = "species2"
    #click on save
    vm.handle_save_project()

    assert "project1" not in vm.project_list
    assert "project2" in vm.project_list
    assert repo.project_exists("project1") is False
    assert repo.project_exists("project2") is True
    assert repo.get_project_by_id("project2").species == "species2"


def test_project_save_empty_name_fails(db_manager):
    repo = ProjectRepository(db_manager)
    repo.add_species("species1")
    vm = ProjectsViewModel(repository=repo)

    # click on new
    vm.handle_new_project()
    vm.current_project = "   "
    vm.current_species = "species1"
    # click on save
    vm.handle_save_project()

    # verify it was not saved
    assert len(vm.project_list) == 0
    assert repo.project_exists("") is False


def test_project_navigation_next_and_previous(db_manager):
    repo = ProjectRepository(db_manager)
    repo.add_project(Project(name="project1", species="species1"))
    repo.add_project(Project(name="project2", species="species2"))
    vm = ProjectsViewModel(repository=repo)

    # initial project selected is project1
    assert vm.current_project == "project1"

    # navigate next
    vm.handle_next_project()
    assert vm.current_project == "project2"

    # navigate previous
    vm.handle_previous_project()
    assert vm.current_project == "project1"


def test_species_direct_add_and_delete(db_manager):
    repo = ProjectRepository(db_manager)
    vm = ProjectsViewModel(repository=repo)

    # add new species directly
    vm.handle_add_species_direct("new_species")
    assert "new_species" in vm.species_list

    # select and delete the unused species
    vm.current_species = "new_species"
    vm.handle_delete_species()
    assert "new_species" not in vm.species_list


def test_delete_species_used_by_project_is_blocked(db_manager):
    repo = ProjectRepository(db_manager)
    repo.add_project(Project(name="project1", species="species1"))
    vm = ProjectsViewModel(repository=repo)

    # try to delete species1 which is currently used by project1
    vm.current_species = "species1"
    vm.handle_delete_species()

    # species1 must NOT be deleted because it is in use
    assert "species1" in vm.species_list

## -- board_viewmodel -- ##

@pytest.fixture
def  sample_project(db_manager):
    proj_repo = ProjectRepository(db_manager)
    proj = Project(name="project1", species="species1")
    proj_repo.add_project(proj)
    return proj

def test_boards_viewmodel_initial_loading(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board1 = Board(board_no = 1, height = 10, base = 10, length = 10)
    board2 = Board(board_no = 2, height = 20, base = 20, length = 20)
    board_repo.add_board(board1, sample_project.name)
    board_repo.add_board(board2, sample_project.name)
        
    vm = BoardsViewModel(repository=board_repo)
    vm.handle_project_changed(sample_project.name)

    assert len(vm.board_list) == 2
    assert vm.board_list == ["1", "2"]
    assert vm.current_board_no == "1"

def test_board_save(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    vm = BoardsViewModel(repository=board_repo)
    vm.handle_project_changed(sample_project.name)
    
    vm.handle_new_board()
    vm.current_board_no = "1"
    vm.height = 10
    vm.base = 10
    vm.length = 10
    vm.test_position = 1
    vm.comment = "comment"
    
    vm.handle_save_board()
    
    assert vm.board_list == ["1"]
    assert board_repo.board_exists("1", sample_project.name) is True

def test_board_save_empty_board_no_fails(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    vm = BoardsViewModel(repository=board_repo)
    vm.handle_project_changed(sample_project.name)
    
    vm.handle_new_board()
    vm.current_board_no = ""
    vm.height = 10
    vm.base = 10
    vm.length = 10
    vm.test_position = 1
    vm.comment = "comment"
    
    vm.handle_save_board()
    
    assert vm.board_list == []
    assert board_repo.board_exists("", sample_project.name) is False

def test_board_delete(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board1 = Board(board_no = 1, height = 10, base = 10, length = 10)
    board_repo.add_board(board1, sample_project.name)
    
    vm = BoardsViewModel(repository=board_repo)
    vm.handle_project_changed(sample_project.name)
    
    vm.current_board_no = "1"
    vm.handle_delete_board()
    
    assert vm.board_list == []
    assert board_repo.board_exists("1", sample_project.name) is False

def test_prev_next_board_selection(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board1 = Board(board_no = 1, height = 10, base = 10, length = 10)
    board2 = Board(board_no = 2, height = 20, base = 20, length = 20)
    board_repo.add_board(board1, sample_project.name)
    board_repo.add_board(board2, sample_project.name)
    
    vm = BoardsViewModel(repository=board_repo)
    vm.handle_project_changed(sample_project.name)
    
    vm.current_board_no = "1"
    vm.handle_next_board()
    assert vm.current_board_no == "2"

    vm.handle_next_board()
    assert vm.current_board_no == "2"

    vm.handle_previous_board()
    assert vm.current_board_no == "1"

    vm.handle_previous_board()
    assert vm.current_board_no == "1"

def test_board_new(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board1 = Board(board_no = 1, height = 10, base = 10, length = 10)
    board_repo.add_board(board1, sample_project.name)
    
    vm = BoardsViewModel(repository=board_repo)
    vm.handle_project_changed(sample_project.name)
    
    vm.current_board_no = "1"
    vm.handle_new_board()
    assert vm.current_board_no == ''
    assert vm.height == None
    assert vm.base == None
    assert vm.length == None
    assert vm.test_position == None
    assert vm.comment == ''
    assert vm._board_editable == True
    
    vm.handle_save_board()
    assert vm.board_list == ["1"]


## -- knots_viewmodel -- ##

@pytest.fixture
def sample_board(db_manager, sample_project):
    board_repo = BoardRepository(db_manager)
    board1 = Board(board_no=1, height=100, base=50, length=2000.0)
    board_repo.add_board(board1, sample_project.name)
    return board1


def test_knots_viewmodel_initial_loading(db_manager, sample_project, sample_board):
    knot_repo = KnotRepository(db_manager)
    board_repo = BoardRepository(db_manager)
    knot_repo.add_knot(Knot(knot_no=1, x=100, pith_z=20, pith_y=20, side1_z1=10, side1_z2=30, side1_dmin=10), sample_board.board_no, sample_project.name)
    knot_repo.add_knot(Knot(knot_no=2, x=200, pith_z=20, pith_y=20, side1_z1=10, side1_z2=30, side1_dmin=10), sample_board.board_no, sample_project.name)

    vm = KnotsViewModel(repository=knot_repo, board_repo=board_repo)
    vm.handle_project_changed(sample_project.name)
    vm.handle_board_changed(str(sample_board.board_no))

    assert len(vm.knot_list) == 2
    assert vm.knot_list == ["1", "2"]
    assert vm.current_knot_no == "1"


def test_knot_new_and_save(db_manager, sample_project, sample_board):
    knot_repo = KnotRepository(db_manager)
    board_repo = BoardRepository(db_manager)
    vm = KnotsViewModel(repository=knot_repo, board_repo=board_repo)
    vm.handle_project_changed(sample_project.name)
    vm.handle_board_changed(str(sample_board.board_no))

    # Click on "New Knot"
    vm.handle_new_knot()
    assert vm.current_knot_no == "1"
    assert vm._knot_editable is True

    # Fill knot coordinates (X, pith, and at least 1 compiled side)
    vm.x = 150
    vm.pith_z = 20
    vm.pith_y = 20
    vm.side1_z1 = 10
    vm.side1_z2 = 30
    vm.side1_dmin = 10
    vm.comment = "nodo test"

    # Save knot
    vm.handle_save_knot()

    assert vm.knot_list == ["1"]
    assert knot_repo.knot_exists("1", sample_board.board_no, sample_project.name) is True
    saved_knot = knot_repo.get_knot_by_id("1", sample_board.board_no, sample_project.name)
    assert saved_knot is not None
    assert saved_knot.x == 150
    assert saved_knot.pith_z == 20


def test_knot_save_invalid_x_fails(db_manager, sample_project, sample_board):
    knot_repo = KnotRepository(db_manager)
    board_repo = BoardRepository(db_manager)
    vm = KnotsViewModel(repository=knot_repo, board_repo=board_repo)
    vm.handle_project_changed(sample_project.name)
    vm.handle_board_changed(str(sample_board.board_no))

    # Click on new knot and set invalid X <= 0
    vm.handle_new_knot()
    vm.x = 0
    vm.pith_z = 20
    vm.pith_y = 20
    vm.side1_z1 = 10
    vm.side1_z2 = 30
    vm.side1_dmin = 10
    vm.handle_save_knot()

    # Verify not saved
    assert len(vm.knot_list) == 0
    assert knot_repo.knot_exists("1", sample_board.board_no, sample_project.name) is False


def test_knot_modify(db_manager, sample_project, sample_board):
    knot_repo = KnotRepository(db_manager)
    board_repo = BoardRepository(db_manager)
    knot_repo.add_knot(
        Knot(knot_no=1, x=100, pith_z=20, pith_y=20, side1_z1=10, side1_z2=30, side1_dmin=10),
        sample_board.board_no,
        sample_project.name
    )

    vm = KnotsViewModel(repository=knot_repo, board_repo=board_repo)
    vm.handle_project_changed(sample_project.name)
    vm.handle_board_changed(str(sample_board.board_no))

    # Select knot 1 and modify X coordinate
    vm.current_knot_no = "1"
    vm.x = 320
    vm.handle_save_knot()

    # Verify updated in DB
    updated = knot_repo.get_knot_by_id("1", sample_board.board_no, sample_project.name)
    assert updated.x == 320


def test_knot_delete_and_renumbering(db_manager, sample_project, sample_board):
    knot_repo = KnotRepository(db_manager)
    board_repo = BoardRepository(db_manager)
    knot_repo.add_knot(Knot(knot_no=1, x=100, pith_z=20, pith_y=20, side1_z1=10, side1_z2=30, side1_dmin=10), sample_board.board_no, sample_project.name)
    knot_repo.add_knot(Knot(knot_no=2, x=200, pith_z=20, pith_y=20, side1_z1=10, side1_z2=30, side1_dmin=10), sample_board.board_no, sample_project.name)

    vm = KnotsViewModel(repository=knot_repo, board_repo=board_repo)
    vm.handle_project_changed(sample_project.name)
    vm.handle_board_changed(str(sample_board.board_no))

    # Delete knot 1 -> knot 2 must be automatically renumbered to knot 1
    vm.current_knot_no = "1"
    vm.handle_delete_knot()

    assert vm.knot_list == ["1"]
    assert knot_repo.knot_exists("1", sample_board.board_no, sample_project.name) is True
    assert knot_repo.knot_exists("2", sample_board.board_no, sample_project.name) is False


## -- virtual board viewmodel -- ##

def test_virtual_board_vm_empty_input_empty_results():
    calculator = BoardCalculator()
    vm = VirtualBoardViewModel(calculator = calculator, knot_repo = None)
    recived_results = []
    vm.results_updated.connect(lambda res: recived_results.append(res))

    vm.update_results(None, [], None)
    assert len(recived_results) == 1
    assert recived_results[0] == calculator._empty_results()
    assert recived_results[0]["tKnot"] == '0.00'
    
def test_virtual_board_vm_calculates_and_emits_results():
    calculator = BoardCalculator()
    vm = VirtualBoardViewModel(calculator=calculator, knot_repo=None)
    board = Board(board_no=1, height=100, base=50, length=2000.0)
    knot = Knot(knot_no=1, x=100, pith_z=20, pith_y=20, side1_z1=10, side1_z2=30, side1_dmin=10)

    received_results = []
    vm.results_updated.connect(lambda res: received_results.append(res))

    vm.update_results(current_board=board, all_knots=[knot], current_knot=knot)
    assert len(received_results) == 1
    results = received_results[0]
    assert isinstance(results, dict)
    assert "tKnot" in results
    assert "mKAR" in results
    assert "DEB" in results


## -- ai_analysis_viewmodel -- ##

@pytest.fixture
def ai_vm(db_manager, sample_project, sample_board):
    board_repo = BoardRepository(db_manager)
    knot_repo = KnotRepository(db_manager)

    boards_vm = BoardsViewModel(repository=board_repo, knot_repo=knot_repo)
    boards_vm.handle_project_changed(sample_project.name)

    knots_vm = KnotsViewModel(repository=knot_repo, board_repo=board_repo)
    knots_vm.handle_project_changed(sample_project.name)
    knots_vm.handle_board_changed(str(sample_board.board_no))

    vm = AiAnalysisViewModel(analyzer=None, boards_vm=boards_vm, knots_vm=knots_vm)
    return vm, boards_vm, knots_vm


def test_ai_analysis_vm_load_image(ai_vm):
    vm, _, _ = ai_vm

    vm.load_image("board_scan.jpg")

    assert vm.current_image_path == "board_scan.jpg"
    assert vm.unassigned_segments == []
    assert vm.selected_segment_ids == []


def test_ai_analysis_vm_manual_segment_add_and_delete(ai_vm):
    vm, _, _ = ai_vm

    points = [Point2D(10.0, 20.0), Point2D(30.0, 40.0), Point2D(20.0, 50.0)]
    vm.add_manual_segment(points, face_id=1)

    assert len(vm.unassigned_segments) == 1
    seg = vm.unassigned_segments[0]
    assert seg.face_id == 1

    vm.delete_segment(seg.segment_id)
    assert len(vm.unassigned_segments) == 0


def test_ai_analysis_vm_toggle_segment_selection_and_face_constraint(ai_vm):
    vm, _, _ = ai_vm

    p1 = [Point2D(10.0, 10.0), Point2D(20.0, 20.0)]
    p2 = [Point2D(30.0, 30.0), Point2D(40.0, 40.0)]
    p3 = [Point2D(50.0, 50.0), Point2D(60.0, 60.0)]

    vm.add_manual_segment(p1, face_id=1)
    vm.add_manual_segment(p2, face_id=1)
    vm.add_manual_segment(p3, face_id=2)

    seg1_id = vm.unassigned_segments[0].segment_id
    seg2_id = vm.unassigned_segments[1].segment_id
    seg3_id = vm.unassigned_segments[2].segment_id

    # select first segment on face 1
    vm.toggle_segment_selection(seg1_id)
    assert seg1_id in vm.selected_segment_ids

    # try selecting second segment on the SAME face 1 (must be blocked)
    vm.toggle_segment_selection(seg2_id)
    assert seg2_id not in vm.selected_segment_ids

    # select segment on different face 2 (allowed)
    vm.toggle_segment_selection(seg3_id)
    assert seg3_id in vm.selected_segment_ids
    assert len(vm.selected_segment_ids) == 2


def test_ai_analysis_vm_reset_state_on_board_change(ai_vm, db_manager, sample_project):
    vm, boards_vm, _ = ai_vm
    board_repo = BoardRepository(db_manager)

    board2 = Board(board_no=2, height=100, base=50, length=2000.0)
    board_repo.add_board(board2, sample_project.name)
    boards_vm.handle_project_changed(sample_project.name)

    vm.load_image("test_image.jpg")
    vm.add_manual_segment([Point2D(10, 10)], face_id=1)

    # change board
    boards_vm.current_board_no = "2"

    # verify AI analysis state is reset
    assert vm.current_image_path is None
    assert vm.unassigned_segments == []
    assert vm.selected_segment_ids == []