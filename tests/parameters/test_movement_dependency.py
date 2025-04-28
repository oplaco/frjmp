import unittest
from frjmp.model.parameters.movement_dependency import MovementDependency
from frjmp.model.sets.position import Position
from tests.setup import ProblemTestSetup


class TestMovementDependency(ProblemTestSetup):

    def test_generate_matrix(self):
        pos_a = Position("A", [])
        pos_b = Position("B", [])
        pos_c = Position("C", [])
        pos_d = Position("D", [])

        dep = MovementDependency(positions=[pos_a, pos_b, pos_c, pos_d])

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
        self.problem.movement_dependency.add_trigger(self.position1, self.position2)
        self.problem.movement_dependency.add_trigger(self.position1, self.position3)

        fixed_assignmenet = self.problem.add_fixed_assignment(0, 0, 0)
        fixed_movement = self.problem.add_fixed_aircraft_movement(
            self.aircraft1.name, 1
        )  # Force movement of aircraft 1 at t1 to trigger movement in position2 and position3 at t0

        status, solver = self.problem.solve()

        amv = self.problem.aircraft_movement_vars
        pmv = self.problem.movement_in_position_vars
        av = self.problem.assigned_vars
        self.assertEqual(
            solver.Value(av[0][0][1]), 0
        )  # Aircraft is not assigned to position 0 in t1 as it was fixed moved.
        self.assertEqual(
            solver.Value(av[0][0][0]), 1
        )  # Aircraft is assigned to position 0 in t0 as it was fixed

        # The position movement position1 exist and therefore triggers a position movement in position2 and position3
        self.assertEqual(solver.Value(pmv[0][1]), 1)
        self.assertEqual(solver.Value(pmv[1][1]), 1)
        self.assertEqual(solver.Value(pmv[2][1]), 1)

        self.assertEqual(
            solver.Value(amv[self.aircraft1.name][1]), 1
        )  # The aircraft1 movement is registered in t1
        self.assertEqual(
            solver.Value(amv[self.aircraft1.name][0]), 0
        )  # The aircraft1 movement is not registered in t0
        # There are aircraft movements for aircraft 2 and 3 at t1.
        self.assertEqual(solver.Value(amv[self.aircraft2.name][1]), 1)
        self.assertEqual(solver.Value(amv[self.aircraft3.name][1]), 1)
