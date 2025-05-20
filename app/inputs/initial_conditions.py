import pandas as pd
from datetime import date, datetime, timedelta
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.sets.aircraft import Aircraft


class InitialConditions:
    # Excel sheet names
    CONFIGURATION_SHEET = "CONFIGURATION"
    POSITIONING_SHEET = "POSITIONING"
    UNPLANNED_JOB_SHEET = "JOB"
    REQUIRED_SHEETS = {CONFIGURATION_SHEET, POSITIONING_SHEET, UNPLANNED_JOB_SHEET}

    # Excel columns titles
    ## Initial assigment
    AIRCRAFT_NAME_COL = "MSN"
    INITIAL_POSITION_COL = "POSITION"
    ## Unplanned jobs
    JOB_AIRCRAFT_NAME_COL = "MSN"
    JOB_AIRCRAFT_MODEL_COL = "MODEL"
    JOB_PHASE_COL = "PHASE"
    JOB_START_COL = "START"
    JOB_END_COL = "END"
    JOB_PATTERN_COL = "PATTERN"

    # Excel variable row names
    T0_NAME = "T0_DATE"
    T_LAST_NAME = "END_DATE"

    def __init__(
        self,
        filepath: str,
        positions: list[Position],
        aircrafts: dict,
        jobs: list[Job],
        phases: list[Phase],
        aircraft_models: dict,
    ):
        self.filepath = filepath
        self.positions = positions
        self.aircrafts = aircrafts
        self.jobs = jobs
        self.phases = phases
        self.aircraft_models = aircraft_models

        self.t0 = None
        self.t_last = None
        self.initial_conditions = {}

        self.load()

    def load(self):
        xls = pd.ExcelFile(self.filepath)
        missing = self.REQUIRED_SHEETS - set(xls.sheet_names)
        if missing:
            raise ValueError(f"Missing required sheets: {', '.join(missing)}")

        df_initial_configuration = xls.parse(self.CONFIGURATION_SHEET)

        df_initial_positioning = xls.parse(
            self.POSITIONING_SHEET, dtype={self.AIRCRAFT_NAME_COL: str}
        )

        df_unplanned_jobs = xls.parse(
            self.UNPLANNED_JOB_SHEET,
            usecols=[
                self.JOB_AIRCRAFT_NAME_COL,
                self.JOB_AIRCRAFT_MODEL_COL,
                self.JOB_PHASE_COL,
                self.JOB_PATTERN_COL,
                self.JOB_START_COL,
                self.JOB_END_COL,
            ],
            dtype={
                self.JOB_AIRCRAFT_NAME_COL: str,
                self.JOB_AIRCRAFT_MODEL_COL: str,
                self.JOB_PHASE_COL: str,
                self.JOB_PATTERN_COL: str,
            },
            parse_dates=[self.JOB_START_COL, self.JOB_END_COL],
        ).dropna(how="all")

        self._parse_initial_configuration(df_initial_configuration)
        self._parse_initial_assignments(df_initial_positioning)
        self._parse_unplanned_jobs(df_unplanned_jobs)

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

    def _parse_initial_assignments(self, df):
        assignments_initial_conditions = {}
        position_map = {p.name: p for p in self.positions}

        for _, row in df.iterrows():
            position_name = str(row[self.INITIAL_POSITION_COL]).strip()
            msn = str(row[self.AIRCRAFT_NAME_COL]).strip()

            if not msn or msn.lower() == "nan":
                continue  # No aircraft assigned to this position

            if msn not in self.aircrafts:
                raise ValueError(f"Aircraft {msn} not found in known aircrafts.")

            if position_name not in position_map:
                raise ValueError(f"Unknown position '{position_name}'.")

            pos = position_map[position_name]
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

    def _parse_unplanned_jobs(self, df):
        unplanned_jobs = []
        position_map = {p.name: p for p in self.positions}
        phase_map = {p.name: p for p in self.phases}

        for _, row in df.iterrows():
            aircraft_name = str(row[self.JOB_AIRCRAFT_NAME_COL]).strip()
            aircraft_model_raw = str(row[self.JOB_AIRCRAFT_MODEL_COL]).strip()
            phase_code = str(row[self.JOB_PHASE_COL]).strip()
            pattern = str(row.get(self.JOB_PATTERN_COL, "")).strip()
            start_raw = row.get(self.JOB_START_COL, "")
            end_raw = row[self.JOB_END_COL]

            if not aircraft_name or aircraft_name.lower() == "nan":
                continue

            if aircraft_name in self.aircrafts:
                raise ValueError(f"Already existing aircraft {aircraft_name}")

            if aircraft_model_raw not in self.aircraft_models:
                raise ValueError(
                    f"Aircraft model '{aircraft_model_raw}' is not recognized. "
                    f"Make sure it is defined in the problem setup or replace it with an existing model from: {list(self.aircraft_models.keys())}."
                )

            if phase_code not in phase_map:
                raise ValueError(
                    f"Phase code '{phase_code}' is not recognized. "
                    f"Ensure it is defined in the problem setup or use one of the available phase codes: {list(phase_map.keys())}."
                )

            new_aircraft = Aircraft(
                aircraft_name, self.aircraft_models[aircraft_model_raw]
            )
            self.aircrafts[aircraft_name] = new_aircraft

            # Parse END date
            if not end_raw:
                raise ValueError(f"Missing END date for aircraft {aircraft_name}")
            end = end_raw.date()

            # Parse START date
            if pd.isna(start_raw):
                start = self.t0
            else:
                start = start_raw.date()

            job = Job(
                aircraft=new_aircraft,
                phase=phase_map[phase_code],
                start=start,
                end=end,
            )

            unplanned_jobs.append(job)

        self.jobs += unplanned_jobs
        # self.initial_conditions["unplanned_jobs"] = unplanned_jobs
