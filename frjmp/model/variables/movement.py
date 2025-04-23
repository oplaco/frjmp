from ortools.sat.python import cp_model
from typing import Dict, List
from frjmp.model.sets.job import Job


def create_aircraft_movement_variables(
    model: cp_model.CpModel, jobs: List[Job], time_indices: List[int]
) -> Dict[str, Dict[int, cp_model.IntVar]]:
    """
    Creates movement variables per aircraft per time step.

    Args:
        model: OR-Tools CP model.
        jobs: List of Job objects.
        time_indices: List of time steps (can be compressed indices or actual steps).

    Returns:
        Dict of movement_vars[aircraft_name][t_idx] = BoolVar
    """
    movement_vars = {}
    aircraft_names = sorted(set(job.aircraft.name for job in jobs))

    for aircraft_name in aircraft_names:
        movement_vars[aircraft_name] = {}
        # Movements are posible starting and including t0
        for t_idx in range(0, len(time_indices)):
            movement_vars[aircraft_name][t_idx] = model.NewBoolVar(
                f"movement_{aircraft_name}_t{t_idx}"
            )

    return movement_vars
