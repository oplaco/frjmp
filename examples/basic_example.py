from datetime import date

if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from frjmp.model.sets.need import Need
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.aircraft import Aircraft
from frjmp.model.sets.position import Position
from frjmp.model.sets.job import Job
from frjmp.model.problem import Problem
from frjmp.plotting.assignment import plot_assignment_gantt
from frjmp.plotting.movement import plot_cumulative_movements

# Create Needs
e_need = Need("E")
wp_need = Need("WP")

# Create Phases
edv_phase = Phase("EDV", e_need)
foury_phase = Phase("4Y", wp_need)

# Create Aircraft
a1 = Aircraft("185")
a2 = Aircraft("187")

# Create Jobs
job1 = Job(a1, edv_phase, date(2025, 4, 15), date(2025, 4, 18))
job2 = Job(a2, edv_phase, date(2025, 4, 16), date(2025, 4, 20))
job3 = Job(a2, foury_phase, date(2025, 4, 25), date(2025, 7, 20))

jobs = [job1, job2, job3]

# Create Positions
posA = Position("Hangar A", [wp_need, e_need])
posB = Position("Hangar B", [wp_need, e_need])

positions = [posA, posB]


# Initialize Problem
problem = Problem(jobs, positions)


# Solve
status, solver = problem.solve()

# Print results
print("\nSolution:")
if status == 4:
    print("\nOptimal Solution found:")
    for j_idx, j_dict in problem.assigned_vars.items():
        for p_idx, p_dict in j_dict.items():
            for t_idx, var in p_dict.items():
                if solver.Value(var):
                    print(
                        f"Job {j_idx} → Position {p_idx} at t={t_idx} ({problem.index_to_date[t_idx]})"
                    )

    plot_assignment_gantt(
        assigned_vars=problem.assigned_vars,
        solver=solver,
        positions=problem.positions,
        index_to_date=problem.index_to_date,
        jobs=problem.jobs,
    )

    plot_cumulative_movements(
        moved_vars=problem.movement_vars,
        solver=solver,
        jobs=problem.jobs,
        index_to_date=problem.index_to_date,
        use_real_dates=True,
    )

else:
    print("No solution found.")
