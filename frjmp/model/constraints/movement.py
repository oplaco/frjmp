from ortools.sat.python import cp_model
from typing import Dict


def add_movement_detection_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    movement_vars: Dict[int, Dict[int, cp_model.IntVar]],
    num_positions: int,
    num_timesteps: int,
):
    """
    For each job j, detect if its position has changed between t-1 and t.
    If yes, set movement_vars[j][t] == 1.
    """
    for j_idx in assigned_vars:
        for t_idx in range(1, num_timesteps):  # skip t=0, no previous step
            # We'll count the position difference at t-1 and t
            diffs = []
            for p_idx in range(num_positions):
                x_prev = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t_idx - 1)
                x_curr = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t_idx)
            if x_prev is not None and x_curr is not None:
                b = model.NewBoolVar(f"diff_j{j_idx}_p{p_idx}_t{t_idx}")
                model.Add(x_prev != x_curr).OnlyEnforceIf(b)
                model.Add(x_prev == x_curr).OnlyEnforceIf(b.Not())
                diffs.append(b)

            if diffs:
                model.AddMaxEquality(movement_vars[j_idx][t_idx], diffs)
