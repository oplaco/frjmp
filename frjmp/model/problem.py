# frjmp/model/problem.py

from datetime import date, timedelta
from ortools.sat.python import cp_model
from frjmp.model.variables.assignment import create_assignment_variables
from frjmp.model.variables.movement import (
    create_aircraft_movement_variables,
    create_movement_in_position_variables,
)
from frjmp.model.variables.pattern_assignment import create_pattern_assignment_variables
from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.constraints.capacity import add_position_capacity_constraints
from frjmp.model.constraints.movement import add_movement_detection_constraints
from frjmp.model.objective_function import (
    minimize_total_aircraft_movements,
    minimize_total_position_movements,
)
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.parameters.position_aircraft_model import (
    PositionsAircraftModelDependency,
)
from frjmp.model.sets.aircraft import AircraftModel
from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position
from frjmp.utils.timeline_utils import (
    compress_dates,
    trim_jobs_before_t0_inplace,
    trim_jobs_after_last_t_inplace,
)
from frjmp.utils.validation_utils import (
    validate_capacity_feasibility,
    validate_non_overlapping_jobs_per_aircraft,
)
from frjmp.model.logger import IncrementalSolverLogger


class Problem:

    # Solver Properties
    SOLVERTIMELIMIT = 1200  # Default value in seconds
    STEPTIMELIMIT = 120  # Default value in seconds

    def __init__(
        self,
        jobs: list[Job],
        positions_configuration: PositionsConfiguration,
        position_aircraftmodel_dependency: PositionsAircraftModelDependency,
        t0: date = date.today(),
        t_last: date = None,
        initial_conditions: dict = None,
    ):
        # Init variables
        self.jobs = jobs
        self.positions_configuration = positions_configuration
        self.positions = positions_configuration.positions
        self.t0 = t0
        self.pos_aircraft_model_dependency = position_aircraftmodel_dependency
        self.aircraft_models = position_aircraftmodel_dependency.aircraft_models
        if t_last is None:
            t_last = t0 + timedelta(days=200)
        self.initial_conditions = initial_conditions

        # Other variables
        self.fixed_variables = (
            []
        )  # List of (var, value) of fixed variables. This can be used for initial or contour conditions.

        # --- Pre-processing ---#
        trim_jobs_before_t0_inplace(jobs, t0)
        trim_jobs_after_last_t_inplace(jobs, t_last)

        # Calculate compressed time scale
        compressed_dates, date_to_index, index_to_date = compress_dates(jobs, [t0])
        self.compressed_dates = compressed_dates
        self.date_to_index = date_to_index
        self.index_to_date = index_to_date

        # Currently use compressed dates as time_step_indexes in the future they might be actual int values
        self.time_step_indexes = compressed_dates

        # --- Validations --- #
        validate_non_overlapping_jobs_per_aircraft(jobs)
        validate_capacity_feasibility(
            jobs, self.positions, compressed_dates, date_to_index
        )

        # Create model
        self.model = cp_model.CpModel()

        # Build variables
        self.build_variables()

    def build_variables(self):
        self.assigned_vars = create_assignment_variables(
            self.model,
            self.jobs,
            self.positions,
            self.compressed_dates,
            self.date_to_index,
        )
        self.aircraft_movement_vars = create_aircraft_movement_variables(
            self.model, self.jobs, self.time_step_indexes
        )
        self.movement_in_position_vars = create_movement_in_position_variables(
            self.model, self.positions, self.time_step_indexes
        )

        self.pattern_assigned_vars = create_pattern_assignment_variables(
            self.model,
            self.jobs,
            self.compressed_dates,
            self.date_to_index,
            self.pos_aircraft_model_dependency,
            self.assigned_vars,
        )

    def add_constraints(self):
        # Add the fixed values (if any) of the variables as constraints to the problem.
        if self.initial_conditions is not None:
            self._apply_initial_conditions_as_fixed_patterns()
        for var, value in self.fixed_variables:
            self.model.Add(var == int(value))

        # Add problem-specific constraints.
        add_job_assignment_constraints(
            self.model,
            self.assigned_vars,
            self.pattern_assigned_vars,
            self.jobs,
            self.positions,
            self.date_to_index,
            self.time_step_indexes,
            self.pos_aircraft_model_dependency,
        )

        add_movement_detection_constraints(
            self.model,
            self.assigned_vars,
            self.pattern_assigned_vars,
            self.aircraft_movement_vars,
            self.movement_in_position_vars,
            self.jobs,
            num_timesteps=len(self.time_step_indexes),
            positions_configuration=self.positions_configuration,
        )

        add_position_capacity_constraints(
            self.model,
            self.assigned_vars,
            self.positions,
            self.jobs,
            num_timesteps=len(self.time_step_indexes),
        )

    def set_objective(self):
        total_movements = minimize_total_aircraft_movements(
            self.model, self.aircraft_movement_vars
        )

        total_movements = minimize_total_position_movements(
            self.model, self.movement_in_position_vars
        )
        self.objective_function = total_movements

    def add_fixed_assignment(self, j_idx, p_idx, t_idx, value=True):
        try:
            var = self.assigned_vars[j_idx][p_idx][t_idx]
        except KeyError:
            raise ValueError(
                f"Invalid fixed assignment: variable for job {j_idx}, position {p_idx}, time {t_idx} does not exist."
            )
        self.fixed_variables.append((var, value))
        return var

    def add_fixed_pattern_assignment(self, j_idx, t_idx, k_idx, value=True):
        try:
            var = self.pattern_assigned_vars[j_idx][t_idx][k_idx]
        except KeyError:
            raise ValueError(
                f"Invalid fixed pattern assignment: variable for job {j_idx}, time {t_idx}, pattern {k_idx} does not exist."
            )
        self.fixed_variables.append((var, value))
        return var

    def add_fixed_aircraft_movement(self, aircraft_name, t_idx, value=True):
        try:
            var = self.aircraft_movement_vars[aircraft_name][t_idx]
        except KeyError:
            raise ValueError(
                f"Invalid fixed movement: variable for aircraft '{aircraft_name}' at time {t_idx} does not exist."
            )
        self.fixed_variables.append((var, value))
        return var

    def add_fixed_bool_var(self, var, value=True):
        # Appends to fixed_variables[] a boolean variable and its desired fixed value.
        self.fixed_variables.append((var, value))

    def _apply_initial_conditions_as_fixed_patterns(self):
        t0_idx = 0  # assuming t0 is at index 0
        pos_index = {p.name: idx for idx, p in enumerate(self.positions)}
        model_index = {model: idx for idx, model in enumerate(self.aircraft_models)}
        pattern_matrix = self.pos_aircraft_model_dependency.generate_matrix()

        for aircraft, assigned_positions in self.initial_conditions[
            "assignments"
        ].items():
            assigned_pos_names = {pos.name for pos in assigned_positions}
            model = aircraft.model
            model_idx = model_index[model]

            # Find matching job
            job_idx = None
            for j_idx, job in enumerate(self.jobs):
                if job.aircraft == aircraft and job.start <= self.t0 <= job.end:
                    job_idx = j_idx
                    break
            if job_idx is None:
                raise ValueError(f"No active job found for {aircraft.name} at t0.")

            # Try to match pattern k_idx in model.allowed_patterns
            matched = False
            for k_idx, pattern_row in enumerate(pattern_matrix[model_idx]):
                pattern_positions = {
                    self.positions[p_idx].name
                    for p_idx, used in enumerate(pattern_row)
                    if used == 1
                }
                if pattern_positions == assigned_pos_names:
                    self.add_fixed_pattern_assignment(
                        job_idx, t0_idx, k_idx, value=True
                    )
                    matched = True
                    break

            if not matched:
                raise ValueError(
                    f"No matching pattern found for aircraft {aircraft.name} with positions {assigned_pos_names}."
                )

    def solve(self):
        self.add_constraints()
        self.set_objective()

        solver = cp_model.CpSolver()

        # When wanting to log
        logger = IncrementalSolverLogger(
            self.objective_function,
            inactivity_timeout=self.STEPTIMELIMIT,
            log=False,
        )
        logger.start_monitoring()
        status = solver.SolveWithSolutionCallback(self.model, logger)

        print(f"BestObjectiveBound: {logger.BestObjectiveBound()}")

        # Some times the max_time_in_seconds is reached but the wall time is a little bit smaller, therefore we add 1 second just to make sure.
        wall_time = solver.WallTime()
        exceeded_time_limit = False
        if wall_time + 1 >= solver.parameters.max_time_in_seconds:
            print(
                f"Stopping search after {wall_time:.2f} s, solver time limit reached. Consider increasing time limit."
            )
            exceeded_time_limit = True
        elif logger.step_time_limit_reached:
            print("Stopping search, step time limit reached.")

        return status, solver
