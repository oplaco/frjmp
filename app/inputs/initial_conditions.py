import pandas as pd
from datetime import date, datetime, timedelta
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.sets.aircraft import Aircraft


class InitialConditions:
    # Excel sheet names
    POSITIONING_SHEET = "POSITIONING"
    CONFIGURATION_SHEET = "CONFIGURATION"
    REQUIRED_SHEETS = {POSITIONING_SHEET, CONFIGURATION_SHEET}

    # Excel columns titles
    AIRCRAFT_NAME_COL = "MSN"
    INITIAL_POSITION_COL = "POSITION"

    # Excel variable row names
    T0_NAME = "T0_DATE"
    T_LAST_NAME = "END_DATE"

    def __init__(
        self,
        filepath: str,
        positions: list[Position],
        aircrafts: list[Aircraft],
        jobs: list[Job],
    ):
        self.filepath = filepath
        self.positions = positions
        self.aircrafts = aircrafts
        self.jobs = jobs

        self.t0 = None
        self.t_last = None
        self.initial_conditions = {}

        self.load()

    def load(self):
        xls = pd.ExcelFile(self.filepath)
        missing = self.REQUIRED_SHEETS - set(xls.sheet_names)
        if missing:
            raise ValueError(f"Missing required sheets: {', '.join(missing)}")

        df_initial_configuration = xls.parse(
            self.CONFIGURATION_SHEET, dtype={self.AIRCRAFT_NAME_COL: str}
        )

        df_initial_positioning = xls.parse(
            self.POSITIONING_SHEET, dtype={self.AIRCRAFT_NAME_COL: str}
        )

        self._parse_initial_configuration(df_initial_configuration)
        self._parse_initial_conditions(df_initial_positioning)

    def _parse_initial_configuration(self, df):
        def parse_value(var_name, val):
            if pd.isna(val) or str(val).strip().lower() in ["", "none"]:
                return None

            val = str(val).strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
                try:
                    return datetime.strptime(val, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Invalid date format for {var_name}: {val}")

        date_vars = {
            str(row["VARIABLE"]).strip(): parse_value(
                str(row["VARIABLE"]).strip(), row["VALUE"]
            )
            for _, row in df.iterrows()
        }

        self.t0 = date_vars.get("T0_DATE") or date.today()
        self.t_last = date_vars.get("END_DATE") or (self.t0 + timedelta(days=365))

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
