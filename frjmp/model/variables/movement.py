from ortools.sat.python import cp_model
from typing import Dict, List
from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position


def create_unit_movement_variables(
    model: cp_model.CpModel, jobs: List[Job], time_indices: List[int]
) -> Dict[str, Dict[int, cp_model.IntVar]]:
    """
    Creates movement variables per unit per time step.

    Args:
        model: OR-Tools CP model.
        jobs: List of Job objects.
        time_indices: List of time steps (can be compressed indices or actual steps).

    Returns:
        Dict of unit_movement_vars[unit_name][t_idx] = BoolVar
    """
    unit_movement_vars = {}
    unit_names = sorted(set(job.unit.name for job in jobs))

    for unit_name in unit_names:
        unit_movement_vars[unit_name] = {}
        # Movements are posible starting and including t0
        for t_idx in range(0, len(time_indices)):
            unit_movement_vars[unit_name][t_idx] = model.NewBoolVar(
                f"movement_{unit_name}_t{t_idx}"
            )

    return unit_movement_vars


def create_movement_in_position_variables(
    model: cp_model.CpModel,
    positions: List[Position],
    time_indices: List[int],
) -> Dict[int, Dict[int, cp_model.IntVar]]:
    """
    Creates movement variables per position per time step.

    These variables represent whether there is any unit-related movement
    in a given position at a given time step. They are useful for modeling
    dependency cascades between positions.

    Args:
        model: OR-Tools CP model.
        positions: List of Position objects.
        time_indices: List of time steps (can be compressed indices or actual steps).

    Returns:
        Dict of movement_in_position_vars[position_index][t_idx] = BoolVar
    """
    movement_in_position_vars = {}

    for p_idx, position in enumerate(positions):
        movement_in_position_vars[p_idx] = {}
        for t_idx in range(0, len(time_indices)):
            movement_in_position_vars[p_idx][t_idx] = model.NewBoolVar(
                f"movement_in_pos_{position.name}_t{t_idx}"
            )

    return movement_in_position_vars
