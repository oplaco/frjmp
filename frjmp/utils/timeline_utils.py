from datetime import date
from typing import List, Dict, Any

from frjmp.model.sets.job import Job


def compress_dates(jobs: List[Job], individual_dates: list[date] = None):
    """
    Compresses the scheduling timeline by extracting and indexing only the relevant dates
    across all jobs in the problem.

    In real-world planning problems like FRJMP, the planning window can span hundreds
    of days (e.g., 300–500), but only a small subset of those days are actually relevant
    for decision-making — specifically, the days on which jobs start or end.

    This function scans all jobs and collects the unique set of dates where a change
    in state can occur — that is, dates when an unit begins or finishes a phase.
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
        individual_dates (List[Job]): The list of additional dates that want to be added as time steps.

    Returns:
        Tuple:
            - List[date]: Sorted list of unique compressed dates.
            - Dict[date, int]: Mapping from real date → compressed time index.
            - Dict[int, date]: Mapping from compressed time index → real date.
    """

    unique_dates = set()

    if individual_dates:
        for date in individual_dates:
            unique_dates.add(date)

    for job in jobs:
        unique_dates.add(job.start)
        unique_dates.add(job.end)

    compressed = sorted(unique_dates)
    date_to_index = {d: i for i, d in enumerate(compressed)}
    index_to_date = {i: d for i, d in enumerate(compressed)}

    return compressed, date_to_index, index_to_date


from typing import List, Dict


def get_active_time_indices(
    job: "Job",
    compressed_ticks: List[int],
    tick_to_index: Dict[int, int],
    adapter: "TimeAdapter",
) -> List[int]:
    """
    Given a Job object, a list of compressed ticks, and a tick_to_index mapping,
    return the list of compressed time indices (integers) for which the job is active.

    A **tick** is the smallest discrete time unit in the problem (as defined by
    the TimeAdapter) — e.g., 1 day, 1 shift, 10 minutes, etc.

    This function:
        - Converts the job's start and end values into ticks.
        - Selects only compressed ticks between [start_tick, end_tick] (inclusive).
        - Maps them to their corresponding compressed indices.

    Example:
        Suppose:
            origin = 2025-04-15
            TimeAdapter: DailyAdapter(origin)
            Job:
                start = 2025-04-15   # tick 0
                end   = 2025-04-18   # tick 3

            compressed_ticks = [0, 1, 3, 5]
            tick_to_index = {0: 0, 1: 1, 3: 2, 5: 3}

        Then:
            start_tick = 0
            end_tick   = 3
            Active compressed ticks = [0, 1, 3]
            Mapped to indices       = [0, 1, 2]

        Output:
            [0, 1, 2]

    Args:
        job (Job): The job with start and end in adapter-native values.
        compressed_ticks (List[int]): All compressed ticks in ascending order.
        tick_to_index (Dict[int, int]): Mapping from tick → compressed index.
        adapter (TimeAdapter): Used to convert job start/end to ticks.

    Returns:
        List[int]: List of compressed time indices the job is active in.
    """
    start_tick = adapter.to_tick(job.start)
    end_tick = adapter.to_tick(job.end)

    return [tick_to_index[t] for t in compressed_ticks if start_tick <= t <= end_tick]


def trim_jobs_before_time_inplace(
    jobs: List["Job"], start_value: Any, adapter: "TimeAdapter"
) -> None:
    """
    Modifies the given list of jobs in-place:
    - Removes jobs that end before start_value
    - Adjusts start of jobs that overlap start_value

    Args:
        jobs: List of Job objects (modified in place).
        start_value: Start of planning horizon (type depends on adapter).
        adapter: TimeAdapter to convert between time values and ticks.
    """
    start_tick = adapter.to_tick(start_value)
    valid_jobs = []

    for job in jobs:
        job_end_tick = adapter.to_tick(job.end)
        job_start_tick = adapter.to_tick(job.start)

        if job_end_tick < start_tick:
            continue  # Drop entirely

        if job_start_tick < start_tick <= job_end_tick:
            job.start = adapter.from_tick(start_tick)  # Trim start

        valid_jobs.append(job)

    jobs.clear()
    jobs.extend(valid_jobs)


def trim_jobs_after_time_inplace(
    jobs: List["Job"],
    end_value: Any,
    adapter: "TimeAdapter",
) -> None:
    """
    Modifies the given list of jobs in-place:
    - Removes jobs that start after end_value
    - Adjusts end of jobs that overlap end_value

    Args:
        jobs: List[Job] (modified in place).
        end_value: End of planning horizon (adapter-native type).
        adapter: TimeAdapter to convert between values and ticks.
    """
    end_tick = adapter.to_tick(end_value)
    valid_jobs: List["Job"] = []

    for job in jobs:
        start_tick = adapter.to_tick(job.start)
        end_tick_job = adapter.to_tick(job.end)

        if start_tick > end_tick:
            continue  # drop entirely

        if start_tick <= end_tick < end_tick_job:
            job.end = adapter.from_tick(end_tick)  # trim end

        valid_jobs.append(job)

    jobs.clear()
    jobs.extend(valid_jobs)


from typing import List, Any, Tuple, Dict
from frjmp.model.adapter import TimeAdapter


def compress_timepoints(
    jobs: List["Job"],
    adapter: TimeAdapter,
    individual_points: list[Any] | None = None,
) -> Tuple[list[int], Dict[int, int], Dict[int, int], Dict[int, Any]]:
    """
    Returns:
      compressed_ticks: sorted unique ticks
      tick_to_index: tick -> compressed index
      index_to_tick: compressed index -> tick
      index_to_value: compressed index -> original time value (for nice reporting)
    """
    unique_ticks = set()
    if individual_points:
        for v in individual_points:
            unique_ticks.add(adapter.to_tick(v))

    for job in jobs:
        unique_ticks.add(adapter.to_tick(job.start))
        unique_ticks.add(adapter.to_tick(job.end))

    compressed_ticks = sorted(unique_ticks)
    tick_to_index = {t: i for i, t in enumerate(compressed_ticks)}
    index_to_tick = {i: t for i, t in enumerate(compressed_ticks)}
    index_to_value = {i: adapter.from_tick(t) for i, t in index_to_tick.items()}
    return compressed_ticks, tick_to_index, index_to_tick, index_to_value
