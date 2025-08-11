from datetime import date
from ortools.sat.python import cp_model

from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position
from frjmp.model.parameters.position_unit_model import (
    PositionsUnitTypeDependency,
)


def add_job_assignment_constraints(
    model: cp_model.CpModel,
    assigned_vars: dict[int, dict[int, dict[int, cp_model.IntVar]]],
    pattern_assigned_vars: dict[int, dict[int, dict[int, cp_model.IntVar]]],
    jobs: list[Job],
    positions: list[Position],
    date_to_index: dict[date, int],
    compressed_dates: list[date],
    dependency: PositionsUnitTypeDependency,
):
    """
    Link pattern assignment variables to position assignment variables.
    - All the jobs must be assigned to at least one pattern in each time step.
    - If a job is assigned to a pattern (pattern_assigned_vars), the job must
        be assigned (assigned_var) to all the positions belonging to that pattern.
        This can raise a ValueError if the pattern contains a position that does
        not cover the job phase need.
    """
    matrix = dependency.generate_matrix()
    unit_types = dependency.unit_types
    model_to_index = {model: idx for idx, model in enumerate(unit_types)}

    for j_idx, job in enumerate(jobs):
        model_idx = model_to_index[job.unit.model]
        n_patterns = len(matrix[model_idx])
        for t_date in compressed_dates:
            if not (job.start <= t_date <= job.end):
                # Avoid creating unnecessary constraints (i.e outside time domain of the job).
                continue
            t_idx = date_to_index[t_date]

            # 1. ExactlyOne over pattern_assigned_vars[j][t]
            model.AddExactlyOne(list(pattern_assigned_vars[j_idx][t_idx].values()))

            # 2. Link assigned_vars[j][p][t] to pattern selection (pattern_assigned_vars).
            for p_idx, _ in enumerate(positions):
                a_var = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t_idx, None)

                if a_var is None:
                    # For the moment I dont think it makes sense to raise and error. If a job cant be done in a position because the latter
                    # does not cover it needs, the variable wont be created (to save memory and time). If this position cant host the job we
                    # cant expect either the pattern to be able to do so. Since patterns are related to units and needs to jobs we cant
                    # directly not create pattern_assigment_vars as well as assigment_vars.
                    continue
                    # raise ValueError(
                    #     f"Pattern {k_idx} expects position {positions[p_idx]} for job {jobs[j_idx]} at time {t_idx}, "
                    #     f"but no assigned_var exists. Check either patterns or compatible positions (if needs are covered by the position)."
                    # )
                terms = []
                for k_idx in range(n_patterns):
                    if matrix[model_idx][k_idx][p_idx] == 1:
                        terms.append(pattern_assigned_vars[j_idx][t_idx][k_idx])

                if a_var is not None:
                    if terms:
                        model.Add(sum(terms) == a_var)
                    else:
                        model.Add(a_var == 0)
