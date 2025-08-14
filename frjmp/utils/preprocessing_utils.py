from collections import defaultdict
from datetime import timedelta
from frjmp.model.sets.job import Job
from typing import List

"""
This file contains functions that do not necessarily belong to the problem itself. 
The problem can be solved witouth them. These functions are related with prepocessing data.
"""


from collections import defaultdict
from frjmp.model.adapter import TimeAdapter
from typing import List


def insert_waiting_jobs(
    jobs: List["Job"],
    phase_waiting: "Phase",
    adapter: "TimeAdapter",
) -> List["Job"]:
    """
    Insert artificial 'waiting' jobs between real jobs of the same unit when there is
    a gap of more than one *tick* (adapter step) between them.

    The adapter defines what a tick is (day, shift, N minutes, week, ...).
    """
    jobs_by_unit: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        jobs_by_unit[job.unit.name].append(job)

    new_jobs = list(jobs)

    for unit_name, unit_jobs in jobs_by_unit.items():
        # Sort by start tick according to the adapter
        sorted_jobs = sorted(unit_jobs, key=lambda j: adapter.to_tick(j.start))

        for i in range(len(sorted_jobs) - 1):
            current = sorted_jobs[i]
            next_job = sorted_jobs[i + 1]

            cur_end_tick = adapter.to_tick(current.end)
            next_start_tick = adapter.to_tick(next_job.start)

            expected_next_tick = cur_end_tick + 1
            if next_start_tick > expected_next_tick:
                waiting_job = Job(
                    unit=current.unit,
                    phase=phase_waiting,
                    start=adapter.from_tick(expected_next_tick),
                    end=adapter.from_tick(next_start_tick - 1),
                )
                new_jobs.append(waiting_job)

    return new_jobs
