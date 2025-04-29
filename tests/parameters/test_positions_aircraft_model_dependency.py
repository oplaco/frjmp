import unittest
from frjmp.model.sets.position import Position
from frjmp.model.sets.aircraft import AircraftModel
from frjmp.model.parameters.position_aircraft_model import (
    Pattern,
    PositionsAircraftModelDependency,
)


class TestPositionsAircraftModelDependency(unittest.TestCase):
    def test_generate_matrix(self):
        # Create dummy positions
        p1 = Position("P1", [])
        p2 = Position("P2", [])
        p3 = Position("P3", [])
        positions = [p1, p2, p3]

        # Create two aircraft models
        m1 = AircraftModel("Model1")
        m2 = AircraftModel("Model2")

        # Add custom patterns
        m1.add_multiple_patterns(
            [
                Pattern([p1]),
                Pattern([p2, p3]),
            ]
        )

        # m2 will have no patterns, should auto-generate one per position

        # Create dependency
        dep = PositionsAircraftModelDependency([m1, m2], positions)

        # Generate matrix
        matrix = dep.generate_matrix()

        # Expected result
        expected_matrix = [
            # Model1
            [
                [1, 0, 0],  # Pattern 0: p1
                [0, 1, 1],  # Pattern 1: p2 and p3
            ],
            # Model2 (auto-generated)
            [
                [1, 0, 0],  # Default pattern for p1
                [0, 1, 0],  # Default pattern for p2
                [0, 0, 1],  # Default pattern for p3
            ],
        ]

        self.assertEqual(matrix, expected_matrix)
