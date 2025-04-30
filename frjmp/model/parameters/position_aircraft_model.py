from frjmp.model.sets.position import Position


class Pattern:
    """Concrete footprint: the set of :class:`Position` objects occupied simultaneously by one:class:`Aircraft`.

    The class itself is agnostic to position capacity; whether several aircraft may share a
    position at the same time is controlled elsewhere (in Position.capacity).  `Pattern` merely
    records which positions this aircraft instance would use, not if that usage is exclusive.
    """

    def __init__(self, positions: list[Position]):
        if len(positions) != len(set(positions)):
            raise ValueError("All positions in a Pattern must be unique.")
        self.positions = positions


class PositionsAircraftModelDependency:
    """Collects every legal Pattern for each AircraftModel and builds a full model-pattern-position 3D matrix."""

    def __init__(
        self,
        aircraft_models: list["AircraftModel"],
        available_positions: list[Position],
    ):
        self.aircraft_models = aircraft_models
        self.available_positions = available_positions

    def generate_matrix(self):
        """Build 3D matrix: model_idx × pattern_idx × position_idx."""
        model_index = {model: idx for idx, model in enumerate(self.aircraft_models)}
        pos_index = {pos.name: idx for idx, pos in enumerate(self.available_positions)}

        full_matrix = []

        for model in self.aircraft_models:
            # Auto-generate default patterns if there is not at least ONE allowed pattern.
            if not model.allowed_patterns:
                model.add_default_single_patterns(self.available_positions)

            mat = []
            for pattern in model.allowed_patterns:
                row = [0] * len(self.available_positions)
                for pos in pattern.positions:
                    row[pos_index[pos.name]] = 1
                mat.append(row)

            full_matrix.append(mat)

        return full_matrix
