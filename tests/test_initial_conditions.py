from datetime import timedelta

from frjmp.model.adapter import DailyAdapter
from tests.setup import ProblemTestSetup
from frjmp.model.problem import Problem
from unittest.mock import MagicMock


class TestInitialConditions(ProblemTestSetup):
    def setUp(self):
        super().setUp()
        t_init_local = self.date1 + timedelta(
            days=1
        )  # Add 1 day to t_init so t0 = date1 and we can apply the initial conditions
        adapter = DailyAdapter(t_init_local)
        self.problem2 = Problem(self.jobs, self.pc, self.pud, adapter)
        # Spy on add_fixed_pattern_assignment
        self.problem2.add_fixed_pattern_assignment = MagicMock()

    def test_applies_fixed_assignment(self):
        self.problem2.initial_conditions = {
            "assignments": {self.unit1: [self.position1]}
        }
        self.problem2._apply_initial_conditions_as_fixed_patterns()
        self.problem2.add_fixed_pattern_assignment.assert_called_once_with(
            0, 0, 0, value=True
        )

    def test_raises_job_not_found_at_t0(self):
        self.problem2.initial_conditions = {
            "assignments": {self.unit4: [self.position2]}
        }
        with self.assertRaises(ValueError) as context:
            self.problem2._apply_initial_conditions_as_fixed_patterns()
        self.assertIn("No active job found", str(context.exception))
