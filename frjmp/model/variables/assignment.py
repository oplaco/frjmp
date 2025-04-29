from ortools.sat.python import cp_model
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.utils.timeline_utils import get_active_time_indices


def create_assignment_variables(
    model: cp_model.CpModel,
    jobs: list[Job],
    positions: list[Position],
    compressed_dates,
    date_to_index,
):
    assigned_vars = {}

    for j_idx, job in enumerate(jobs):
        assigned_vars[j_idx] = {}
        active_time_indices = get_active_time_indices(
            job, compressed_dates, date_to_index
        )

        # Check if any position is compatible for this job
        compatible_positions = [
            p_idx
            for p_idx, pos in enumerate(positions)
            if can_position_cover_phase_needs(pos, job.phase)
        ]
        if not compatible_positions:
            raise ValueError(
                f"No compatible position found for job {j_idx} ({job.aircraft.name}, phase={job.phase.name})"
            )

        # Safely loop over compatible positions only
        for p_idx in compatible_positions:
            assigned_vars[j_idx][p_idx] = {}
            for t_idx in active_time_indices:
                var = model.NewBoolVar(f"assigned_j{j_idx}_p{p_idx}_t{t_idx}")
                assigned_vars[j_idx][p_idx][t_idx] = var

    return assigned_vars


def can_position_cover_phase_needs(position: Position, phase: Phase):
    position_need_names = {need.name for need in position.available_needs}
    return phase.required_need.name in position_need_names
