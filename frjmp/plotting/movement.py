import matplotlib.pyplot as plt
from typing import List
from matplotlib.ticker import MaxNLocator


def plot_cumulative_movements(
    movement_vars,
    solver,
    ax,
    x_vals: List,
    color_map: dict,
    use_real_dates: bool = False,
):
    """
    Plots the cumulative number of movements per aircraft over time using step lines.

    Each aircraft is shown as a separate line, increasing its cumulative movement count
    whenever a movement is detected at a given time step.

    Args:
        movement_vars: Dict[aircraft_name][t_idx] -> BoolVar indicating movement.
        solver: OR-Tools solver with values assigned after solving.
        ax: Matplotlib Axes object to draw the plot on.
        x_vals: List of time step values (either compressed indices or real dates),
                aligned with solver time dimension.
        color_map: Dict mapping aircraft names to consistent plot colors.
        use_real_dates: Whether to label the X-axis using real dates.

    Returns:
        fig, ax: The Matplotlib Figure and Axes with the plotted data.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    else:
        fig = ax.figure

    time_indices = [t for t, _ in enumerate(x_vals)]
    max_total = 0

    for aircraft_name in sorted(movement_vars.keys()):
        cumulative = []
        total = 0
        for t in time_indices:
            var = movement_vars[aircraft_name].get(t)
            if var is not None:
                total += solver.Value(var)
            cumulative.append(total)
            max_total = max(max_total, total)

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
    ax.set_yticks(list(range(0, max_total + 2)))
    ax.set_xlabel("Date" if use_real_dates else "Time Step")

    # Legend
    handles = [
        plt.Line2D([0], [0], color=color_map[name], lw=2, label=name)
        for name in sorted(movement_vars.keys())
    ]
    ax.legend(handles=handles, title="Aircraft")

    return fig, ax
