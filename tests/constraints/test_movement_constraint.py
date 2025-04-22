import unittest
from datetime import date
from ortools.sat.python import cp_model
from frjmp.model.sets.aircraft import Aircraft
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.need import Need
from frjmp.model.sets.position import Position
from frjmp.model.sets.job import Job
from frjmp.model.variables.assignment import create_assignment_variables
from frjmp.model.variables.movement import create_movement_variables
from frjmp.model.constraints.movement import add_movement_detection_constraints
from frjmp.utils.timeline_utils import compress_dates


class TestMovementConstraint(unittest.TestCase):
    def setUp(self):
        self.aircraft = Aircraft("AC1")
        self.need = Need("repair")
        self.phase = Phase("repair-phase", self.need)
        self.job = Job(self.aircraft, self.phase, date(2025, 4, 10), date(2025, 4, 12))
        self.jobs = [self.job]

        self.pos1 = Position("Hangar A", [self.need], capacity=1)
        self.pos2 = Position("Hangar B", [self.need], capacity=1)
        self.positions = [self.pos1, self.pos2]

        # Calculate compressed time scale
        compressed_dates, date_to_index, index_to_date = compress_dates(self.jobs)
        self.compressed_dates = compressed_dates
        self.date_to_index = date_to_index
        self.index_to_date = index_to_date
        # Currently use compressed dates as time_step_indexes in the future they might be actual int values
        self.time_step_indexes = compressed_dates

    def create_local_problem(self):
        """Create the optimization problem resembling the frjmp.project.Problem object but with ONLY the necessary constraints and variables."""
        self.model = cp_model.CpModel()
        self.movement_vars = create_movement_variables(
            self.model, self.jobs, self.time_step_indexes
        )
        self.assigned_vars = create_assignment_variables(
            self.model,
            self.jobs,
            self.positions,
            self.compressed_dates,
            self.date_to_index,
        )

        add_movement_detection_constraints(
            self.model,
            self.assigned_vars,
            self.movement_vars,
            num_positions=len(self.positions),
            num_timesteps=len(self.time_step_indexes),
        )

    def test_movement_detected_when_position_changes(self):
        self.create_local_problem()
        # To isolate the movement constraint. Fake the other crucial constraint, the assigment constraint by setting some values.
        # Move assign aircraft 0 to pos1 in t0 and in pos2 in t1 and t2.
        self.model.Add(self.assigned_vars[0][0][0] == 1)  # t0 = pos1
        self.model.Add(self.assigned_vars[0][0][1] == 0)
        self.model.Add(self.assigned_vars[0][1][1] == 1)  # t1 = pos2

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(
            solver.Value(self.movement_vars[0][1]), 1
        )  # Should detect movement at t1
        self.assertEqual(solver.Value(self.movement_vars[0][0]), 0)  # No movement at t0


if __name__ == "__main__":
    unittest.main()
