from frjmp.model.sets.position import Position
from typing import Dict, List


class PositionsConfiguration:
    def __init__(
        self,
        positions: List[Position] = None,
        triggers: dict[tuple[Position, Position], set[Position]] = None,
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

    def add_trigger(
        self,
        from_position: Position,
        to_position: Position,
        triggered_positions: set[Position],
    ):
        """Declare that a movement from 'from_position' to 'to_position' triggers a set of positions."""
        self.triggers[(from_position, to_position)] = triggered_positions

    def generate_matrix(self):
        """
        Returns:
            - matrix[i][j][k] = 1 if movement from i to j triggers movement in k
            - index_map: position name -> index
        """
        index_map = {pos.name: idx for idx, pos in enumerate(self.positions)}
        size = len(self.positions)
        matrix = [
            [[0] * size for _ in range(size)] for _ in range(size)
        ]  # 3D zero matrix

        for (from_pos, to_pos), triggered_positions in self.triggers.items():
            i = index_map[from_pos.name]
            j = index_map[to_pos.name]
            for trg_pos in triggered_positions:
                k = index_map[trg_pos.name]
                matrix[i][j][k] = 1

        return matrix, index_map
