from ortools.sat.python import cp_model
from frjmp.model.sets.job import Job
from frjmp.model.parameters.position_aircraft_model import (
    PositionsAircraftModelDependency,
)
from frjmp.model.sets.aircraft import AircraftModel
from datetime import date
from frjmp.utils.timeline_utils import get_active_time_indices


def create_pattern_assignment_variables(
    model: cp_model.CpModel,
    jobs: list[Job],
    compressed_dates: list[date],
    date_to_index: dict[date, int],
    dependency: PositionsAircraftModelDependency,
    aircraft_models: list[AircraftModel],
):
    """
    Create Boolean variables pattern_assigned_vars[j][t][k] that select the pattern k
    for job j at time step t.
    """
    pattern_assigned_vars = {}
    matrix = dependency.generate_matrix()
    model_to_index = {model: idx for idx, model in enumerate(aircraft_models)}

    for j_idx, job in enumerate(jobs):
        pattern_assigned_vars[j_idx] = {}

        model_idx = model_to_index[job.aircraft.model]
        n_patterns = len(matrix[model_idx])

        active_time_indices = get_active_time_indices(
            job, compressed_dates, date_to_index
        )

        for t_idx in active_time_indices:
            pattern_assigned_vars[j_idx][t_idx] = {}

            for k_idx in range(n_patterns):
                y_var = model.NewBoolVar(
                    f"pattern_assigned_j{j_idx}_t{t_idx}_pat{k_idx}"
                )
                pattern_assigned_vars[j_idx][t_idx][k_idx] = y_var

    return pattern_assigned_vars
