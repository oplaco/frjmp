if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date
from frjmp.model.adapter import ShiftAdapter
from frjmp.model.sets.need import Need
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.unit import Unit, UnitType
from frjmp.model.sets.position import Position
from frjmp.model.sets.job import Job
from frjmp.model.problem import Problem
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.parameters.position_unit_model import PositionsUnitTypeDependency
from examples.plot_example import plot_solution
from frjmp.utils.preprocessing_utils import insert_waiting_jobs

# Create Needs
wipe_need = Need("Wipe")
tools_need = Need("Tools")
towing_need = Need("Towing")

# Create Phases
cleaning_phase = Phase("Cleaning", wipe_need)
repair_phase = Phase("Repair", tools_need)
delivery_phase = Phase("Delivery", tools_need)

# Create Unit
mercedes = UnitType("Mercedes")
audi = UnitType("Audi")
unit_types = [mercedes, audi]
u1 = Unit("CLA 250", mercedes)
u2 = Unit("CLA Coupé", mercedes)
u3 = Unit("A8", audi)

# t_init
shifts = ["Morning", "Evening", "Night"]
origin = [date(2025, 4, 15), "Morning"]
time_adapter = ShiftAdapter(origin, shifts)

# Create Jobs
job1 = Job(
    u1, cleaning_phase, (date(2025, 4, 15), "Evening"), (date(2025, 4, 19), "Night")
)
job2 = Job(
    u2, repair_phase, (date(2025, 4, 17), "Morning"), (date(2025, 5, 1), "Night")
)
job3 = Job(
    u3, cleaning_phase, (date(2025, 5, 3), "Night"), (date(2025, 5, 13), "Night")
)

jobs = [job1, job2, job3]
jobs = insert_waiting_jobs(jobs, delivery_phase, time_adapter)

# Create Positions
posA = Position("Workshop A", [wipe_need, tools_need, delivery_phase])
posB = Position("Workshop B", [wipe_need, tools_need, delivery_phase])

positions = [posA, posB]
conf = PositionsConfiguration(positions)
pos_unit_dep = PositionsUnitTypeDependency(unit_types, positions)


# Initialize Problem
problem = Problem(
    jobs=jobs,
    positions_configuration=conf,
    position_unittype_dependency=pos_unit_dep,
    time_adapter=time_adapter,
)


# Solve
status, solver = problem.solve()

# Print results
print("\nSolution:")
if status == 4:
    print("\nOptimal Solution found:")
    for j_idx, j_dict in problem.unit_movement_vars.items():
        for t_idx, var in j_dict.items():
            if solver.Value(var) == 1:
                print(
                    f"Movement Job {j_idx} at t={t_idx} ({problem.index_to_value[t_idx]})"
                )

    for j_idx, j_dict in problem.assigned_vars.items():
        for p_idx, p_dict in j_dict.items():
            for t_idx, var in p_dict.items():
                if solver.Value(var) == 1:
                    print(
                        f"Assignment of Job {j_idx} to position {p_idx} at  t={t_idx} ({problem.index_to_value[t_idx]})"
                    )

    for j_idx, j_dict in problem.pattern_assigned_vars.items():
        job = problem.jobs[j_idx]
        for t_idx, t_dict in j_dict.items():
            for k_idx, var in t_dict.items():
                if solver.Value(var) == 1:
                    pattern = job.unit.type.allowed_patterns[k_idx]
                    pos_names = [p.name for p in pattern.positions]
                    print(
                        f"Job {j_idx} at t={t_idx} ({problem.index_to_value[t_idx]}): "
                        f"Pattern {k_idx} → Positions {pos_names}"
                    )

    plot_solution(problem, solver)

else:
    print("No solution found.")

print("Finished.")
