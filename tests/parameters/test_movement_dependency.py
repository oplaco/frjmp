import unittest
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.sets.position import Position
from tests.setup import ProblemTestSetup


class TestMovementDependency(ProblemTestSetup):

    def test_generate_matrix(self):
        pos_a = Position("A", [])
        pos_b = Position("B", [])
        pos_c = Position("C", [])
        pos_d = Position("D", [])

        dep = PositionsConfiguration(positions=[pos_a, pos_b, pos_c, pos_d])

        dep.add_trigger(pos_a, pos_b)
        dep.add_trigger(pos_a, pos_c)

        matrix, index_map = dep.generate_matrix()

        # Ensure matrix has correct size
        self.assertEqual(len(matrix), 4)
        self.assertEqual(len(matrix[0]), 4)

        i = index_map["A"]
        j = index_map["B"]
        k = index_map["C"]
        l = index_map["D"]

        # Triggers
        self.assertEqual(matrix[i][j], 1)
        self.assertEqual(matrix[i][k], 1)
        self.assertEqual(matrix[i][l], 0)

        # No reverse trigger
        self.assertEqual(matrix[j][i], 0)
        self.assertEqual(matrix[k][i], 0)

    def test_dependant_movements(self):
        """Test if a position movement in position1 triggers a position movement in position2 and position3.
        Test if the corresponding aircraft movements are created.
        """
        self.problem.positions = [self.position1, self.position2, self.position3]
        self.problem.positions_configuration.add_trigger(self.position1, self.position2)
        self.problem.positions_configuration.add_trigger(self.position1, self.position3)

        t0 = 0
        # Fixed assignments
        self.problem.model.Add(self.problem.pattern_assigned_vars[0][t0][0] == 1)
        self.problem.model.Add(self.problem.pattern_assigned_vars[1][t0][1] == 1)
        self.problem.model.Add(self.problem.pattern_assigned_vars[2][t0][2] == 1)

        # Initial position movement that trigger the others.
        self.problem.model.Add(self.problem.movement_in_position_vars[0][t0] == 1)

        status, solver = self.problem.solve()

        amv = self.problem.aircraft_movement_vars
        pmv = self.problem.movement_in_position_vars
        pav = self.problem.pattern_assigned_vars

        # Aircraft1 is assigned to pattern 0 in t0 as it was fixed
        self.assertEqual(solver.Value(pav[0][t0][0]), 1)

        # The position movement position1 exist and therefore triggers a position movement in position2 and position3
        self.assertEqual(solver.Value(pmv[0][0]), 1)
        self.assertEqual(solver.Value(pmv[1][0]), 1)
        self.assertEqual(solver.Value(pmv[2][0]), 1)

        self.assertEqual(
            solver.Value(amv[self.aircraft1.name][t0]), 1
        )  # The aircraft1 movement is registered in t0
        self.assertEqual(
            solver.Value(amv[self.aircraft1.name][1]), 0
        )  # The aircraft1 movement is not registered in t1

        # There are aircraft movements for aircraft 2 and 3 at t0.
        self.assertEqual(solver.Value(amv[self.aircraft2.name][t0]), 1)
        self.assertEqual(solver.Value(amv[self.aircraft3.name][t0]), 1)
