# frjmp/model/problem.py

from datetime import date, timedelta
from ortools.sat.python import cp_model
from frjmp.model.variables.assignment import create_assignment_variables
from frjmp.model.variables.movement import (
    create_unit_movement_variables,
    create_movement_in_position_variables,
)
from frjmp.model.variables.pattern_assignment import create_pattern_assignment_variables
from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.constraints.capacity import add_position_capacity_constraints
from frjmp.model.constraints.movement import add_movement_detection_constraints
from frjmp.model.objective_function import (
    minimize_total_unit_movements,
    minimize_total_position_movements,
)
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.parameters.position_unit_model import (
    PositionsUnitTypeDependency,
)
from frjmp.model.sets.unit import UnitType
from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position
from frjmp.utils.timeline_utils import (
    trim_jobs_before_time_inplace,
    trim_jobs_after_time_inplace,
    compress_timepoints,
)
from frjmp.utils.validation_utils import (
    validate_capacity_feasibility,
    validate_non_overlapping_jobs_per_unit,
    validate_job_time_format,
)
from frjmp.model.logger import IncrementalSolverLogger
from frjmp.model.adapter import TimeAdapter


class Problem:

    # Solver Properties
    SOLVERTIMELIMIT = 1200  # Default value in seconds
    STEPTIMELIMIT = 120  # Default value in seconds

    def __init__(
        self,
        jobs: list[Job],
        positions_configuration: PositionsConfiguration,
        position_unittype_dependency: PositionsUnitTypeDependency,
        time_adapter: TimeAdapter,
        t_last=None,
        initial_conditions: dict = None,
    ):
        # Init variables
        self.jobs = jobs
        self.positions_configuration = positions_configuration
        self.positions = positions_configuration.positions
        self.pos_unit_model_dependency = position_unittype_dependency
        self.unit_types = position_unittype_dependency.unit_types
        self.time_adapter = time_adapter
        t_init = time_adapter.origin
        self.initial_conditions = initial_conditions

        # Convert bounds to ticks
        t_init_tick = time_adapter.to_tick(t_init)
        t0_tick = t_init_tick - 1
        t0 = time_adapter.from_tick(t0_tick)
        # If there is no t_last use the latest job end
        if t_last is None:
            if not jobs:
                raise ValueError("Provide t_last when jobs is empty.")
            t_last_tick = max(time_adapter.to_tick(j.end) for j in jobs)
            t_last = time_adapter.from_tick(t_last_tick)  # value (date, shift, dt…)
        else:
            t_last_tick = time_adapter.to_tick(t_last)

        self.t_init_tick = t_init_tick
        self.t0_tick = t0_tick
        self.t0 = t0
        self.t_last_tick = t_last_tick

        # Other variables
        self.fixed_variables = (
            []
        )  # List of (var, value) of fixed variables. This can be used for initial or contour conditions.

        # --- Pre-processing ---#
        validate_job_time_format(jobs, time_adapter)
        validate_non_overlapping_jobs_per_unit(jobs, time_adapter)
        trim_jobs_before_time_inplace(jobs, t0, time_adapter)
        trim_jobs_after_time_inplace(jobs, t_last, time_adapter)

        # Calculate compressed time scale
        (
            compressed_ticks,
            tick_to_index,
            index_to_tick,
            index_to_value,
        ) = compress_timepoints(
            jobs,
            adapter=time_adapter,
            individual_points=[self.t0],  # Include the t0 point.
        )
        self.compressed_ticks = compressed_ticks
        self.tick_to_index = tick_to_index
        self.index_to_tick = index_to_tick
        self.index_to_value = index_to_value

        # Time step indexes start at 0 like: 0, 1, ...., len(compressed_ticks)
        self.time_step_indexes = list(range(len(compressed_ticks)))
        self.num_time_steps = len(self.time_step_indexes)

        # --- Feasability Validations --- #
        validate_capacity_feasibility(
            jobs,
            self.positions,
            self.compressed_ticks,
            self.tick_to_index,
            self.time_adapter,
            self.index_to_value,
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
            self.compressed_ticks,
            self.tick_to_index,
            self.time_adapter,
        )
        self.unit_movement_vars = create_unit_movement_variables(
            self.model, self.jobs, self.num_time_steps
        )
        self.movement_in_position_vars = create_movement_in_position_variables(
            self.model, self.positions, self.num_time_steps
        )

        self.pattern_assigned_vars = create_pattern_assignment_variables(
            self.model,
            self.jobs,
            self.compressed_ticks,
            self.tick_to_index,
            self.pos_unit_model_dependency,
            self.assigned_vars,
            self.time_adapter,
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
            self.tick_to_index,
            self.compressed_ticks,
            self.pos_unit_model_dependency,
            self.time_adapter,
        )

        add_movement_detection_constraints(
            self.model,
            self.assigned_vars,
            self.pattern_assigned_vars,
            self.unit_movement_vars,
            self.movement_in_position_vars,
            self.jobs,
            num_timesteps=self.num_time_steps,
            positions_configuration=self.positions_configuration,
        )

        add_position_capacity_constraints(
            self.model,
            self.assigned_vars,
            self.positions,
            self.jobs,
            num_timesteps=self.num_time_steps,
        )

    def set_objective(self):
        total_movements = minimize_total_unit_movements(
            self.model, self.unit_movement_vars
        )

        # total_movements = minimize_total_position_movements(
        #     self.model, self.movement_in_position_vars
        # )
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

    def add_fixed_unit_movement(self, unit_name, t_idx, value=True):
        try:
            var = self.unit_movement_vars[unit_name][t_idx]
        except KeyError:
            raise ValueError(
                f"Invalid fixed movement: variable for unit '{unit_name}' at time {t_idx} does not exist."
            )
        self.fixed_variables.append((var, value))
        return var

    def add_fixed_bool_var(self, var, value=True):
        # Appends to fixed_variables[] a boolean variable and its desired fixed value.
        self.fixed_variables.append((var, value))

    def _apply_initial_conditions_as_fixed_patterns(self):
        """
        Apply initial movement and assignment conditions at t0 using fixed variables.

        Raises:
            ValueError: If no active job exists at t0 for a unit.
            ValueError: If no valid pattern matches the given assignment.
        """
        # Use compressed index for t0
        t0_idx = self.tick_to_index[self.t0_tick]

        # Position/model index maps
        pos_index = {p.name: idx for idx, p in enumerate(self.positions)}
        model_index = {model: idx for idx, model in enumerate(self.unit_types)}

        pattern_matrix = self.pos_unit_model_dependency.generate_matrix()

        for unit, assigned_positions in self.initial_conditions["assignments"].items():
            assigned_pos_names = {pos.name for pos in assigned_positions}
            model = unit.type
            model_idx = model_index[model]

            # Find job active at t0_tick
            job_idx = None
            for j_idx, job in enumerate(self.jobs):
                start_tick = self.time_adapter.to_tick(job.start)
                end_tick = self.time_adapter.to_tick(job.end)
                if job.unit == unit and start_tick <= self.t0_tick <= end_tick:
                    job_idx = j_idx
                    break

            if job_idx is None:
                raise ValueError(f"No active job found for {unit.name} at t0.")

            # Match pattern from matrix
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
                    f"No matching pattern found for unit {unit.name} with positions {assigned_pos_names}."
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
