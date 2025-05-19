import pandas as pd
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.aircraft import Aircraft


class IndustrialPlan:
    # Excel sheet names
    INDUSTRIAL_PLAN_SHEET = "INDUSTRIAL_PLAN"
    REQUIRED_SHEETS = {INDUSTRIAL_PLAN_SHEET}

    # Excel columns titles
    AIRCRAFT_NAME_COL = "MSN"
    AIRCRAFT_MODEL_COL = "MODEL"
    PHASE_COL = "ST"
    START_COL = "START"
    END_COL = "END"

    # Rows to remove from industrial plan (Normally because they represent milestones rather than actual phases with work).
    PHASES_TO_REMOVE = ["DGAM", "TECHNICAL ACCEPTANCE", "ADM", "CAR", "ROLLOUT", "CTOT"]

    def __init__(
        self,
        filepath: str,
        phases: list[Phase],
        aircraft_models: dict,
    ):
        self.filepath = filepath
        self.phases = phases
        self.aircraft_models = aircraft_models
        self.aircrafts = {}
        self.jobs = []
        self.load()

    def load(self):
        xls = pd.ExcelFile(self.filepath)
        missing = self.REQUIRED_SHEETS - set(xls.sheet_names)
        if missing:
            raise ValueError(f"Missing required sheets: {', '.join(missing)}")

        df_industrial_phase = xls.parse(self.INDUSTRIAL_PLAN_SHEET)

        self._parse_aircrafts(df_industrial_phase)
        self._parse_jobs(df_industrial_phase)

    def _parse_aircrafts(self, df):
        self.aircrafts = {}

        grouped = df.groupby("MSN")["MODEL"].unique()

        for msn, models in grouped.items():
            if len(models) > 1:
                raise ValueError(
                    f"Multiple models found for MSN {msn}: {models.tolist()}"
                )

            model_name = models[0]
            if model_name not in self.aircraft_models:
                raise ValueError(
                    f"Unknown model '{model_name}' for MSN {msn}. \
                    \nAvailable models are {list(self.aircraft_models.keys())}"
                )

            model = self.aircraft_models[model_name]
            self.aircrafts[str(msn)] = Aircraft(str(msn), model)

    def _parse_jobs(self, df):
        phase_map = {phase.name: phase for phase in self.phases}

        for _, row in df.iterrows():
            msn = str(row[self.AIRCRAFT_NAME_COL]).strip()
            phase_code = str(row[self.PHASE_COL]).strip()
            if phase_code in self.PHASES_TO_REMOVE:
                continue
            start = pd.to_datetime(row[self.START_COL]).date()
            end = pd.to_datetime(row[self.END_COL]).date()

            if msn not in self.aircrafts:
                raise ValueError(
                    f"Aircraft with MSN {msn} not found in aircrafts dictionary."
                )

            if phase_code not in phase_map:
                raise ValueError(f"Unknown phase code '{phase_code}' in job row.")

            aircraft = self.aircrafts[msn]
            phase = phase_map[phase_code]

            self.jobs.append(Job(aircraft, phase, start, end))
