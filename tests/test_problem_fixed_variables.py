from ortools.sat.python import cp_model
from tests.setup import ProblemTestSetup


class TestFixedVariableConstraints(ProblemTestSetup):

    def test_fixed_assignment(self):
        # Assignments. Simulating assigment initial conditions.
        var1 = self.problem.add_fixed_assignment(0, 0, 0)
        var2 = self.problem.add_fixed_assignment(1, 1, 0)

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
        var1 = self.problem.add_fixed_movement(self.aircraft1.name, 1)

        status, solver = self.problem.solve()

        with self.assertRaises(ValueError):
            self.problem.add_fixed_movement(
                "THIS AIRCRAFT DOES NOT EXIST", 25
            )  # Check that a non existent movement variable raises a Value error.
        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual(solver.Value(var1), 1)
