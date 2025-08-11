from ortools.sat.python import cp_model
from frjmp.model.sets.job import Job
from frjmp.model.parameters.position_unit_model import (
    PositionsUnitTypeDependency,
)
from frjmp.model.sets.unit import UnitType
from datetime import date
from frjmp.utils.timeline_utils import get_active_time_indices
import warnings


def create_pattern_assignment_variables(
    model: cp_model.CpModel,
    jobs: list[Job],
    compressed_dates: list[date],
    date_to_index: dict[date, int],
    dependency: PositionsUnitTypeDependency,
    assigned_vars,
):
    """
    Create Boolean variables pattern_assigned_vars[j][t][k] that select pattern k
    for job j at time step t — but only if the pattern is valid for that job at that time.

    A pattern is considered valid if all positions it uses are compatible with the job's needs.
    This is determined by checking whether an assigned_var[j][p][t] exists.
    """
    pattern_assigned_vars = {}
    matrix = dependency.generate_matrix()
    model_to_index = {model: idx for idx, model in enumerate(dependency.unit_types)}

    for j_idx, job in enumerate(jobs):
        pattern_assigned_vars[j_idx] = {}

        model_idx = model_to_index[job.unit.model]
        n_patterns = len(matrix[model_idx])

        active_time_indices = get_active_time_indices(
            job, compressed_dates, date_to_index
        )

        for t_idx in active_time_indices:
            pattern_assigned_vars[j_idx][t_idx] = {}

            for k_idx in range(n_patterns):
                # Extract all positions used by this pattern
                pattern_positions = [
                    p_idx
                    for p_idx, uses in enumerate(matrix[model_idx][k_idx])
                    if uses == 1
                ]

                # Check if all these positions have a valid assigned_var[j][p][t]
                pattern_is_valid = all(
                    p_idx in assigned_vars.get(j_idx, {})
                    and t_idx in assigned_vars[j_idx][p_idx]
                    for p_idx in pattern_positions
                )

                if not pattern_is_valid:
                    # Skip this pattern for this job at this time — not all positions are compatible
                    incompatible_pos_names = [
                        dependency.available_positions[p_idx].name
                        for p_idx in pattern_positions
                        if not (
                            p_idx in assigned_vars.get(j_idx, {})
                            and t_idx in assigned_vars[j_idx][p_idx]
                        )
                    ]
                    # warnings.warn(
                    #     f"Skipped pattern {k_idx} for Job {job} (UnitType={job.unit.model}) at t={t_idx}: "
                    #     f"positions {incompatible_pos_names} do not cover job need ({job.phase.required_need}).",
                    #     stacklevel=2,
                    # )
                    continue

                # Create variable only if the pattern is fully compatible with the job
                y_var = model.NewBoolVar(
                    f"pattern_assigned_j{j_idx}_t{t_idx}_pat{k_idx}"
                )
                pattern_assigned_vars[j_idx][t_idx][k_idx] = y_var

    return pattern_assigned_vars
