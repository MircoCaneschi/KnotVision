"""
Data Models for LocalKnot application.

Contains pure data classes representing domain entities without any GUI dependencies.
These models encapsulate the business logic and data validation.
"""


class Project:
    """
    Represents a Project entity.

    Attributes:
        name (str): Unique project name
        species (str): Associated species for this project
    """

    def __init__(self, name: str, species: str):
        self.name = name
        self.species = species

    def validate_name(self, name: str) -> bool:
        """
        Validate project name according to business rules.

        Args:
            name: Project name to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return bool(name and name.strip())

    def __eq__(self, other):
        """Compare two projects by name."""
        if not isinstance(other, Project):
            return False
        return self.name == other.name

    def __repr__(self):
        return f"Project(name='{self.name}', species='{self.species}')"


class Species:
    """
    Represents a Species entity.

    Attributes:
        name (str): Unique species name
    """

    def __init__(self, name: str):
        self.name = name

    def validate_name(self, name: str) -> bool:
        """
        Validate species name according to business rules.

        Args:
            name: Species name to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return bool(name and name.strip())

    def __eq__(self, other):
        """Compare two species by name."""
        if not isinstance(other, Species):
            return False
        return self.name == other.name


class Board:
    """
    Represents a Board entity within a Project.

    Attributes:
        board_no (int | str): Board identifier
        height (int): Board height measurement
        base (int): Board base measurement
        length (float): Board length measurement
        test_position (int): Test position reference
        comment (str): Additional notes about the board
    """

    def __init__(self, board_no: int | str, height: int = 0,
                 base: int = 0, length: float = 0.0,
                 test_position: int = 0, comment: str = ""):
        """
        Initialize a Board.

        Args:
            board_no: Unique board identifier
            height: Height measurement (integer mm)
            base: Base measurement (integer mm)
            length: Length measurement
            test_position: Test position reference
            comment: Additional notes
        """
        self.board_no = board_no
        self.height = height
        self.base = base
        self.length = length
        self.test_position = test_position
        self.comment = comment

    def validate_measurements(self) -> bool:
        """
        Validate that all measurements are positive.

        Returns:
            bool: True if valid, False otherwise
        """
        return self.height >= 0 and self.base >= 0 and self.length >= 0


class Knot:
    """
    Represents a Knot entity within a Board.

    Attributes:
        knot_no (int | str): Knot identifier
        x (float): X coordinate position
        pith_z (float): Pith Z coordinate
        pith_y (float): Pith Y coordinate
        is_pruned_knot (bool): Whether this is a pruned knot
        pruned_z1 (int): Pruned Z1 coordinate
        pruned_y1 (int): Pruned Y1 coordinate
        pruned_z2 (int): Pruned Z2 coordinate
        pruned_y2 (int): Pruned Y2 coordinate
        comment (str): Additional notes about the knot
        side1_z1 (int): Top z1 coordinate
        side1_z2 (int): Top z2 coordinate
        side1_dmin (int): Top dmin coordinate
        side2_z1 (int): Right z1 coordinate
        side2_z2 (int): Right z2 coordinate
        side2_dmin (int): Right dmin coordinate
        side3_z1 (int): Bottom z1 coordinate
        side3_z2 (int): Bottom z2 coordinate
        side3_dmin (int): Bottom dmin coordinate
        side4_z1 (int): Left z1 coordinate
        side4_z2 (int): Left z2 coordinate
        side4_dmin (int): Left dmin coordinate
    """

    def __init__(self, knot_no: int | str, x: int = 0,
                 pith_z: int | None = None, pith_y: int | None = None,
                 is_pruned_knot: bool = False, pruned_z1: int | None = None, pruned_y1: int | None = None,
                 pruned_z2: int | None = None, pruned_y2: int | None = None, comment: str = "",
                 side1_z1: int | None = None, side1_z2: int | None = None, side1_dmin: int | None = None,
                 side2_z1: int | None = None, side2_z2: int | None = None, side2_dmin: int | None = None,
                 side3_z1: int | None = None, side3_z2: int | None = None, side3_dmin: int | None = None,
                 side4_z1: int | None = None, side4_z2: int | None = None, side4_dmin: int | None = None):
        """
        Initialize a Knot.

        Args:
            knot_no: Unique knot identifier
            x: X coordinate
            pith_z: Pith Z coordinate
            pith_y: Pith Y coordinate
            is_pruned_knot: Whether knot is pruned
            pruned_z1: Pruned Z1 coordinate
            pruned_y1: Pruned Y1 coordinate
            pruned_z2: Pruned Z2 coordinate
            pruned_y2: Pruned Y2 coordinate
            comment: Additional notes
        """
        self.knot_no = knot_no
        self.x = x
        self.pith_z = pith_z
        self.pith_y = pith_y
        self.is_pruned_knot = is_pruned_knot
        self.pruned_z1 = pruned_z1
        self.pruned_y1 = pruned_y1
        self.pruned_z2 = pruned_z2
        self.pruned_y2 = pruned_y2
        self.comment = comment
        
        # Side parameters
        self.side1_z1 = side1_z1
        self.side1_z2 = side1_z2
        self.side1_dmin = side1_dmin
        self.side2_z1 = side2_z1
        self.side2_z2 = side2_z2
        self.side2_dmin = side2_dmin
        self.side3_z1 = side3_z1
        self.side3_z2 = side3_z2
        self.side3_dmin = side3_dmin
        self.side4_z1 = side4_z1
        self.side4_z2 = side4_z2
        self.side4_dmin = side4_dmin

    def validate_coordinates(self) -> bool:
        """
        Validate that coordinates are within acceptable ranges.

        Returns:
            bool: True if valid, False otherwise
        """
        return isinstance(self.x, int) and \
               (self.pith_z is None or isinstance(self.pith_z, int)) and \
               (self.pith_y is None or isinstance(self.pith_y, int))

