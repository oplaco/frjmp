from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.sets.job import Job
from collections import defaultdict
from ortools.sat.python import cp_model
from typing import Dict, List, Tuple, Set
from collections import defaultdict


def add_movement_detection_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    pattern_assigned_vars,
    aircraft_movement_vars: Dict[int, Dict[int, cp_model.IntVar]],
    movement_in_position_vars: Dict[int, Dict[int, cp_model.IntVar]],
    jobs: list[Job],
    num_timesteps: int,
    positions_configuration: PositionsConfiguration,
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
        model,
        movement_in_position_vars,
        aircraft_movement_vars,
        pattern_assigned_vars,
        jobs,
        positions_configuration,
        num_timesteps,
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
    model: cp_model.CpModel,
    movement_in_position_vars: Dict[int, Dict[int, cp_model.IntVar]],
    aircraft_movement_vars: Dict[str, Dict[int, cp_model.IntVar]],
    pattern_assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    jobs: List,
    positions_configuration,
    num_timesteps: int,
) -> None:
    """
    When aircraft is movev from pattern k0 to pattern k1 every possition in k0 and k1
    register a position movement. Then each position movement might trigger more position
    movements based on the dependency matrix dep_matrix[i][j][k]

    For every aircraft and every timestep t → t+1:
        * Detect the pattern k₀ the aircraft occupies at t
        * Detect the pattern k₁ it occupies at t+1
        * Create a Boolean hop variable  hop_{k₀→k₁,t}
        * If that hop is active, then
              – every position in k₀ (vacated) must register movement
              – every position in k₁ (entered) must register movement
              – every position triggered by (p_out, p_in) pairs must register movement
    Trigger logic uses a 3-D matrix:
        dep_matrix[i][j][k] == 1  ⇒  moving   i → j   triggers position k.
    """
    # Dependency / trigger lookup
    dep_matrix, index_map = positions_configuration.generate_matrix()
    P = len(dep_matrix)

    # (i, j)  → {k1, k2, …}
    trigger_map: Dict[Tuple[int, int], Set[int]] = {
        (i, j): {k for k, v in enumerate(dep_matrix[i][j]) if v}
        for i in range(P)
        for j in range(P)
        if any(dep_matrix[i][j])
    }

    # helper: Pattern  →  list[int] (indices in 0‥P-1)
    def pattern_indices(pattern) -> List[int]:
        try:
            return [index_map[pos.name] for pos in pattern.positions]
        except KeyError as err:
            raise ValueError(
                f"Position {err.args[0]} in Pattern not in positions_configuration"
            ) from None

    def movement_dependency_helper(
        pos_k0, pos_k1, t, trigger_map, model, movement_in_position_vars, hop
    ):
        touched: Set[int] = set(pos_k0) | set(pos_k1)
        # triggered positions
        for p_out in pos_k0:
            for p_in in pos_k1:
                touched.update(trigger_map.get((p_out, p_in), ()))

        for p in touched:
            try:
                pos_mov = movement_in_position_vars[p][t]
            except KeyError:
                raise ValueError(f"Missing movement var for position {p} at t={t}")
            model.AddImplication(hop, pos_mov)

    # Group job-indices by aircraft
    jobs_by_ac = defaultdict(list)  # ac_name → list[j_idx]
    for j_idx, job in enumerate(jobs):
        jobs_by_ac[job.aircraft.name].append(j_idx)

    # Build constraints
    for ac_name, job_idxs in jobs_by_ac.items():
        ac_mov_dict = aircraft_movement_vars.get(ac_name, {})

        # All jobs of this aircraft share the same AircraftModel
        aircraft_model = jobs[job_idxs[0]].aircraft.model
        allowed_patterns = aircraft_model.allowed_patterns  # list[Pattern]

        for t in range(num_timesteps - 1):  # Can not evaluate t+1
            ac_mov_t = ac_mov_dict[t]
            # --- collect (k_idx, BoolVar) pairs for t and t+1 -----------
            pat_vars_t: List[Tuple[int, cp_model.IntVar]] = []
            pat_vars_t1: List[Tuple[int, cp_model.IntVar]] = []

            for j in job_idxs:
                if t in pattern_assigned_vars[j]:
                    pat_vars_t.extend(pattern_assigned_vars[j][t].items())
                if t + 1 in pattern_assigned_vars[j]:
                    pat_vars_t1.extend(pattern_assigned_vars[j][t + 1].items())

            if ac_name == "ALPHA" and t == 0:
                pass
            # Aircraft inactive in one slice?  Nothing to do
            if not pat_vars_t and not pat_vars_t1:
                continue

            if not pat_vars_t and pat_vars_t1:
                # ----------------- iterate over every possible hop ---------- #
                for k1_idx, var_k1 in pat_vars_t1:
                    hop = model.NewBoolVar(f"hop_{ac_name}_k{k1_idx}_t{t}")

                    # hop ⇒  ac moved AND pattern k0 active AND pattern k1 active
                    model.Add(hop == 1).OnlyEnforceIf([ac_mov_t, var_k1])

                    # Positions touched by this hop
                    pos_k0 = pattern_indices(
                        allowed_patterns[0]
                    )  # We need to add an OUT position in the future, currently use position 0 which has direct access to OUT.
                    pos_k1 = pattern_indices(allowed_patterns[k1_idx])

                    movement_dependency_helper(
                        pos_k0,
                        pos_k1,
                        t,
                        trigger_map,
                        model,
                        movement_in_position_vars,
                        hop,
                    )

            elif pat_vars_t and not pat_vars_t1:
                # ----------------- iterate over every possible hop ---------- #
                for k0_idx, var_k0 in pat_vars_t:
                    hop = model.NewBoolVar(f"hop_{ac_name}_k{k0_idx}_t{t}")

                    # hop ⇒  ac moved AND pattern k0 active AND pattern k1 active
                    model.Add(hop == 1).OnlyEnforceIf([ac_mov_t, var_k0])

                    # Positions touched by this hop
                    pos_k0 = pattern_indices(allowed_patterns[k0_idx])
                    pos_k1 = pattern_indices(
                        allowed_patterns[0]
                    )  # We need to add an OUT position in the future, currently use position 0 which has direct access to OUT.

                    movement_dependency_helper(
                        pos_k0,
                        pos_k1,
                        t,
                        trigger_map,
                        model,
                        movement_in_position_vars,
                        hop,
                    )

            # ----------------- iterate over every possible hop ---------- #
            else:
                for k0_idx, var_k0 in pat_vars_t:
                    for k1_idx, var_k1 in pat_vars_t1:
                        hop = model.NewBoolVar(
                            f"hop_{ac_name}_k{k0_idx}_k{k1_idx}_t{t}"
                        )

                        # hop ⇒  ac moved AND pattern k0 active AND pattern k1 active
                        model.Add(hop == 1).OnlyEnforceIf([ac_mov_t, var_k0, var_k1])

                        # Positions touched by this hop
                        pos_k0 = pattern_indices(allowed_patterns[k0_idx])
                        pos_k1 = pattern_indices(allowed_patterns[k1_idx])

                        movement_dependency_helper(
                            pos_k0,
                            pos_k1,
                            t,
                            trigger_map,
                            model,
                            movement_in_position_vars,
                            hop,
                        )


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
