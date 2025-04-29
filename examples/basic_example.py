if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date, timedelta
from frjmp.model.sets.need import Need
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.aircraft import Aircraft, AircraftModel
from frjmp.model.sets.position import Position
from frjmp.model.sets.job import Job
from frjmp.model.problem import Problem
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

# Create Aircraft
c295 = AircraftModel("C295")
a400m = AircraftModel("A400M")
aircraft_models = [c295, a400m]
a1 = Aircraft("185", c295)
a2 = Aircraft("187", a400m)

# T0
t0 = date(2025, 4, 15)

# Create Jobs
job1 = Job(a1, edv_phase, t0, t0 + timedelta(days=10))
job2 = Job(a2, foury_phase, date(2025, 4, 16), date(2025, 5, 20))
job3 = Job(a2, edv_phase, date(2025, 5, 25), date(2025, 7, 20))

jobs = [job1, job2, job3]
jobs = insert_waiting_jobs(jobs, waiting_phase)

# Create Positions
posA = Position("Hangar A", [edv_need, wp_need, waiting_phase])
posB = Position("Hangar B", [wp_need, waiting_phase])

positions = [posA, posB]


# Initialize Problem
problem = Problem(aircraft_models, jobs, positions, t0)


# Solve
status, solver = problem.solve()

# Print results
print("\nSolution:")
if status == 4:
    print("\nOptimal Solution found:")
    for j_idx, j_dict in problem.aircraft_movement_vars.items():
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

    plot_solution(problem, solver)

else:
    print("No solution found.")

print("Finished.")
