from frjmp.model.sets.position import Position
from typing import Dict, List


class PositionsConfiguration:
    def __init__(
        self,
        positions: List[Position],
        out_position: Position = Position("OUT", [], 0),
        triggers: dict[tuple[Position, Position], set[Position]] = None,
        out_paths: dict[tuple[Position, Position], list[Position]] = None,
        in_paths: dict[tuple[Position, Position], list[Position]] = None,
    ):
        self.positions = positions
        self.out_position = out_position
        self.triggers = triggers or {}
        self.out_paths = out_paths or {}
        self.in_paths = in_paths or {}

        self.index_map = {pos.name: idx for idx, pos in enumerate(self.positions)}

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
        index_map = self.index_map
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

    def generate_paths_matrix(self):
        """
        Generates two 2D matrices representing the involved positions in out-paths and in-paths
        for each (from_position, to_position) pair.

        Returns:
            - out_paths_matrix[i][j]: list of indices (k) such that position k is involved
            in the out-path from position i to position j.
            - in_paths_matrix[i][j]: list of indices (k) such that position k is involved
            in the in-path from position i to position j.
        """
        index_map = self.index_map
        size = len(self.positions)
        out_paths_matrix = [[[] for _ in range(size)] for _ in range(size)]
        in_paths_matrix = [[[] for _ in range(size)] for _ in range(size)]

        for (from_pos, to_pos), involved_positions in self.out_paths.items():
            i = index_map[from_pos.name]
            j = index_map[to_pos.name]
            out_paths_matrix[i][j] = [index_map[pos.name] for pos in involved_positions]

        for (from_pos, to_pos), involved_positions in self.in_paths.items():
            i = index_map[from_pos.name]
            j = index_map[to_pos.name]
            in_paths_matrix[i][j] = [index_map[pos.name] for pos in involved_positions]

        return out_paths_matrix, in_paths_matrix
