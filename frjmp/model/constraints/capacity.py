from ortools.sat.python import cp_model
from typing import Dict, List

from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position


def add_position_capacity_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    positions: List[Position],
    jobs: List[Job],
    num_timesteps: int,
):
    """
    For each position and each time step, the number of assigned jobs must not exceed the position's capacity.

    Args:
        model: OR-Tools CP model
        assigned_vars: assigned_var[j][p][t] = BoolVar indicating job j in position p at time t
        positions: List of Position objects (must include `.capacity`)
        jobs: List of jobs
        num_timesteps: Total number of compressed time steps
    """
    for p_idx, position in enumerate(positions):
        for t_idx in range(num_timesteps):
            active_vars = []
            for j_idx in range(len(jobs)):
                if (
                    p_idx in assigned_vars.get(j_idx, {})
                    and t_idx in assigned_vars[j_idx][p_idx]
                ):
                    active_vars.append(assigned_vars[j_idx][p_idx][t_idx])

            if active_vars:
                model.Add(sum(active_vars) <= position.capacity)
