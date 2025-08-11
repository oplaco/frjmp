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

        dep.add_trigger(pos_a, pos_d, {pos_b})
        dep.add_trigger(pos_a, pos_c, {pos_b})

        matrix, index_map = dep.generate_matrix()

        # Ensure matrix has correct size
        self.assertEqual(len(matrix), 4)
        self.assertEqual(len(matrix[0]), 4)

        i = index_map["A"]
        j = index_map["B"]
        k = index_map["C"]
        l = index_map["D"]

        # Triggers
        self.assertEqual(matrix[i][j][j], 0)
        self.assertEqual(matrix[i][k][j], 1)
        self.assertEqual(matrix[i][l][j], 1)

        # No reverse trigger
        self.assertEqual(matrix[j][i][j], 0)
        self.assertEqual(matrix[k][i][j], 0)

    def test_dependant_movements(self):
        """Test if a position movement in position1 to position4 triggers a position movement in position2 and position3.
        Test if the corresponding unit movements are created.
        """
        self.problem.positions = [
            self.position1,
            self.position2,
            self.position3,
            self.position4,
        ]
        self.problem.positions_configuration.add_trigger(
            self.position1, self.position4, {self.position2, self.position3}
        )

        t_init_idx = self.problem.date_to_index[self.t_init]

        # Fixed assignments
        #   Force the movement of job0 from position1 to position4
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[0][t_init_idx][0] == 1
        )
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[0][t_init_idx + 1][3] == 1
        )
        #   For assigments of other units at t_init so they register as well an aicraft movement.
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[1][t_init_idx][1] == 1
        )
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[2][t_init_idx][2] == 1
        )

        status, solver = self.problem.solve()

        amv = self.problem.unit_movement_vars
        pmv = self.problem.movement_in_position_vars
        pav = self.problem.pattern_assigned_vars

        # Unit1 is assigned to pattern 0 in t_init as it was fixed
        self.assertEqual(solver.Value(pav[0][t_init_idx][0]), 1)

        # The position movement position1 exist and therefore triggers a position movement in position2 and position3
        self.assertEqual(solver.Value(pmv[0][t_init_idx]), 1)  # From
        self.assertEqual(solver.Value(pmv[1][t_init_idx]), 1)  # Triggered
        self.assertEqual(solver.Value(pmv[2][t_init_idx]), 1)  # Triggered
        self.assertEqual(solver.Value(pmv[3][t_init_idx]), 1)  # To

        # The unit1 movement is registered in t_init
        self.assertEqual(solver.Value(amv[self.unit1.name][t_init_idx]), 1)

        # The unit1 movement is not registered in t_init + 1
        self.assertEqual(solver.Value(amv[self.unit1.name][t_init_idx + 1]), 0)

        # There are unit movements for unit 2 and 3 at t_init.
        self.assertEqual(solver.Value(amv[self.unit2.name][t_init_idx]), 1)
        self.assertEqual(solver.Value(amv[self.unit3.name][t_init_idx]), 1)

    def test_dependant_movement_direction(self):
        """If A triggers a movement in B and B triggers a movement in C a movement from B to A
        should not actually trigger a movement on C as movements have directions.
        """
        self.problem.positions = [self.position1, self.position2, self.position3]
        self.problem.positions_configuration.add_trigger(
            self.position1, self.position3, {self.position2}
        )

        t_init_idx = self.problem.date_to_index[self.t_init]
        # Fixed assignments at t_init_idx for the three units and patterns (positions).
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[0][t_init_idx][0] == 1
        )
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[1][t_init_idx][1] == 1
        )
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[2][t_init_idx][2] == 1
        )

        # Initial position movement from position2 to position1 that should not trigger a movement in position3.
        self.problem.model.Add(
            self.problem.pattern_assigned_vars[1][t_init_idx + 1][0] == 1
        )

        status, solver = self.problem.solve()

        amv = self.problem.unit_movement_vars
        pmv = self.problem.movement_in_position_vars
        pav = self.problem.pattern_assigned_vars

        # Unit1 is assigned to pattern 0 in t_init as it was fixed
        self.assertEqual(solver.Value(pav[0][t_init_idx][0]), 1)

        # Unit2 is assigned to pattern 0 in t_init as it was fixed
        self.assertEqual(solver.Value(pav[1][t_init_idx + 1][0]), 1)

        # The unit2 movement is registered in t_init and therefore unit1 as well to make room for it.
        self.assertEqual(solver.Value(amv[self.unit1.name][t_init_idx]), 1)
        self.assertEqual(solver.Value(amv[self.unit2.name][t_init_idx]), 1)

        # The position movement position1 exist and therefore triggers a position movement in position2 and position3
        self.assertEqual(solver.Value(pmv[0][0]), 1)
        self.assertEqual(solver.Value(pmv[1][0]), 1)
        self.assertEqual(solver.Value(pmv[2][0]), 1)

        # # The unit1 movement is not registered in t_init + 1
        self.assertEqual(solver.Value(amv[self.unit1.name][t_init_idx + 1]), 0)

        # # There are unit movements for unit 2 and none for unit3 at t_init.
        self.assertEqual(solver.Value(amv[self.unit2.name][t_init_idx]), 1)
        self.assertEqual(solver.Value(amv[self.unit3.name][t_init_idx]), 0)
