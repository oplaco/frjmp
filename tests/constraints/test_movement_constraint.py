import unittest
from datetime import date

from ortools.sat.python import cp_model

from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.constraints.capacity import add_position_capacity_constraints
from frjmp.model.constraints.movement import add_movement_detection_constraints
from frjmp.model.parameters.movement_dependency import MovementDependency
from frjmp.model.parameters.position_aircraft_model import (
    PositionsAircraftModelDependency,
)
from frjmp.model.sets.aircraft import Aircraft, AircraftModel
from frjmp.model.sets.job import Job
from frjmp.model.sets.need import Need
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.variables.assignment import create_assignment_variables
from frjmp.model.variables.movement import (
    create_aircraft_movement_variables,
    create_movement_in_position_variables,
)
from frjmp.model.variables.pattern_assignment import create_pattern_assignment_variables
from frjmp.utils.timeline_utils import compress_dates


class TestMovementConstraint(unittest.TestCase):
    def setUp(self):
        self.aircraft_model1 = AircraftModel("C295")
        self.aircraft_models = [self.aircraft_model1]
        self.aircraft = Aircraft("AC1", self.aircraft_model1)
        self.need = Need("repair")
        self.phase = Phase("repair-phase", self.need)
        self.job1 = Job(self.aircraft, self.phase, date(2025, 4, 10), date(2025, 4, 12))
        self.job2 = Job(self.aircraft, self.phase, date(2025, 4, 13), date(2025, 4, 20))
        self.jobs = [self.job1, self.job2]

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
        self.aircraft_movement_vars = create_aircraft_movement_variables(
            self.model, self.jobs, self.time_step_indexes
        )

        self.assigned_vars = create_assignment_variables(
            self.model,
            self.jobs,
            self.positions,
            self.compressed_dates,
            self.date_to_index,
        )

        self.movement_in_position_vars = create_movement_in_position_variables(
            self.model, self.positions, self.time_step_indexes
        )

        pos_aircraft_model_dependency = PositionsAircraftModelDependency(
            self.aircraft_models, self.positions
        )

        self.pattern_assigned_vars = create_pattern_assignment_variables(
            self.model,
            self.jobs,
            self.compressed_dates,
            self.date_to_index,
            pos_aircraft_model_dependency,
            self.aircraft_models,
            self.assigned_vars,
        )

        # Add basic constraints
        add_job_assignment_constraints(
            self.model,
            self.assigned_vars,
            self.pattern_assigned_vars,
            self.jobs,
            self.positions,
            self.date_to_index,
            self.time_step_indexes,
            pos_aircraft_model_dependency,
        )

        add_movement_detection_constraints(
            self.model,
            self.assigned_vars,
            self.aircraft_movement_vars,
            self.movement_in_position_vars,
            self.jobs,
            num_positions=len(self.positions),
            num_timesteps=len(self.time_step_indexes),
            movement_dependency=MovementDependency(),  # Empty mock dependency
        )

        add_position_capacity_constraints(
            self.model,
            self.assigned_vars,
            self.positions,
            self.jobs,
            num_timesteps=len(self.time_step_indexes),
        )

    def test_movement_detected_when_position_changes_same_job(self):
        self.create_local_problem()
        # To isolate the movement constraint. Fake the other crucial constraint, the assigment constraint by setting some values.
        # Move assign aircraft 0 to pos1 in t0 and in pos2 in t1 and t2.
        self.model.Add(self.assigned_vars[0][0][0] == 1)  # t0 = pos1
        self.model.Add(self.assigned_vars[0][0][1] == 0)
        self.model.Add(self.assigned_vars[0][1][1] == 1)  # t1 = pos2

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][0]), 0
        )  # No movement at t0
        # Should detect movement at t1
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][1]), 1
        )
        self.assertEqual(solver.Value(self.movement_in_position_vars[1][1]), 1)

    def test_movement_detected_when_position_changes_different_job(self):
        self.create_local_problem()
        # To isolate the movement constraint. Fake the other crucial constraint, the assigment constraint by setting some values.
        previous_pos_idx = 0
        after_pos_idx = 1
        # Movement between job1 and job2 from pos1 in t1 to pos2 in t3.
        self.model.Add(self.assigned_vars[0][previous_pos_idx][0] == 1)  # t0 = pos1
        self.model.Add(self.assigned_vars[0][previous_pos_idx][1] == 1)  # t1 = pos1

        self.model.Add(self.assigned_vars[1][after_pos_idx][2] == 1)  # t2 = pos2
        self.model.Add(self.assigned_vars[1][after_pos_idx][3] == 1)  # t3 = pos2

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        # Should detect movement at t2
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][2]), 1
        )
        self.assertEqual(
            solver.Value(self.movement_in_position_vars[after_pos_idx][2]), 1
        )
        # No movement at t1
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][1]), 0
        )
        self.assertEqual(
            solver.Value(self.movement_in_position_vars[after_pos_idx][1]), 0
        )
