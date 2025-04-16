from ortools.sat.python import cp_model
from frjmp.model.sets.job import Job


def create_movement_variables(
    model: cp_model.CpModel, jobs: list[Job], time_indices: list[int]
):
    movement_vars = {}

    for j_idx, job in enumerate(jobs):
        movement_vars[j_idx] = {}
        for t_idx in range(1, len(time_indices)):
            movement_vars[j_idx][t_idx] = model.NewBoolVar(
                f"movement_vars_j{j_idx}_t{t_idx}"
            )

    return movement_vars
