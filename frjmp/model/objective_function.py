from ortools.sat.python import cp_model
from typing import Dict


def minimize_total_movements(
    model: cp_model.CpModel,
    aircraft_movement_vars_vars: Dict[int, Dict[int, cp_model.IntVar]],
):
    """
    Add an objective to minimize the total number of aircraft movements.
    """
    all_moves = []
    for aircraft_id, time_dict in aircraft_movement_vars_vars.items():
        for var in time_dict.values():
            all_moves.append(var)

    total_movements = sum(all_moves)
    model.Minimize(total_movements)
    return total_movements
