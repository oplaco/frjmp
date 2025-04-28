from frjmp.model.sets.position import Position
from typing import Dict, List


class MovementDependency:
    def __init__(
        self,
        positions: List[Position] = None,
        triggers: Dict[Position, Position] = None,
    ):
        self.positions = positions or []
        self.triggers = triggers or {}

    def add_position(self, position: Position):
        """Add a single Position object to available positions."""
        if all(p.name != position.name for p in self.positions):
            self.positions.append(position)

    def add_multiple_positions(self, positions: list[Position]):
        """Add a list of Position objects at once."""
        for pos in positions:
            self.add_position(pos)

    def add_trigger(self, from_position: Position, to_position: Position):
        """Declare that a movement in from_position triggers to_position."""
        self.triggers.setdefault(from_position.name, set()).add(to_position.name)

    def generate_matrix(self):
        """Return: matrix[i][j] = 1 if movement in i triggers movement in j, and name -> index mapping."""
        index_map = {pos.name: idx for idx, pos in enumerate(self.positions)}
        size = len(self.positions)
        matrix = [[0] * size for _ in range(size)]
        for from_name, to_names in self.triggers.items():
            i = index_map[from_name]
            for to_name in to_names:
                j = index_map[to_name]
                matrix[i][j] = 1

        return matrix, index_map
