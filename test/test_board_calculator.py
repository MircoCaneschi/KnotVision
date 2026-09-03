
from core.board_calculator import BoardCalculator
from mvvm.models import Board, Knot

def test_calculate_knot_results_with_data():
    board = Board(board_no=1, height=100, base=50, length=2000)
    knot = Knot(knot_no=1, x=500, side1_z1=10, side1_z2=30, side2_z1=0, side2_z2=0)
    knots = [knot]
    
    calc = BoardCalculator()
    results = calc.calculate_knot_results(board, knots, knot)
    assert results is not None
    assert "DEB" in results
    assert float(results["DEB"]) >= 0.0


def test_calculate_knot_results():
    board = None
    knots = None
    current_knot = None

    calc = BoardCalculator()
    results = calc.calculate_knot_results(board, knots, current_knot)
    assert results == {"tKnot": "0.00", "mKnot": "0.00", "tKAR": "0.00", "mKAR_L": "0.00", "mKAR_R": "0.00", "mKAR": "0.00", "DEB": "0.00", "DAB": "0.00", "DEK": "0.00", "EEB": "0.00", "EAB": "0.00", "SplayKnot": "0"}


def test_knots_outside_150mm_interval_are_ignored():
    board = Board(board_no=1, height=100, base=50, length=2000)
    main_knot = Knot(knot_no=1, x=100, side1_z1=10, side1_z2=30)
    far_knot = Knot(knot_no=2, x=500, side1_z1=40, side1_z2=60)
    
    calc = BoardCalculator()
    res_main = calc.calculate_knot_results(board, [main_knot], main_knot)
    res_with_far = calc.calculate_knot_results(board, [main_knot, far_knot], main_knot)

    assert res_with_far["DAB"] == res_main["DAB"]
    assert res_with_far["EAB"] == res_main["EAB"]
    assert res_with_far["tKAR"] == res_main["tKAR"]


def test_to_standard_knot_coordinates_conversion():
    board = Board(board_no=1, height=100, base=50, length=2000)
    knot = Knot(
        knot_no=1, 
        x=500,
        side1_z1=10, side1_z2=30,
        side2_z1=5,  side2_z2=15,
        side3_z1=20, side3_z2=40
    )
    calc = BoardCalculator()
    std_knot = calc._to_standard_knot(knot, board)
    assert std_knot.side1_z1 == 70  
    assert std_knot.side1_z2 == 90  
    assert std_knot.side2_z1 == 35  
    assert std_knot.side2_z2 == 45  
    assert std_knot.side3_z1 == 20
    assert std_knot.side3_z2 == 40
    
    assert std_knot.knot_no == knot.knot_no
    assert std_knot.x == knot.x


def test_knot_results_boundaries():
    board = Board(board_no=1, height=100, base=50, length=2000)
    knot = Knot(knot_no=1, x=500, side1_z1=0, side1_z2=100, side2_z1=0, side2_z2=50)
    
    calc = BoardCalculator()
    results = calc.calculate_knot_results(board, [knot], knot)
    
    #these parameters are percentages
    for param in ["tKnot", "mKnot", "tKAR", "mKAR", "DEB"]:
        val = float(results[param])
        assert 0.0 <= val <= 1.0


def test_is_face_knot():
    calc = BoardCalculator()
    
    knot_top = Knot(knot_no=1, x=100, side1_z1=10, side1_z2=20)
    assert calc._isFaceKnot(knot_top) is False

    knot_face = Knot(knot_no=2, x=100, side2_z1=5, side2_z2=15)
    assert calc._isFaceKnot(knot_face) is True


