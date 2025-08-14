import matplotlib.pyplot as plt
from typing import List
from matplotlib.ticker import MaxNLocator


def plot_cumulative_movements(
    unit_movement_vars,
    solver,
    ax,
    x_vals: List,
    color_map: dict,
    use_real_values: bool = False,
):
    """
    Plots the cumulative number of movements per unit over time using step lines.

    Each unit is shown as a separate line, increasing its cumulative movement count
    whenever a movement is detected at a given time step.

    Args:
        unit_movement_vars: Dict[unit_name][t_idx] -> BoolVar indicating movement.
        solver: OR-Tools solver with values assigned after solving.
        ax: Matplotlib Axes object to draw the plot on.
        x_vals: List of time step values (either compressed indices or real dates),
                aligned with solver time dimension.
        color_map: Dict mapping unit names to consistent plot colors.
        use_real_values: Whether to label the X-axis using real dates.

    Returns:
        fig, ax: The Matplotlib Figure and Axes with the plotted data.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    else:
        fig = ax.figure

    time_indices = [t for t, _ in enumerate(x_vals)]
    max_total = 0

    for unit_name in sorted(unit_movement_vars.keys()):
        cumulative = []
        total = 0
        for t in time_indices:
            var = unit_movement_vars[unit_name].get(t)
            if var is not None:
                total += solver.Value(var)
            cumulative.append(total)
            max_total = max(max_total, total)

        ax.step(
            x_vals,
            cumulative,
            label=unit_name,
            linewidth=2,
            color=color_map.get(unit_name, "black"),
            where="post",
        )

    ax.set_title("Cumulative Movements per Unit Over Time")
    ax.set_ylabel("Cumulative Movements")
    ax.set_yticks(list(range(0, max_total + 2)))
    ax.set_xlabel("Date" if use_real_values else "Time Step")

    # # Add legend based on color map
    # handles = [
    #     plt.Line2D([0], [0], color=color_map[name], lw=2, label=name)
    #     for name in color_map
    # ]
    # ax.legend(
    #     handles=handles,
    #     title="Unit",
    #     loc="upper right",
    #     ncol=4,
    # )

    return fig, ax
