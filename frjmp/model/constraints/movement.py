from frjmp.model.parameters.movement_dependency import MovementDependency
from frjmp.model.sets.job import Job
from collections import defaultdict
from ortools.sat.python import cp_model
from typing import Dict
from collections import defaultdict


def add_movement_detection_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    aircraft_movement_vars: Dict[int, Dict[int, cp_model.IntVar]],
    movement_in_position_vars: Dict[int, Dict[int, cp_model.IntVar]],
    jobs: list[Job],
    num_positions: int,
    num_timesteps: int,
    movement_dependency: MovementDependency,
):
    """
    Adds movement detection constraints for all jobs.

    Args:
        model: OR-Tools CP model
        assigned_vars: assignment variables [job][position][time]
        aircraft_movement_vars: movement detection variables [job][time]
        num_positions: number of positions
        num_timesteps: number of time steps
        forced_movements: optional dict specifying forced movement times per job
    """
    add_aircraft_movement_constraint(
        model, assigned_vars, aircraft_movement_vars, jobs, num_positions, num_timesteps
    )

    add_movement_dependency_constraints(
        model, movement_in_position_vars, movement_dependency, num_timesteps
    )

    link_aircraft_movements_to_position_movements(
        model,
        assigned_vars,
        movement_in_position_vars,
        aircraft_movement_vars,
        jobs,
    )


def add_aircraft_movement_constraint(
    model: cp_model.CpModel,
    assigned_vars: dict,
    aircraft_movement_vars: dict,
    jobs: list,
    num_positions: int,
    num_timesteps: int,
):
    """
    Adds movement detection and enforcement constraints:
    - Detects when an aircraft changes position between t-1 and t.
    - Ensures that if a movement is forced at t, then the position must change.
    """

    # Group job indices by aircraft
    aircraft_to_jobs = defaultdict(list)
    for j_idx, job in enumerate(jobs):
        aircraft_to_jobs[job.aircraft.name].append(j_idx)

    for aircraft_name, job_indices in aircraft_to_jobs.items():
        for t in range(1, num_timesteps):
            diffs = []

            for p_idx in range(num_positions):
                x_prev_terms = []
                x_curr_terms = []

                for j_idx in job_indices:
                    # Note: We only include vars that were actually created (Remember assignments do not exist outside active time indexes, x_prev for start date is None)
                    x_prev = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t - 1)
                    x_curr = assigned_vars.get(j_idx, {}).get(p_idx, {}).get(t)

                    if x_prev is not None:
                        x_prev_terms.append(x_prev)
                    if x_curr is not None:
                        x_curr_terms.append(x_curr)

                # If no terms exist for both prev and curr, skip this position
                if not x_prev_terms and not x_curr_terms:
                    continue

                # Safe: If only prev or curr exists, treat missing as 0
                x_prev_sum = sum(x_prev_terms) if x_prev_terms else model.NewConstant(0)
                x_curr_sum = sum(x_curr_terms) if x_curr_terms else model.NewConstant(0)

                # Create a bool diff = 1 if usage changed for this position
                diff = model.NewBoolVar(f"diff_{aircraft_name}_p{p_idx}_t{t}")
                model.Add(x_prev_sum != x_curr_sum).OnlyEnforceIf(diff)
                model.Add(x_prev_sum == x_curr_sum).OnlyEnforceIf(diff.Not())
                diffs.append(diff)

            if diffs:
                # DETECT: any diff → movement
                model.AddMaxEquality(aircraft_movement_vars[aircraft_name][t], diffs)

                # ENFORCE: movement → any diff
                model.AddBoolOr(diffs).OnlyEnforceIf(
                    aircraft_movement_vars[aircraft_name][t]
                )


def add_movement_dependency_constraints(
    model, movement_in_position_vars, movement_dependency, num_timesteps
):
    dependency_matrix, index_map = movement_dependency.generate_matrix()
    size = len(dependency_matrix)
    for from_idx in range(size):
        for to_idx in range(size):
            if dependency_matrix[from_idx][to_idx] == 1:
                for t in range(num_timesteps):
                    try:
                        var_from = movement_in_position_vars[from_idx][t]
                        var_to = movement_in_position_vars[to_idx][t]
                        model.AddImplication(var_from, var_to)
                    except KeyError:
                        raise ValueError(
                            "Invalid entrance in add_movement_dependency_constraints"
                        )
                        # continue  # skip invalid entries


def link_aircraft_movements_to_position_movements(
    model,
    assigned_vars,
    movement_in_position_vars,
    aircraft_movement_vars,
    jobs,
):
    """
    If an aircraft is assigned to a position at time t and moves at t,
    then that position must also register a movement.

    Args:
        model: OR-Tools model.
        assigned_vars: Dict[j][p][t] → BoolVar
        movement_in_position_vars: Dict[p][t] → BoolVar
        aircraft_movement_vars: Dict[aircraft_name][t] → BoolVar
        jobs: List of Job objects
    """
    for p_idx in movement_in_position_vars:
        for t_idx in movement_in_position_vars[p_idx]:
            triggers = []

            for j_idx, job in enumerate(jobs):
                if (
                    p_idx in assigned_vars.get(j_idx, {})
                    and t_idx in assigned_vars[j_idx][p_idx]
                ):
                    is_assigned = assigned_vars[j_idx][p_idx][t_idx]
                    aircraft_moved = aircraft_movement_vars[job.aircraft.name][t_idx]

                    # trigger_var = is_assigned AND aircraft_moved
                    trigger_var = model.NewBoolVar(
                        f"trigger_p{p_idx}_t{t_idx}_j{j_idx}"
                    )
                    model.AddBoolAnd([is_assigned, aircraft_moved]).OnlyEnforceIf(
                        trigger_var
                    )
                    model.AddBoolOr(
                        [is_assigned.Not(), aircraft_moved.Not()]
                    ).OnlyEnforceIf(trigger_var.Not())
                    triggers.append(trigger_var)

            if triggers:
                # If any aircraft that was assigned here moved, the position moved
                model.AddMaxEquality(movement_in_position_vars[p_idx][t_idx], triggers)
            else:
                # No job is even assigned here → movement must be 0
                model.Add(movement_in_position_vars[p_idx][t_idx] == 0)
