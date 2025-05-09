from frjmp.model.parameters.movement_dependency import MovementDependency
from frjmp.model.sets.job import Job
from collections import defaultdict
from ortools.sat.python import cp_model
from typing import Dict
from collections import defaultdict


def add_movement_detection_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    pattern_assigned_vars,
    aircraft_movement_vars: Dict[int, Dict[int, cp_model.IntVar]],
    movement_in_position_vars: Dict[int, Dict[int, cp_model.IntVar]],
    jobs: list[Job],
    num_timesteps: int,
    movement_dependency: MovementDependency,
):
    """
    Adds movement detection constraints for all jobs.

    Args:
        model: OR-Tools CP model
        assigned_vars: assignment variables [job][position][time]
        aircraft_movement_vars: movement detection variables [job][time]
        num_timesteps: number of time steps
        forced_movements: optional dict specifying forced movement times per job
    """
    add_aircraft_movement_constraint(
        model, pattern_assigned_vars, aircraft_movement_vars, jobs, num_timesteps
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
    pattern_assigned_vars: dict[int, dict[int, dict[int, cp_model.IntVar]]],
    aircraft_movement_vars: dict[str, dict[int, cp_model.IntVar]],
    jobs: list,
    num_timesteps: int,
):
    from collections import defaultdict

    # group jobs by aircraft
    ac_to_jobs = defaultdict(list)
    for j_idx, job in enumerate(jobs):
        ac_to_jobs[job.aircraft.name].append(j_idx)

    for ac_name, job_idxs in ac_to_jobs.items():
        for t in range(num_timesteps - 1):
            diffs: list[cp_model.BoolVar] = []

            # 2a) find every pattern k that ever appears at t or t+1
            k_set = set()  # Existing patterns for job j in t and t+1
            for j in job_idxs:
                if t in pattern_assigned_vars[j]:
                    k_set.update(pattern_assigned_vars[j][t].keys())
                if t + 1 in pattern_assigned_vars[j]:
                    k_set.update(pattern_assigned_vars[j][t + 1].keys())

            # 2b) for each pattern k, sum across jobs at t vs t+1
            for k in k_set:
                prev_sum_terms = []
                next_sum_terms = []

                for j in job_idxs:
                    prev = pattern_assigned_vars[j].get(t, {}).get(k)
                    nxt = pattern_assigned_vars[j].get(t + 1, {}).get(k)

                    if prev is not None:
                        prev_sum_terms.append(prev)
                    if nxt is not None:
                        next_sum_terms.append(nxt)

                if len(prev_sum_terms) == 0 and len(next_sum_terms) == 0:
                    continue  # job doesn't exist at t or t+1, skip
                sum_prev = (
                    sum(prev_sum_terms) if prev_sum_terms else model.NewConstant(0)
                )
                sum_next = (
                    sum(next_sum_terms) if next_sum_terms else model.NewConstant(0)
                )

                diff = model.NewBoolVar(f"diff_{ac_name}_k{k}_t{t}")
                model.Add(sum_prev != sum_next).OnlyEnforceIf(diff)
                model.Add(sum_prev == sum_next).OnlyEnforceIf(diff.Not())
                diffs.append(diff)

            # 4) movement[t] = OR(diffs)
            if diffs:
                mov = aircraft_movement_vars[ac_name][t]
                model.AddBoolOr(diffs).OnlyEnforceIf(mov)
                # and keep its value in sync
                model.AddMaxEquality(mov, diffs)


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
    An aircraft movement at t (between t and t+1) between position p and p' must enforce a position movement
    at t in both p and p' (movement_in_position_vars[p][t] and movement_in_position_vars[p'][t]).
    We need to check  assigned_var[j][p'][t+1] so we know to which position it was assigned.
    In the contrary, if there is a movement in postion p at time t. There is only an aircraft movement
    if any of the jobs of that aircraft is assigned to that position according to assigned_var[j][p][t] (for all j).


    This links aircraft-level movement to the spatial footprint of position-level movement.
    """

    # 1) Group job‐indices by aircraft name
    aircraft_to_jobs: dict[str, list[int]] = defaultdict(list)
    for j_idx, job in enumerate(jobs):
        aircraft_to_jobs[job.aircraft.name].append(j_idx)

    # 2) For each aircraft and each time‐slice t
    for ac_name, job_idxs in aircraft_to_jobs.items():
        for t, ac_mov in aircraft_movement_vars[ac_name].items():
            # FORWARD: ac_mov + assignment to p at t or t+1 → movement in p at t
            for j in job_idxs:
                for p, t_dict in assigned_vars.get(j, {}).items():
                    if t in t_dict:
                        assigned = assigned_vars[j][p][t]
                        model.AddImplication(
                            ac_mov, movement_in_position_vars[p][t]
                        ).OnlyEnforceIf(assigned)
                    if t + 1 in t_dict:
                        assigned = assigned_vars[j][p][t + 1]
                        model.AddImplication(
                            ac_mov, movement_in_position_vars[p][t]
                        ).OnlyEnforceIf(assigned)

            # BACKWARD: movement in p at t + assignment to p at t → ac_mov
            for j in job_idxs:
                for p, t_dict in assigned_vars.get(j, {}).items():
                    if t in t_dict:
                        assigned = assigned_vars[j][p][t]
                        pos_mov = movement_in_position_vars[p][t]
                        # (assigned AND pos_mov) ⇒ ac_mov
                        model.AddBoolOr([assigned.Not(), pos_mov.Not(), ac_mov])
