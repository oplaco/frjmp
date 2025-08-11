from frjmp.model.parameters.position_unit_model import Pattern
from frjmp.model.sets.position import Position


class UnitType:
    def __init__(self, name: str):
        self.name = name
        self.allowed_patterns: list[Pattern] = []

    def add_pattern(self, pattern: Pattern) -> None:
        self.allowed_patterns.append(pattern)

    def add_multiple_patterns(self, patterns: list[Pattern]) -> None:
        self.allowed_patterns.extend(patterns)

    def add_default_single_patterns(self, available_positions: list[Position]) -> None:
        if not self.allowed_patterns:
            for pos in available_positions:
                self.allowed_patterns.append(Pattern([pos]))

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Unit:
    def __init__(self, name: str, type: UnitType):
        self.name = name
        self.type = type

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
