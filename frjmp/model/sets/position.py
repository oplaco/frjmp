from frjmp.model.sets.need import Need


class Position:
    def __init__(self, name: str, needs: list[Need], capacity: int = 1):
        if capacity <= 0:
            raise ValueError(
                f"Position {name} must have capacity greater than 0 (got {capacity})"
            )
        self.name = name
        self.available_needs = needs
        self.capacity = capacity

    def __repr__(self):
        return f"Position {self.name}"
