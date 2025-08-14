import matplotlib.pyplot as plt


import matplotlib.pyplot as plt


def plot_assignment_gantt(
    assigned_vars,
    solver,
    positions,
    jobs,
    ax,
    x_vals,
    color_map,
):
    """
    Plot a Gantt-like chart of job assignments over time per position.
    Each bar represents a continuous block of time where a job is assigned
    to a position. Time is shown as discrete step indices (0, 1, 2...).

    Args:
        assigned_vars: Dict[j][p][t] -> BoolVar
        solver: OR-Tools solver
        positions: List of Position objects
        jobs: List of Job objects
        ax: Matplotlib Axes
        x_vals: List[int] (time step indices)
        color_map: unit name → color
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    else:
        fig = ax.figure

    y_labels = []
    y_ticks = []

    for p_idx, pos in enumerate(positions):
        y = p_idx
        y_labels.append(pos.name)
        y_ticks.append(y)

        for j_idx, job in enumerate(jobs):
            if p_idx not in assigned_vars.get(j_idx, {}):
                continue

            active = [
                t_idx
                for t_idx, var in assigned_vars[j_idx][p_idx].items()
                if solver.Value(var)
            ]
            if not active:
                continue

            unit_name = job.unit.name
            start = prev = active[0]

            for t in active[1:] + [None]:
                if t is None or t != prev + 1:
                    bar_left = x_vals[start]
                    width = prev - start + 1

                    ax.barh(
                        y,
                        width,
                        left=bar_left,
                        height=0.8,
                        color=color_map[unit_name],
                        edgecolor="black",
                    )
                    label_x = bar_left + width / 2
                    ax.text(
                        label_x,
                        y,
                        str(job),
                        va="center",
                        ha="center",
                        fontsize=8,
                        color="white",
                    )
                    if t is not None:
                        start = t
                prev = t

    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels)
    ax.set_title("Unit Positioning Gantt Chart")
    ax.set_xlabel("Time Step Index")
    return fig, ax
