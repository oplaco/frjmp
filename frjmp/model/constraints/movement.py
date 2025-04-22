from ortools.sat.python import cp_model
from typing import Dict


def add_movement_detection_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    movement_vars: Dict[int, Dict[int, cp_model.IntVar]],
    num_positions: int,
    num_timesteps: int,
    forced_movements: Dict[int, Dict[int, bool]] = None,
):
    """
    Adds movement detection constraints for all jobs.

    Args:
        model: OR-Tools CP model
        assigned_vars: assignment variables [job][position][time]
        movement_vars: movement detection variables [job][time]
        num_positions: number of positions
        num_timesteps: number of time steps
        forced_movements: optional dict specifying forced movement times per job
    """
    detect_intra_position_movements(
        model, assigned_vars, movement_vars, num_positions, num_timesteps
    )

    if forced_movements:
        apply_forced_movements(model, movement_vars, forced_movements)


def detect_intra_position_movements(
    model, assigned_vars, movement_vars, num_positions, num_timesteps
):
    """
    Detect movements between positions for assigned jobs.
    If a job is in a different position at t-1 and t, movement = 1.
    """
    for j_idx in assigned_vars:
        for t_idx in range(1, num_timesteps):  # skip t=0
            diffs = []
            for p_idx in range(num_positions):
                x_prev = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t_idx - 1)
                x_curr = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t_idx)
                if x_prev is not None and x_curr is not None:
                    # If x_prev and x_curr differ (job was reassigned), b = True
                    b = model.NewBoolVar(f"diff_j{j_idx}_p{p_idx}_t{t_idx}")
                    model.Add(x_prev != x_curr).OnlyEnforceIf(b)
                    model.Add(x_prev == x_curr).OnlyEnforceIf(b.Not())
                    diffs.append(b)

            if diffs:
                # movement[j][t] = 1 if any diffs are True
                model.AddMaxEquality(movement_vars[j_idx][t_idx], diffs)


def apply_forced_movements(model, movement_vars, forced_movements):
    """
    Enforces that specific jobs must move at given time steps.

    Args:
        movement_vars: Dict[j][t] → BoolVar
        forced_movements: Dict[j][t] = True if must move
    """
    for j_idx, times in forced_movements.items():
        for t_idx, force in times.items():
            if force:
                model.Add(movement_vars[j_idx][t_idx] == 1)
