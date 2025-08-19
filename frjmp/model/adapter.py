from typing import Protocol, Any
from datetime import date, timedelta, datetime


class TimeAdapter(Protocol):
    def to_tick(self, value: Any) -> int: ...
    def from_tick(self, tick: int) -> Any: ...


class DailyAdapter:
    time_value_type = date

    def __init__(self, origin: date):
        self.origin = origin

    def to_tick(self, d: date) -> int:
        return (d - self.origin).days

    def from_tick(self, tick: int) -> date:
        return self.origin + timedelta(days=tick)


class ShiftAdapter:
    time_value_type = (date, str)

    def __init__(self, origin: tuple[date, str], shifts: list[str]):
        if not all(isinstance(s, str) for s in shifts):
            raise TypeError(f"All shifts must be strings. Got: {shifts}")
        self.origin = origin
        self.origin_date, self.origin_shift = origin
        self.shifts = shifts
        self.per_day = len(shifts)
        self.origin_shift_index = self.shifts.index(self.origin_shift)

    def to_tick(self, v: tuple[date, str]) -> int:
        d, s = v
        day_offset = (d - self.origin_date).days
        try:
            shift_offset = self.shifts.index(s) - self.origin_shift_index
        except ValueError:
            raise ValueError(
                f"Invalid shift label '{s}' for date {d}. "
                f"Expected one of: {self.shifts}"
            )
        return day_offset * self.per_day + shift_offset

    def from_tick(self, tick: int) -> tuple[date, str]:
        total_shift_index = self.origin_shift_index + tick
        day = total_shift_index // self.per_day
        s_idx = total_shift_index % self.per_day
        return (self.origin_date + timedelta(days=day), self.shifts[s_idx])


class MinuteStepAdapter:
    time_value_type = datetime

    def __init__(self, origin: datetime, step_minutes: int):
        self.origin = origin
        self.step = step_minutes

    def to_tick(self, dt: datetime) -> int:
        delta = dt - self.origin
        return int(delta.total_seconds() // (self.step * 60))

    def from_tick(self, tick: int) -> datetime:
        return self.origin + timedelta(minutes=tick * self.step)


class WeeklyAdapter(DailyAdapter):
    time_value_type = int

    def to_tick(self, d: date) -> int:
        return super().to_tick(d) // 7

    def from_tick(self, tick: int) -> date:
        return self.origin + timedelta(days=7 * tick)
