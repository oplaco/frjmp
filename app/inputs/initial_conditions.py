import pandas as pd
from datetime import date
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.sets.aircraft import Aircraft


class InitialConditions:
    # Excel sheet names
    POSITIONING_SHEET = "POSITIONING"
    REQUIRED_SHEETS = {POSITIONING_SHEET}

    # Excel columns titles
    AIRCRAFT_NAME_COL = "MSN"
    INITIAL_POSITION_COL = "POSITION"

    def __init__(
        self,
        filepath: str,
        t0: date,
        positions: list[Position],
        aircrafts: list[Aircraft],
        jobs: list[Job],
    ):
        self.filepath = filepath
        self.t0 = t0
        self.positions = positions
        self.aircrafts = aircrafts
        self.jobs = jobs
        self.initial_conditions = {}

        self.load()

    def load(self):
        xls = pd.ExcelFile(self.filepath)
        missing = self.REQUIRED_SHEETS - set(xls.sheet_names)
        if missing:
            raise ValueError(f"Missing required sheets: {', '.join(missing)}")

        df_industrial_phase = xls.parse(
            self.POSITIONING_SHEET, dtype={self.AIRCRAFT_NAME_COL: str}
        )

        self._parse_initial_conditions(df_industrial_phase)

    def _parse_initial_conditions(self, df):
        assignments_initial_conditions = {}
        name_to_position = {p.name: p for p in self.positions}

        for _, row in df.iterrows():
            position_name = str(row[self.INITIAL_POSITION_COL]).strip()
            msn = str(row[self.AIRCRAFT_NAME_COL]).strip()

            if not msn or msn.lower() == "nan":
                continue  # No aircraft assigned to this position

            if msn not in self.aircrafts:
                raise ValueError(f"Aircraft {msn} not found in known aircrafts.")

            if position_name not in name_to_position:
                raise ValueError(f"Unknown position '{position_name}'.")

            pos = name_to_position[position_name]
            aircraft = self.aircrafts[msn]

            # Get the job active at t0
            active_job = None
            for job in self.jobs:
                if job.aircraft == aircraft and job.start <= self.t0 <= job.end:
                    active_job = job
                    break

            if not active_job:
                raise ValueError(f"No active job at t0 {self.t0} for aircraft {msn}.")

            required_need = active_job.phase.required_need

            if required_need not in pos.available_needs:
                raise ValueError(
                    f"Position '{position_name}' cannot fulfill required need '{required_need.name}' "
                    f"for aircraft {msn} at t0."
                )

            if aircraft not in assignments_initial_conditions:
                assignments_initial_conditions[aircraft] = []

            assignments_initial_conditions[aircraft].append(pos)

        self.initial_conditions = {"assignments": assignments_initial_conditions}
