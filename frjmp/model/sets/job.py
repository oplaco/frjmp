from frjmp.model.adapter import TimeAdapter
from frjmp.model.sets.unit import Unit
from frjmp.model.sets.phase import Phase
from typing import Any


class Job:
    def __init__(
        self,
        unit: Unit,
        phase: Phase,
        adapter: TimeAdapter,
        start: Any,
        end: Any,
    ):
        if start is None or end is None:
            raise ValueError("Job start and end must be defined.")

        adapter.validate_time_value_type(start)
        adapter.validate_time_value_type(end)

        if adapter.to_tick(end) < adapter.to_tick(start):
            raise ValueError(
                f"Job for {unit} at {phase} end time {end} cannot be before start time {start}."
            )

        self.unit = unit
        self.phase = phase
        self.start = start
        self.end = end

    def __repr__(self):
        return f"{self.unit.name}-{self.phase.name}"
