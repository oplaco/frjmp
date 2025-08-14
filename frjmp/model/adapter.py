from typing import Protocol, Any
from datetime import date, timedelta, datetime


class TimeAdapter(Protocol):
    def to_tick(self, value: Any) -> int: ...
    def from_tick(self, tick: int) -> Any: ...


class DailyAdapter:
    def __init__(self, origin: date):
        self.origin = origin

    def to_tick(self, d: date) -> int:
        return (d - self.origin).days

    def from_tick(self, tick: int) -> date:
        return self.origin + timedelta(days=tick)


class ShiftAdapter:
    def __init__(self, origin: date, shifts: list[str]):
        self.origin = origin
        self.shifts = shifts
        self.per_day = len(shifts)

    def to_tick(self, v: tuple[date, str]) -> int:
        d, s = v
        day_ticks = (d - self.origin).days * self.per_day
        return day_ticks + self.shifts.index(s)

    def from_tick(self, tick: int) -> tuple[date, str]:
        day = tick // self.per_day
        s_idx = tick % self.per_day
        return (self.origin + timedelta(days=day), self.shifts[s_idx])


class MinuteStepAdapter:
    def __init__(self, origin: datetime, step_minutes: int):
        self.origin = origin
        self.step = step_minutes

    def to_tick(self, dt: datetime) -> int:
        delta = dt - self.origin
        return int(delta.total_seconds() // (self.step * 60))

    def from_tick(self, tick: int) -> datetime:
        return self.origin + timedelta(minutes=tick * self.step)


class WeeklyAdapter(DailyAdapter):
    def to_tick(self, d: date) -> int:
        return super().to_tick(d) // 7

    def from_tick(self, tick: int) -> date:
        return self.origin + timedelta(days=7 * tick)
