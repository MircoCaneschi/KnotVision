from mvvm.models import Project, Species, Board, Knot

#-- project--
def test_project_validate_name():
    p_valid = Project("name", "species")
    p_valid2 = Project("    name ", "species")
    p_invalid = Project("", "species")
    p_invalid2 = Project("   ", "species")

    assert p_valid.validate_name("name") is True
    assert p_valid2.validate_name("name") is True
    assert p_invalid.validate_name("") is False
    assert p_invalid2.validate_name("") is False

def test_project_equality():
    p1 = Project("ProgettoA", "Abete")
    p2 = Project("ProgettoA", "Pino")
    p3 = Project("ProgettoB", "Abete")

    assert p1 == p2
    assert p1 != p3
    assert p1 != "ProgettoA"

#-- species --
def test_species_validate_name():
    s_valid = Species("Abete")
    s_valid2 = Species("  Pino  ")
    s_invalid = Species("")
    s_invalid2 = Species("   ")

    assert s_valid.validate_name("Abete") is True
    assert s_valid2.validate_name("Pino") is True
    assert s_invalid.validate_name("") is False
    assert s_invalid2.validate_name("") is False

def test_species_equality():
    s1 = Species("Abete")
    s2 = Species("Abete")
    s3 = Species("Pino")

    assert s1 == s2
    assert s1 != s3
    assert s1 != "Abete"

#-- board --
def test_board_validate_measurements():
    b_valid = Board(1, 10, 10, 10.0)
    b_invalid = Board(1, -10, 10, 10.0)
    b_invalid2 = Board(1, 10, -10, 10.0)
    b_invalid3 = Board(1, 10, 10, -10.0)

    assert b_valid.validate_measurements() is True
    assert b_invalid.validate_measurements() is False
    assert b_invalid2.validate_measurements() is False
    assert b_invalid3.validate_measurements() is False

#--knot--
def test_knot_validate_coordinates():
    k_valid = Knot(knot_no=1, x=500, pith_z=10, pith_y=None)
    k_invalid_x = Knot(knot_no=1, x="invalid_x")
    k_invalid_pith_z = Knot(knot_no=1, x=500, pith_z="invalid_z")
    k_invalid_pith_y = Knot(knot_no=1, x=500, pith_y="invalid_y")

    assert k_valid.validate_coordinates() is True
    assert k_invalid_x.validate_coordinates() is False
    assert k_invalid_pith_z.validate_coordinates() is False
    assert k_invalid_pith_y.validate_coordinates() is False
