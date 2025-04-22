import matplotlib.pyplot as plt
from typing import List
from matplotlib.ticker import MaxNLocator


def plot_cumulative_movements(
    moved_vars,
    solver,
    jobs,
    ax,
    x_vals: List,
    color_map: dict,
    use_real_dates: bool = False,
):
    """
    Plots the cumulative number of movements per aircraft over time using step lines.

    Each aircraft is shown as a separate line, increasing its cumulative movement count
    whenever a job is detected as moved at a given time step.

    Args:
        moved_vars: Dict[int][int] -> BoolVar indicating if job j moved at time step t.
        solver: OR-Tools solver with values assigned after solving.
        jobs: List of Job objects involved in the problem.
        ax: Matplotlib Axes object to draw the plot on.
        x_vals: List of time step values (either compressed time step indices or real dates),
                aligned with solver time dimension.
        color_map: Dict mapping aircraft names to consistent plot colors.
        use_real_dates: Whether the X-axis should use actual date values instead of time step indices.

    Returns:
        fig, ax: The Matplotlib Figure and Axes with the plotted data.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    else:
        fig = ax.figure

    aircraft_names = [job.aircraft.name for job in jobs]
    aircraft_to_j_indices = {
        name: [j_idx for j_idx, job in enumerate(jobs) if job.aircraft.name == name]
        for name in sorted(set(aircraft_names))
    }

    time_indices = [t for t, _ in enumerate(x_vals)]
    max_total = 0
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
            if total > max_total:
                max_total = total

        ax.step(
            x_vals,
            cumulative,
            label=aircraft_name,
            linewidth=2,
            color=color_map.get(aircraft_name, "black"),
            where="post",
        )

    ax.set_title("Cumulative Movements per Aircraft Over Time")
    ax.set_ylabel("Cumulative Movements")
    ax.set_yticks(list(range(0, max_total + 3)))

    # Add legend based on color map
    handles = [
        plt.Line2D([0], [0], color=color_map[name], lw=2, label=name)
        for name in color_map
    ]
    ax.legend(handles=handles, title="Aircraft")

    return fig, ax
