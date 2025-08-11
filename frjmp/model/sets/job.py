from frjmp.model.sets.unit import Unit
from frjmp.model.sets.phase import Phase
from datetime import date


class Job:
    def __init__(
        self,
        unit: Unit,
        phase: Phase,
        start: date,
        end: date,
    ):
        if end < start:
            raise ValueError(
                f"Job for {unit} {phase} end date {end} cannot be before start date {start}."
            )

        self.unit = unit
        self.phase = phase
        self.start = start
        self.end = end

    def __repr__(self):
        return f"{self.unit.name}-{self.phase.name}"
