if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date, timedelta
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
edv_need = Need("E")
wp_need = Need("WP")
w_need = Need("Waiting")

# Create Phases
edv_phase = Phase("EDV", edv_need)
foury_phase = Phase("4Y", wp_need)
waiting_phase = Phase("WAITING", wp_need)

# Create Unit
c295 = UnitType("C295")
a400m = UnitType("A400M")
unit_types = [c295, a400m]
a1 = Unit("185", c295)
a2 = Unit("187", a400m)

# t_init
t_init = date(2025, 4, 15)

# Create Jobs
job1 = Job(a1, edv_phase, t_init, t_init + timedelta(days=10))
job2 = Job(a2, foury_phase, date(2025, 4, 16), date(2025, 5, 20))
job3 = Job(a2, edv_phase, date(2025, 5, 25), date(2025, 7, 20))

jobs = [job1, job2, job3]
jobs = insert_waiting_jobs(jobs, waiting_phase)

# Create Positions
posA = Position("Hangar A", [edv_need, wp_need, waiting_phase])
posB = Position("Hangar B", [edv_need, wp_need, waiting_phase])

positions = [posA, posB]
conf = PositionsConfiguration(positions)
pos_unit_dep = PositionsUnitTypeDependency(unit_types, positions)


# Initialize Problem
problem = Problem(
    jobs=jobs,
    positions_configuration=conf,
    position_unittype_dependency=pos_unit_dep,
    t_init=t_init,
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
                    f"Movement Job {j_idx} at t={t_idx} ({problem.index_to_date[t_idx]})"
                )

    for j_idx, j_dict in problem.assigned_vars.items():
        for p_idx, p_dict in j_dict.items():
            for t_idx, var in p_dict.items():
                if solver.Value(var) == 1:
                    print(
                        f"Assignment of Job {j_idx} to position {p_idx} at  t={t_idx} ({problem.index_to_date[t_idx]})"
                    )

    for j_idx, j_dict in problem.pattern_assigned_vars.items():
        job = problem.jobs[j_idx]
        for t_idx, t_dict in j_dict.items():
            for k_idx, var in t_dict.items():
                if solver.Value(var) == 1:
                    pattern = job.unit.type.allowed_patterns[k_idx]
                    pos_names = [p.name for p in pattern.positions]
                    print(
                        f"Job {j_idx} at t={t_idx} ({problem.index_to_date[t_idx]}): "
                        f"Pattern {k_idx} → Positions {pos_names}"
                    )

    plot_solution(problem, solver)

else:
    print("No solution found.")

print("Finished.")
