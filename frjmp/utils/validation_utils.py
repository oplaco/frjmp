from collections import defaultdict
from datetime import date
from typing import List, Dict, Tuple, Any

from frjmp.model.adapter import TimeAdapter
from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position


def validate_capacity_feasibility(
    jobs: List["Job"],
    positions: List["Position"],
    compressed_ticks: List[int],
    tick_to_index: Dict[int, int],
    adapter: TimeAdapter,
    index_to_value: Dict[int, Any],
) -> Dict[int, Dict[str, Tuple[int, int]]]:
    """
    Validates that for each compressed tick, the demand per need is within
    the capacity provided by positions that cover that need, AND that overall
    capacity is enough to handle total demand.

    Returns:
        Dict[t_idx] = {
            total_capacity: int,
            total_demand: int,
            per_need: Dict[need_name] = (capacity, demand)
        }

    Raises:
        ValueError: If at any tick, any need has more demand than capacity.
    """
    summary = {}

    for tick in compressed_ticks:
        t_idx = tick_to_index[tick]
        d = index_to_value[t_idx]

        # Count job demand per need
        need_demand = defaultdict(int)
        for job in jobs:
            start_tick = adapter.to_tick(job.start)
            end_tick = adapter.to_tick(job.end)
            if start_tick <= tick <= end_tick:
                need_name = job.phase.required_need.name
                need_demand[need_name] += 1

        total_demand = sum(need_demand.values())
        total_capacity = sum(pos.capacity for pos in positions)

        # Per-need capacity
        per_need_capacity = defaultdict(int)
        for pos in positions:
            for need in pos.available_needs:
                per_need_capacity[need.name] += pos.capacity

        # Per-need checks
        for need, demand in need_demand.items():
            available = per_need_capacity.get(need, 0)
            if demand > available:
                raise ValueError(
                    f"At {d}, need '{need}' has demand {demand} "
                    f"but only {available} capacity is available."
                )

        # Global check
        if total_demand > total_capacity:
            raise ValueError(
                f"At {d}, total job demand is {total_demand}, "
                f"but system capacity is {total_capacity}."
            )

        # Summary output
        summary[t_idx] = {
            "total_capacity": total_capacity,
            "total_demand": total_demand,
            "per_need": {
                need: (per_need_capacity[need], need_demand[need])
                for need in need_demand
            },
        }

    return summary


def validate_non_overlapping_jobs_per_unit(jobs: List["Job"], adapter: TimeAdapter):
    """
    Validates that no unit has overlapping jobs in time (inclusive),
    based on tick comparisons using the provided adapter.

    Raises:
        ValueError: If any unit has two overlapping jobs.
    """
    unit_jobs = defaultdict(list)

    for job in jobs:
        unit_jobs[job.unit.name].append(job)

    for unit_name, job_list in unit_jobs.items():
        # Sort using tick value of job.start
        sorted_jobs = sorted(job_list, key=lambda j: adapter.to_tick(j.start))

        for i in range(1, len(sorted_jobs)):
            prev = sorted_jobs[i - 1]
            curr = sorted_jobs[i]

            prev_end_tick = adapter.to_tick(prev.end)
            curr_start_tick = adapter.to_tick(curr.start)

            if curr_start_tick <= prev_end_tick:
                raise ValueError(
                    f"Unit '{unit_name}' has overlapping jobs: "
                    f"{prev.start}–{prev.end} and {curr.start}–{curr.end}"
                )
