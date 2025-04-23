from collections import defaultdict
from datetime import timedelta
from frjmp.model.sets.job import Job
from typing import List

"""
This file contains functions that do not necessarily belong to the problem itself. 
The problem can be solved witouth them. These functions are related with prepocessing data.
"""


def insert_waiting_jobs(jobs: List[Job], phase_waiting) -> List[Job]:
    """
    Inserts artificial waiting jobs between real jobs of the same aircraft
    when there is a gap greater than one day between them.

    Args:
        jobs: list of Job objects
        phase_waiting: special Phase object representing idle time

    Returns:
        List of original + artificial jobs
    """
    jobs_by_aircraft = defaultdict(list)
    for job in jobs:
        jobs_by_aircraft[job.aircraft.name].append(job)

    new_jobs = list(jobs)

    for aircraft_name, aircraft_jobs in jobs_by_aircraft.items():
        sorted_jobs = sorted(aircraft_jobs, key=lambda j: j.start)
        for i in range(len(sorted_jobs) - 1):
            current = sorted_jobs[i]
            next_job = sorted_jobs[i + 1]
            expected_next_day = current.end + timedelta(days=1)
            if next_job.start > expected_next_day:
                waiting_job = Job(
                    aircraft=current.aircraft,
                    phase=phase_waiting,
                    start=expected_next_day,
                    end=next_job.start - timedelta(days=1),
                )
                new_jobs.append(waiting_job)

    return new_jobs
