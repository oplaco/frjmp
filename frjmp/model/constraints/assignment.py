from datetime import date
from ortools.sat.python import cp_model
from typing import List, Dict

from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position


def add_job_assignment_constraints(
    model: cp_model.CpModel,
    assigned_vars: Dict[int, Dict[int, Dict[int, cp_model.IntVar]]],
    jobs: List[Job],
    positions: List[Position],
    date_to_index: Dict[date, int],
    compressed_dates: List[date],
):
    """
    For each job, ensure that it is assigned_vars to one and only one compatible position
    for every time step between its start and end (inclusive) — only considering
    dates that actually exist in the compressed time steps.
    """
    for j_idx, job in enumerate(jobs):
        for t_date in compressed_dates:
            if job.start <= t_date <= job.end:
                t_idx = date_to_index[t_date]
                assign_vars = []

                for p_idx, position in enumerate(positions):
                    if (
                        p_idx in assigned_vars.get(j_idx, {})
                        and t_idx in assigned_vars[j_idx][p_idx]
                    ):
                        assign_vars.append(assigned_vars[j_idx][p_idx][t_idx])

                if assign_vars:
                    model.AddExactlyOne(assign_vars)
