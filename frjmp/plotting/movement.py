import matplotlib.pyplot as plt
from typing import List


def plot_cumulative_movements(
    unit_movement_vars: dict,
    solver,
    ax,
    x_vals: List[int],
    color_map: dict,
):
    """
    Plots cumulative number of movements per unit over discrete time step indices.

    Args:
        unit_movement_vars: Dict[unit_name][t_idx] -> BoolVar
        solver: OR-Tools solver
        ax: Matplotlib Axes
        x_vals: List[int] time step indices (e.g., [0, 1, 2, ...])
        color_map: Dict of unit_name → color

    Returns:
        fig, ax: The plot Figure and Axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    else:
        fig = ax.figure

    time_indices = list(range(len(x_vals)))
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
    ax.set_xlabel("Time Step Index")
    ax.set_yticks(list(range(0, max_total + 2)))

    return fig, ax
