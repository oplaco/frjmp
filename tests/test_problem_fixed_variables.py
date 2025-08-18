# python -m unittest tests/test_problem_fixed_variables.py
from ortools.sat.python import cp_model
from tests.setup import ProblemTestSetup


class TestFixedVariableConstraints(ProblemTestSetup):

    def test_fixed_assignment(self):
        # Assignments. Simulating assigment initial conditions.
        init_tick = self.adapter.to_tick(self.t_init)
        t_init_idx = self.problem.tick_to_index[init_tick]
        var1 = self.problem.add_fixed_assignment(0, 0, t_init_idx)
        var2 = self.problem.add_fixed_assignment(1, 1, t_init_idx)

        status, solver = self.problem.solve()

        with self.assertRaises(ValueError):
            self.problem.add_fixed_assignment(
                12, 45, 25
            )  # Check that a non existent assignment variable raises a Value error.
        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual(solver.Value(var1), 1)
        self.assertEqual(solver.Value(var2), 1)

    def test_fixed_movement(self):
        # Movements. Simulating movement on t1.
        movement_a1_t1 = self.problem.add_fixed_unit_movement(self.unit1.name, 1)

        assignment_a1_t1 = self.problem.add_fixed_assignment(0, 0, 1)

        status, solver = self.problem.solve()

        with self.assertRaises(ValueError):
            self.problem.add_fixed_unit_movement(
                "THIS UNIT DOES NOT EXIST", 25
            )  # Check that a non existent movement variable raises a Value error.

        amv = self.problem.unit_movement_vars
        av = self.problem.assigned_vars

        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual(
            solver.Value(movement_a1_t1), 1
        )  # Check fixed unit movement in t1.
        self.assertEqual(
            solver.Value(assignment_a1_t1), 1
        )  # Check the fixed assignment at t1.
        self.assertEqual(
            solver.Value(av[0][0][2]), 0
        )  # Check that the unit was not in p0 at t1+1 as there was a movement for unit1 in t2.
