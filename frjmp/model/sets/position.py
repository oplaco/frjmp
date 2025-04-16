from frjmp.model.sets.need import Need


class Position:
    def __init__(self, name: str, needs: list[Need], capacity: int = 1):
        if capacity <= 0:
            raise ValueError(
                f"Position {name} must have positive capacity (got {capacity})"
            )
        self.name = name
        self.available_needs = needs
        self.capacity = capacity

    def __repr__(self):
        return f"Position {self.name}"
