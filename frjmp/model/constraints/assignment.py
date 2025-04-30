from datetime import date
from ortools.sat.python import cp_model

from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position
from frjmp.model.parameters.position_aircraft_model import (
    PositionsAircraftModelDependency,
)


def add_job_assignment_constraints(
    model: cp_model.CpModel,
    assigned_vars: dict[int, dict[int, dict[int, cp_model.IntVar]]],
    pattern_assigned_vars: dict[int, dict[int, dict[int, cp_model.IntVar]]],
    jobs: list[Job],
    positions: list[Position],
    date_to_index: dict[date, int],
    compressed_dates: list[date],
    dependency: PositionsAircraftModelDependency,
):
    """
    Link pattern assignment variables to position assignment variables.
    """
    matrix = dependency.generate_matrix()
    aircraft_models = dependency.aircraft_models
    model_to_index = {model: idx for idx, model in enumerate(aircraft_models)}

    for j_idx, job in enumerate(jobs):
        model_idx = model_to_index[job.aircraft.model]
        n_patterns = len(matrix[model_idx])
        for t_date in compressed_dates:
            if not (job.start <= t_date <= job.end):
                # Avoid creating unnecessary constraints (i.e outside time domain of the job).
                continue
            t_idx = date_to_index[t_date]

            # 1. ExactlyOne over pattern_assigned_vars[j][t]
            model.AddExactlyOne(list(pattern_assigned_vars[j_idx][t_idx].values()))
            # 2. Link assigned_vars[j][p][t] to pattern selection.
            for p_idx, _ in enumerate(positions):
                a_var = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t_idx, None)

                terms = []
                for k_idx in range(n_patterns):
                    if matrix[model_idx][k_idx][p_idx] == 1:
                        if a_var is None:
                            raise ValueError(
                                f"Pattern {k_idx} expects position {p_idx} for job {j_idx} at time {t_idx}, "
                                f"but no assigned_var exists. Check either patterns or compatible positions (if needs are covered by the position)."
                            )
                        terms.append(pattern_assigned_vars[j_idx][t_idx][k_idx])

                if a_var is not None:
                    if terms:
                        model.Add(sum(terms) == a_var)
                    else:
                        model.Add(a_var == 0)
