from collections import defaultdict
from datetime import date
from typing import List, Dict, Tuple
from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position


def validate_capacity_feasibility(
    jobs: List[Job],
    positions: List[Position],
    compressed_dates: List[date],
    date_to_index: Dict[date, int],
) -> Dict[int, Dict[str, Tuple[int, int]]]:
    """
    Validates that for each compressed time step, the demand per need is within
    the capacity provided by positions that cover that need, AND that overall
    capacity is enough to handle total demand.

    Returns a summary per timestep.

    Raises:
        ValueError: If at any timestep, any need has more demand than available capacity,
                    or total demand exceeds total capacity.
    """
    summary = {}

    for d in compressed_dates:
        t_idx = date_to_index[d]

        # Count job demand per need
        need_demand = defaultdict(int)
        for job in jobs:
            if job.start <= d <= job.end:
                need_name = job.phase.required_need.name
                need_demand[need_name] += 1

        # Total demand (sum of all active jobs)
        total_demand = sum(need_demand.values())

        # Total capacity
        total_capacity = sum(pos.capacity for pos in positions)

        # Per-need capacity (only from positions that serve that need)
        per_need_capacity = defaultdict(int)
        for pos in positions:
            for need in pos.available_needs:
                per_need_capacity[need.name] += pos.capacity

        # Check each need independently
        for need, demand in need_demand.items():
            available = per_need_capacity.get(need, 0)
            if demand > available:
                raise ValueError(
                    f"On {d}, need '{need}' has demand {demand} "
                    f"but only {available} capacity is available from positions that support it."
                )

        # Optional overall system check
        if total_demand > total_capacity:
            raise ValueError(
                f"On {d}, total job demand is {total_demand}, but total system capacity is {total_capacity}."
            )

        # Build summary
        summary[t_idx] = {
            "total_capacity": total_capacity,
            "total_demand": total_demand,
            "per_need": {
                need: (per_need_capacity[need], need_demand[need])
                for need in need_demand
            },
        }

    return summary


def validate_non_overlapping_jobs_per_aircraft(jobs: List[Job]):
    """
    Validates that no aircraft has overlapping jobs in time (inclusive).

    Raises:
        ValueError: If any aircraft has two jobs that overlap.
    """
    aircraft_jobs = defaultdict(list)

    for job in jobs:
        aircraft_jobs[job.aircraft.name].append(job)

    for aircraft_name, job_list in aircraft_jobs.items():
        sorted_jobs = sorted(job_list, key=lambda j: j.start)
        for i in range(1, len(sorted_jobs)):
            prev = sorted_jobs[i - 1]
            curr = sorted_jobs[i]
            if curr.start <= prev.end:
                raise ValueError(
                    f"Aircraft '{aircraft_name}' has overlapping jobs: "
                    f"{prev.start}–{prev.end} and {curr.start}–{curr.end}"
                )
