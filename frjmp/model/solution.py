# frjmp/solution.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd

CP_SAT_OPTIMAL = 4
CP_SAT_FEASIBLE = 3


@dataclass(frozen=True)
class SolutionMetrics:
    status: int
    is_optimal: bool
    is_feasible: bool
    objective_value: Optional[float]
    best_bound: Optional[float]
    wall_time_sec: Optional[float]


class Solution:
    """
    Result container for FRJMP runs.
    Provides easy tabular views in dataframes.
    """

    def __init__(self, problem, solver, status: int):
        self.problem = problem
        self.solver = solver
        self.metrics = SolutionMetrics(
            status=status,
            is_optimal=(status == CP_SAT_OPTIMAL),
            is_feasible=(status in (CP_SAT_OPTIMAL, CP_SAT_FEASIBLE)),
            objective_value=getattr(solver, "ObjectiveValue", lambda: None)(),
            best_bound=getattr(solver, "BestObjectiveBound", lambda: None)(),
            wall_time_sec=getattr(solver, "WallTime", lambda: None)(),
        )

        # Build tidy frames (only 1s).
        self.assignments = self._build_assignments_df()
        self.movements = self._build_movements_df()
        self.patterns = self._build_patterns_df()

    def _build_assignments_df(self) -> pd.DataFrame:
        """
        Columns: job_id, position_id, t_idx, time_value
        One row per (job, position, time) where assigned==1.
        """
        rows: List[Dict[str, Any]] = []
        idx2time = (
            self.problem.index_to_value
        )  # e.g. datetime/shift tuple via your adapter

        for j_idx, p_dict in self.problem.assigned_vars.items():
            job = self.problem.jobs[j_idx]
            job_unit_name = job.unit.name
            job_phase = job.phase.name
            for p_idx, t_dict in p_dict.items():
                position = self.problem.positions[p_idx]
                position_name = position.name
                for t_idx, var in t_dict.items():
                    if self.solver.Value(var) == 1:
                        rows.append(
                            dict(
                                job_idx=j_idx,
                                job_unit_name=job_unit_name,
                                job_phase=job_phase,
                                position_idx=p_idx,
                                position_name=position_name,
                                t_idx=t_idx,
                                time_value=idx2time[t_idx],
                            )
                        )
        return (
            pd.DataFrame(rows)
            .sort_values(["t_idx", "position_idx", "job_idx"])
            .reset_index(drop=True)
        )

    def _build_movements_df(self) -> pd.DataFrame:
        """
        Columns: unit_name, t_before_idx, t_after_idx, t_before_value, t_after_value,
                from_position, to_position
        One row per (unit, time) where movement==1.
        """
        rows: List[Dict[str, Any]] = []
        idx2time = self.problem.index_to_value
        assignments = self.assignments
        out_position = self.problem.positions_configuration.out_position

        for unit_name, t_dict in self.problem.unit_movement_vars.items():
            for t_idx, var in t_dict.items():
                if self.solver.Value(var) == 1:
                    t_before = t_idx
                    t_after = t_idx + 1
                    # Filter assignments for this unit and t_before / t_after
                    df_before = assignments.query(
                        "job_unit_name == @unit_name and t_idx == @t_before"
                    )
                    df_after = assignments.query(
                        "job_unit_name == @unit_name and t_idx == @t_after"
                    )

                    from_pos = (
                        df_before["position_name"].iloc[0]
                        if not df_before.empty
                        else out_position
                    )
                    to_pos = (
                        df_after["position_name"].iloc[0]
                        if not df_after.empty
                        else out_position
                    )

                    rows.append(
                        dict(
                            unit_name=unit_name,
                            from_position=from_pos,
                            to_position=to_pos,
                            t_before_idx=t_before,
                            t_after_idx=t_after,
                            t_before_value=idx2time[t_before],
                            t_after_value=idx2time[t_after],
                        )
                    )

        return (
            pd.DataFrame(rows)
            .sort_values(["t_before_idx", "unit_name"])
            .reset_index(drop=True)
        )

    def _build_patterns_df(self) -> pd.DataFrame:
        """
        Columns: job_id, t_idx, pattern_idx, positions (list[str])
        Only where pattern_assigned==1.
        """
        rows: List[Dict[str, Any]] = []
        idx2time = self.problem.index_to_value

        for j_idx, t_map in self.problem.pattern_assigned_vars.items():
            job = self.problem.jobs[j_idx]
            job_unit_name = job.unit.name
            job_phase = job.phase.name
            for t_idx, k_map in t_map.items():
                for k_idx, var in k_map.items():
                    if self.solver.Value(var) == 1:
                        pattern = job.unit.type.allowed_patterns[k_idx]
                        pos_names = [p.name for p in pattern.positions]
                        rows.append(
                            dict(
                                job_idx=j_idx,
                                job_unit_name=job_unit_name,
                                job_phase=job_phase,
                                t_idx=t_idx,
                                time_value=idx2time[t_idx],
                                pattern_idx=k_idx,
                                pattern_positions=pos_names,
                            )
                        )
        return (
            pd.DataFrame(rows)
            .sort_values(["t_idx", "job_idx", "pattern_idx"])
            .reset_index(drop=True)
        )
