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

        t0 = 0
        self.problem.model.Add(self.problem.pattern_assigned_vars[0][t0][0] == 1)
        # fixed_assignmenet = self.problem.add_fixed_assignment(0, 0, 0)
        self.problem.model.Add(self.problem.movement_in_position_vars[0][t0] == 1)

        status, solver = self.problem.solve()

        for j_idx, j_dict in self.problem.pattern_assigned_vars.items():
            job = self.problem.jobs[j_idx]
            for t_idx, t_dict in j_dict.items():
                for k_idx, var in t_dict.items():
                    if solver.Value(var) == 1:
                        pattern = job.aircraft.model.allowed_patterns[k_idx]
                        pos_names = [p.name for p in pattern.positions]
                        print(
                            f"Job {self.problem.jobs[j_idx]} at t={t_idx} ({self.problem.index_to_date[t_idx]}): "
                            f"Pattern {k_idx} → Positions {pos_names}"
                        )

        for j_idx, j_dict in self.problem.aircraft_movement_vars.items():
            for t_idx, var in j_dict.items():
                if solver.Value(var) == 1:
                    print(
                        f"Movement Job {j_idx} at t={t_idx} ({self.problem.index_to_date[t_idx]})"
                    )

        for p_idx, p_dict in self.problem.movement_in_position_vars.items():
            for t_idx, var in p_dict.items():
                if solver.Value(var) == 1:
                    print(
                        f"Movement in postion {p_idx} at t={t_idx} ({self.problem.index_to_date[t_idx]})"
                    )

        amv = self.problem.aircraft_movement_vars
        pmv = self.problem.movement_in_position_vars
        pav = self.problem.pattern_assigned_vars
        self.assertEqual(
            solver.Value(pav[0][t0][1]), 0
        )  # Aircraft is not assigned to patter 0 at t1 as it was fixed moved.
        self.assertEqual(
            solver.Value(pav[0][t0][0]), 1
        )  # Aircraft is assigned to pattern 0 in t0 as it was fixed

        # The position movement position1 exist and therefore triggers a position movement in position2 and position3
        self.assertEqual(solver.Value(pmv[0][0]), 1)
        self.assertEqual(solver.Value(pmv[1][0]), 1)
        self.assertEqual(solver.Value(pmv[2][0]), 1)
        self.assertEqual(solver.Value(pmv[3][0]), 0)

        self.assertEqual(
            solver.Value(amv[self.aircraft1.name][t0]), 1
        )  # The aircraft1 movement is registered in t0
        self.assertEqual(
            solver.Value(amv[self.aircraft1.name][1]), 0
        )  # The aircraft1 movement is not registered in t1
        # There are aircraft movements for aircraft 2 and 3 at t0.
        self.assertEqual(solver.Value(amv[self.aircraft2.name][t0]), 1)
        self.assertEqual(solver.Value(amv[self.aircraft3.name][t0]), 1)
