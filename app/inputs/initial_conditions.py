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
    INITIAL_POSITIONS_COL = "POSITIONS"

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
        self.initial_assignments = {}

        self.load()

    def load(self):
        xls = pd.ExcelFile(self.filepath)
        missing = self.REQUIRED_SHEETS - set(xls.sheet_names)
        if missing:
            raise ValueError(f"Missing required sheets: {', '.join(missing)}")

        df_industrial_phase = xls.parse(self.POSITIONING_SHEET)

        self._parse_initial_conditions(df_industrial_phase)

    def _parse_initial_conditions(self, df):
        assigned_aircrafts = set()
        name_to_position = {p.name: p for p in self.positions}

        for _, row in df.iterrows():
            msn = str(row["MSN"]).strip()
            if msn in assigned_aircrafts:
                raise ValueError(f"Aircraft {msn} is assigned multiple times at t0.")

            assigned_aircrafts.add(msn)

            if msn not in self.aircrafts:
                raise ValueError(f"Aircraft {msn} not found in known aircrafts.")

            aircraft = self.aircrafts[msn]

            # Get the job active at t0
            active_job = None
            for job in self.jobs:
                if job.aircraft.name == msn and job.start <= self.t0 <= job.end:
                    active_job = job
                    break

            if not active_job:
                raise ValueError(f"No active job at t0 {self.t0} for aircraft {msn}.")

            required_need = active_job.phase.required_need

            # Get positions from string (semicolon-separated)
            position_names = [p.strip() for p in str(row["POSITIONS"]).split(";")]
            local_positions = []

            for pname in position_names:
                if pname not in name_to_position:
                    raise ValueError(f"Unknown position '{pname}' for aircraft {msn}.")
                pos = name_to_position[pname]
                if required_need not in pos.available_needs:
                    raise ValueError(
                        f"Position '{pname}' cannot fulfill required need '{required_need.name}' "
                        f"for aircraft {msn} at t0."
                    )
                local_positions.append(pos)

            self.initial_assignments[aircraft] = local_positions
