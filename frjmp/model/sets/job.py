from frjmp.model.sets.aircraft import Aircraft
from frjmp.model.sets.phase import Phase
from datetime import date


class Job:
    def __init__(self, aircraft: Aircraft, phase: Phase, start: date, end: date):
        if end < start:
            raise ValueError(
                f"Job for {aircraft} {phase} end date {end} cannot be before start date {start}."
            )

        self.aircraft = aircraft
        self.phase = phase
        self.start = start
        self.end = end

    def __repr__(self):
        return f"{self.aircraft.name}-{self.phase.name}"

    # def __repr__(self):
    #     return (
    #         f"Job(aircraft={self.aircraft.name}, "
    #         f"phase={self.phase.name}, "
    #         f"start={self.start}, end={self.end})"
    #     )
