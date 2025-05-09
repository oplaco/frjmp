from ortools.sat.python import cp_model
from typing import Dict


def minimize_total_aircraft_movements(
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


def minimize_total_position_movements(
    model: cp_model.CpModel,
    movement_in_position_vars: Dict[int, Dict[int, cp_model.IntVar]],
):
    """
    Add an objective to minimize the total number of position movements.
    """
    all_moves = []
    for p_idx, p_dict in movement_in_position_vars.items():
        for t_idx, var in p_dict.items():
            all_moves.append(var)

    total_movements = sum(all_moves)
    model.Minimize(total_movements)
    return total_movements
