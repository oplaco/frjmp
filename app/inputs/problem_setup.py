import pandas as pd
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.parameters.position_aircraft_model import (
    Pattern,
    PositionsAircraftModelDependency,
)
from frjmp.model.sets.need import Need
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.sets.aircraft import AircraftModel


class ProblemSetup:
    # Excel sheet names
    PHASE_NEED_LINK_SHEET = "PHASE_NEED_LINK"
    POSITION_SHEET = "POSITION"
    MOVEMENT_DEPENDENCY_SHEET = "MOVEMENT_DEPENDENCY"
    AIRCRAFT_MODEL_SHEET = "AIRCRAFT_MODEL"
    REQUIRED_SHEETS = {PHASE_NEED_LINK_SHEET, POSITION_SHEET, MOVEMENT_DEPENDENCY_SHEET}

    # Excel columns titles
    NEED_COL = "NEED"
    PHASE_COL = "PHASE"
    MODEL_COL = "MODEL"
    PATTERN_COL = "PATTERN"

    # Default waiting need name.
    WAITING_NEED = "WAITING"

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.positions = []
        self.needs = []
        self.phases = []
        self.triggers = {}
        self.load()

    def load(self):
        xls = pd.ExcelFile(self.filepath)
        missing = self.REQUIRED_SHEETS - set(xls.sheet_names)
        if missing:
            raise ValueError(f"Missing required sheets: {', '.join(missing)}")

        df_phase_need_link = xls.parse(self.PHASE_NEED_LINK_SHEET)
        df_position = xls.parse(self.POSITION_SHEET)
        df_movement_depedency = xls.parse(self.MOVEMENT_DEPENDENCY_SHEET, index_col=0)
        df_aircraft_model = xls.parse(self.AIRCRAFT_MODEL_SHEET)

        self._parse_needs(df_phase_need_link)
        self._parse_phases(df_phase_need_link)
        self._parse_positions(df_position)
        self._parse_movement_dependency(df_movement_depedency)
        self._parse_aircraft_models(df_aircraft_model)
        self.positions_configuration = PositionsConfiguration(
            self.positions, self.triggers
        )
        self.position_aircraftmodel_dependency = PositionsAircraftModelDependency(
            self.aircraft_models_list, self.positions
        )

    def _parse_needs(self, df):
        # Replace N/A (now nan) needs to our default waiting need
        serie = df[self.NEED_COL].fillna(self.WAITING_NEED)

        need_names = serie.dropna().unique()
        self.needs = [Need(name) for name in need_names]

    def _parse_phases(self, df):
        need_map = {need.name: need for need in self.needs}
        # Default waiting phase with waiting need.
        self.waiting_phase = Phase("WAITING", need_map[self.WAITING_NEED])
        self.phases.append(self.waiting_phase)

        # User-defined phases.
        for _, row in df.iterrows():
            phase_name = row[self.PHASE_COL]
            need_name = row[self.NEED_COL]
            df[self.NEED_COL].fillna(self.WAITING_NEED)

            if pd.isna(need_name):
                need_name = self.WAITING_NEED
                # raise ValueError(f"Missing need for phase '{phase_name}'")

            if need_name not in need_map:
                raise ValueError(f"Unknown need '{need_name}' for phase '{phase_name}'")

            need = need_map[need_name]
            self.phases.append(Phase(phase_name, need))

    def _parse_positions(self, df):
        if df.empty:
            raise ValueError("No positions defined in the sheet.")

        # Get all column names that represent needs (skip first two: 'Position', 'Capacity')
        need_columns = df.columns[2:]
        known_need_names = {need.name for need in self.needs}

        if set(need_columns) != known_need_names:
            missing = known_need_names - set(need_columns)
            extra = set(need_columns) - known_need_names
            msg = []
            if missing:
                msg.append(f"Missing need columns: {', '.join(sorted(missing))}")
            if extra:
                msg.append(
                    f"Unknown columns not matching any need: {', '.join(sorted(extra))}"
                )
            raise ValueError("Invalid need columns in position sheet. " + " ".join(msg))

        need_map = {need.name: need for need in self.needs}
        self.positions = []

        for _, row in df.iterrows():
            name = row["Position"]
            capacity = int(row["Capacity"])

            covered_needs = [
                need_map[need_name]
                for need_name in need_columns
                if int(row[need_name]) == 1
            ]

            self.positions.append(Position(name, covered_needs, capacity))

    def _parse_movement_dependency(self, df):
        if (
            df.empty
            or df.shape[0] != len(self.positions)
            or df.shape[1] != len(self.positions)
        ):
            raise ValueError(
                "Movement dependency matrix must be square and match number of positions."
            )

        name_to_position = {p.name: p for p in self.positions}
        matrix_rows = df.index.tolist()
        matrix_cols = df.columns.tolist()

        if set(matrix_rows) != set(matrix_cols) or set(matrix_rows) != set(
            name_to_position.keys()
        ):
            raise ValueError("Row/column names must match position names exactly.")

        for from_name in matrix_rows:
            from_pos = name_to_position[from_name]
            for to_name in matrix_cols:
                if int(df.loc[from_name, to_name]) == 1:
                    to_pos = name_to_position[to_name]
                    self.triggers.setdefault(from_pos, set()).add(to_pos)

    def _parse_aircraft_models(self, df) -> list[AircraftModel]:
        name_to_position = {p.name: p for p in self.positions}
        models = {}

        for _, row in df.iterrows():
            model_name = str(row[self.MODEL_COL]).strip()
            pattern_str = str(row[self.PATTERN_COL]).strip()

            model = AircraftModel(model_name)

            if pattern_str.lower() == "nan" or not pattern_str:
                models[model_name] = model
                continue  # No patterns defined

            # Cada patrón separado por ";"
            pattern_groups = pattern_str.split(";")
            for group in pattern_groups:
                position_names = [p.strip() for p in group.split(",") if p.strip()]
                pattern_positions = []

                for pname in position_names:
                    if pname not in name_to_position:
                        raise ValueError(
                            f"Position '{pname}' not found in known positions."
                        )
                    pattern_positions.append(name_to_position[pname])

                pattern = Pattern(pattern_positions)
                model.allowed_patterns.append(pattern)

            models[model_name] = model

        self.aircraft_models_dict = models
        self.aircraft_models_list = list(models.values())
