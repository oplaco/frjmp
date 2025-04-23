from frjmp.model.sets.job import Job
from collections import defaultdict
from ortools.sat.python import cp_model
from typing import Dict


def add_movement_detection_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    movement_vars: Dict[int, Dict[int, cp_model.IntVar]],
    jobs: list[Job],
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
        model, assigned_vars, movement_vars, jobs, num_positions, num_timesteps
    )

    if forced_movements:
        apply_forced_movements(model, movement_vars, forced_movements)


def detect_intra_position_movements(
    model: cp_model.CpModel,
    assigned_vars: dict,
    movement_vars: dict,
    jobs: list,
    num_positions: int,
    num_timesteps: int,
):
    """
    Detects when an aircraft moves between positions across consecutive time steps.
    A movement is triggered if the aircraft is assigned to different positions at t-1 and t.

    Inputs:
        model: OR-Tools CP model
        assigned_vars: Dict[job][position][time] -> BoolVar indicating assignment
        movement_vars: Dict[aircraft_name][time] -> BoolVar to track movement
        jobs: list of Job objects
        num_positions: total number of positions
        num_timesteps: total number of time steps
    """
    # Group jobs by aircraft
    aircraft_to_jobs = defaultdict(list)
    for j_idx, job in enumerate(jobs):
        aircraft_to_jobs[job.aircraft].append(j_idx)

    # For each aircraft and each time step, check if position has changed
    for aircraft, job_indices in aircraft_to_jobs.items():
        aircraft_name = aircraft.name
        for t_idx in range(1, num_timesteps):  # We skip t = 0 (no previous step)
            diffs = []

            # For each position, compare total assignment at t-1 and t
            for p_idx in range(num_positions):
                # Collect all job assignments for this aircraft to this position
                prev_assignments = [
                    assigned_vars[j][p_idx][t_idx - 1]
                    for j in job_indices
                    if p_idx in assigned_vars[j]
                    and t_idx - 1 in assigned_vars[j][p_idx]
                ]
                curr_assignments = [
                    assigned_vars[j][p_idx][t_idx]
                    for j in job_indices
                    if p_idx in assigned_vars[j] and t_idx in assigned_vars[j][p_idx]
                ]

                if prev_assignments and curr_assignments:
                    # Sum of assignments at t-1 and t for this position
                    sum_prev = model.NewIntVar(
                        0,
                        len(prev_assignments),
                        f"sum_prev_{aircraft_name}_p{p_idx}_t{t_idx}",
                    )
                    sum_curr = model.NewIntVar(
                        0,
                        len(curr_assignments),
                        f"sum_curr_{aircraft_name}_p{p_idx}_t{t_idx}",
                    )
                    model.Add(sum_prev == sum(prev_assignments))
                    model.Add(sum_curr == sum(curr_assignments))

                    # Boolean variable indicating if assignment changed at this position
                    b = model.NewBoolVar(f"diff_{aircraft_name}_p{p_idx}_t{t_idx}")
                    model.Add(sum_prev != sum_curr).OnlyEnforceIf(b)
                    model.Add(sum_prev == sum_curr).OnlyEnforceIf(b.Not())
                    diffs.append(b)

            # If any position assignment changed → movement = 1
            if diffs:
                model.AddMaxEquality(movement_vars[aircraft_name][t_idx], diffs)


def apply_forced_movements(model, movement_vars, forced_movements):
    """
    Enforces that specific aircraft must move at given time steps.

    Args:
        movement_vars: Dict[aircraft_name][t_idx] -> BoolVar
        forced_movements: Dict[aircraft_name][t_idx] = True if must move
    """
    for aircraft_name, times in forced_movements.items():
        for t_idx, force in times.items():
            if force:
                model.Add(movement_vars[aircraft_name][t_idx] == 1)
