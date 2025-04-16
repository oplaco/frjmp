import matplotlib.pyplot as plt
from datetime import timedelta


import matplotlib.pyplot as plt
from datetime import timedelta


def plot_cumulative_movements(
    moved_vars, solver, jobs, index_to_date, use_real_dates=False
):
    """
    Plots the cumulative number of movements per aircraft over time using step lines.

    Args:
        moved_vars: Dict[j_idx][t_idx] -> BoolVar indicating if job j moved at t
        solver: OR-Tools solver with values
        jobs: list of Job objects
        index_to_date: mapping from time index to real date
        use_real_dates: whether to use actual dates on the x-axis
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    aircraft_names = [job.aircraft.name for job in jobs]
    aircraft_to_j_indices = {
        name: [j_idx for j_idx, job in enumerate(jobs) if job.aircraft.name == name]
        for name in set(aircraft_names)
    }

    time_indices = sorted(index_to_date.keys())
    x_vals = [index_to_date[t] if use_real_dates else t for t in time_indices]

    for aircraft_name, job_indices in aircraft_to_j_indices.items():
        cumulative = []
        total = 0
        for t in time_indices:
            movements = [
                solver.Value(moved_vars[j_idx][t])
                for j_idx in job_indices
                if t in moved_vars.get(j_idx, {})
            ]
            total += sum(movements)
            cumulative.append(total)

        ax.step(x_vals, cumulative, label=aircraft_name, linewidth=2, where="post")

    ax.set_title("Cumulative Movements per Aircraft Over Time")
    ax.set_ylabel("Cumulative Movements")
    ax.set_xlabel("Date" if use_real_dates else "Time Step")
    ax.legend(title="Aircraft")
    plt.tight_layout()
    plt.show()
