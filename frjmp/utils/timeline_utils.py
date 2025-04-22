from datetime import date
from typing import List, Dict

from frjmp.model.sets.job import Job


def compress_dates(jobs: List[Job]):
    """
    Compresses the scheduling timeline by extracting and indexing only the relevant dates
    across all jobs in the problem.

    In real-world planning problems like FRJMP, the planning window can span hundreds
    of days (e.g., 300–500), but only a small subset of those days are actually relevant
    for decision-making — specifically, the days on which jobs start or end.

    This function scans all jobs and collects the unique set of dates where a change
    in state can occur — that is, dates when an aircraft begins or finishes a phase.
    These are the only points in time where constraints or decisions may apply.

    By compressing the full timeline down to just these active dates, we dramatically reduce
    the number of time steps the solver needs to consider. This makes the optimization problem
    far more scalable and efficient without losing any relevant information.

    For example:
        Jobs:
            Job A: start = 2025-04-15, end = 2025-04-18
            Job B: start = 2025-04-16, end = 2025-04-20

        Full timeline: [2025-04-15 ... 2025-04-20] → 6 days
        Compressed: [2025-04-15, 2025-04-16, 2025-04-18, 2025-04-20] → 4 steps

        Output:
            compressed_dates = [date1, date2, ...]
            date_to_index = {date1: 0, date2: 1, ...}
            index_to_date = {0: date1, 1: date2, ...}

    These outputs are then used throughout the model to:
        - Define variables over compressed time steps
        - Build constraints and movement logic
        - Translate model solutions back into real dates for interpretation

    Args:
        jobs (List[Job]): The list of jobs, each with a start and end date.

    Returns:
        Tuple:
            - List[date]: Sorted list of unique compressed dates.
            - Dict[date, int]: Mapping from real date → compressed time index.
            - Dict[int, date]: Mapping from compressed time index → real date.
    """

    unique_dates = set()

    for job in jobs:
        unique_dates.add(job.start)
        unique_dates.add(job.end)

    compressed = sorted(unique_dates)
    date_to_index = {d: i for i, d in enumerate(compressed)}
    index_to_date = {i: d for i, d in enumerate(compressed)}

    return compressed, date_to_index, index_to_date


def get_active_time_indices(
    job: Job, compressed_dates: List[date], date_to_index: Dict[date, int]
) -> List[int]:
    """
    Given a Job object, a list of compressed dates, and a date_to_index mapping,
    return the list of compressed time indices (integers) for which the job is active.

    This function filters the compressed time steps to include only those
    that fall within the job's planned window [start, end], inclusive,
    and maps them to their corresponding compressed index.

    Example:
        Job:
            start = 2025-04-15
            end   = 2025-04-18

        compressed_dates = [
            date(2025, 4, 15),
            date(2025, 4, 16),
            date(2025, 4, 18),
            date(2025, 4, 20)
        ]

        date_to_index = {
            date(2025, 4, 15): 0,
            date(2025, 4, 16): 1,
            date(2025, 4, 18): 2,
            date(2025, 4, 20): 3
        }

        Output:
            [0, 1, 2]

    Args:
        job (Job): The job with start and end.
        compressed_dates (List[date]): List of all compressed dates.
        date_to_index (Dict[date, int]): Mapping of date → compressed index.

    Returns:
        List[int]: List of compressed time indices the job is active in.
    """
    return [date_to_index[d] for d in compressed_dates if job.start <= d <= job.end]


def trim_jobs_before_t0_inplace(jobs: List[Job], t0: date) -> None:
    """
    Modifies the given list of jobs in-place:
    - Removes jobs that end before t0
    - Adjusts start_date of jobs that overlap t0

    Args:
        jobs: List of Job objects (modified in place).
        t0: Start of planning horizon.
    """
    valid_job = []
    for job in jobs:
        if job.end < t0:
            continue  # Drop it
        if job.start < t0 <= job.end:
            job.start = t0  # Trim start date
        valid_job.append(job)

    jobs.clear()
    jobs.extend(valid_job)
