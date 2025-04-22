# frjmp/model/problem.py

from datetime import date
from ortools.sat.python import cp_model
from frjmp.model.variables.assignment import create_assignment_variables
from frjmp.model.variables.movement import create_movement_variables
from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.constraints.capacity import add_position_capacity_constraints
from frjmp.model.constraints.movement import add_movement_detection_constraints
from frjmp.model.objective_function import minimize_total_movements
from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position
from frjmp.utils.timeline_utils import compress_dates, trim_jobs_before_t0_inplace
from frjmp.utils.validation_utils import (
    validate_capacity_feasibility,
    validate_non_overlapping_jobs_per_aircraft,
)


class Problem:
    def __init__(
        self, jobs: list[Job], positions: list[Position], t0: date = date.today()
    ):
        self.jobs = jobs
        self.positions = positions
        self.t0 = t0

        self.model = cp_model.CpModel()

        # Set initial conditions

        # --- Pre-processing ---#
        trim_jobs_before_t0_inplace(jobs, t0)

        # Calculate compressed time scale
        compressed_dates, date_to_index, index_to_date = compress_dates(jobs)
        self.compressed_dates = compressed_dates
        self.date_to_index = date_to_index
        self.index_to_date = index_to_date

        # Currently use compressed dates as time_step_indexes in the future they might be actual int values
        self.time_step_indexes = compressed_dates

        # --- Validations --- #
        validate_non_overlapping_jobs_per_aircraft(jobs)
        validate_capacity_feasibility(jobs, positions, compressed_dates, date_to_index)

    def build_variables(self):
        self.assigned_vars = create_assignment_variables(
            self.model,
            self.jobs,
            self.positions,
            self.compressed_dates,
            self.date_to_index,
        )
        self.movement_vars = create_movement_variables(
            self.model, self.jobs, self.time_step_indexes
        )
        add_position_capacity_constraints(
            self.model,
            self.assigned_vars,
            self.positions,
            self.jobs,
            num_timesteps=len(self.time_step_indexes),
        )

    def add_constraints(self):
        add_job_assignment_constraints(
            self.model,
            self.assigned_vars,
            self.jobs,
            self.positions,
            self.date_to_index,
            self.time_step_indexes,
        )
        add_movement_detection_constraints(
            self.model,
            self.assigned_vars,
            self.movement_vars,
            num_positions=len(self.positions),
            num_timesteps=len(self.time_step_indexes),
        )

    def set_objective(self):
        minimize_total_movements(self.model, self.movement_vars)

    def solve(self):
        self.build_variables()
        self.add_constraints()
        self.set_objective()

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        return status, solver
