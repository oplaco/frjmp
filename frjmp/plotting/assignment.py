import matplotlib.pyplot as plt


def plot_assignment_gantt(
    assigned_vars, solver, positions, jobs, ax, x_vals, color_map, use_real_values
):
    """
    Creates a Gantt-like chart showing job assignments over time, grouped by position.

    Each bar represents a time block during which a job is assigned to a specific position.
    Bars are colored per unit to maintain consistency, and unit labels are shown inside the bars.

    Args:
        assigned_vars: Dict[int][int][int] -> BoolVar indicating if job j is assigned to position p at time step t.
        solver: OR-Tools solver with values assigned after solving.
        positions: List of Position objects available for job assignment.
        jobs: List of Job objects to be scheduled.
        ax: Matplotlib Axes object to draw the plot on.
        x_vals: List of time step values (either compressed indices or real dates), matching solver time steps.
        color_map: Dict mapping unit names to consistent plot colors.
        use_real_values: Whether the X-axis should use actual date values instead of time step indices.

    Returns:
        fig, ax: The Matplotlib Figure and Axes with the plotted data.
    """

    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    else:
        fig = ax.figure

    pos_index_map = {idx: pos.name for idx, pos in enumerate(positions)}
    y_labels = []
    y_ticks = []

    for p_idx, pos_name in pos_index_map.items():
        y = p_idx
        y_labels.append(pos_name)
        y_ticks.append(y)
        for j_idx, job in enumerate(jobs):
            if p_idx not in assigned_vars.get(j_idx, {}):
                continue
            unit_name = job.unit.name
            active_blocks = []
            for t_idx, var in assigned_vars[j_idx][p_idx].items():
                if solver.Value(var):
                    active_blocks.append(t_idx)
            if active_blocks:
                start = prev = active_blocks[0]
                for t in active_blocks[1:] + [None]:
                    if t is None or t != prev + 1:
                        # Use x_vals[start] as the left edge
                        bar_left = x_vals[start]
                        if use_real_values:
                            width = (x_vals[prev] - x_vals[start]).days + 1
                        else:
                            width = prev - start + 1

                        ax.barh(
                            y,
                            width,
                            left=bar_left,
                            height=0.8,
                            color=color_map[unit_name],
                            edgecolor="black",
                        )
                        # Place label at midpoint
                        if use_real_values:
                            from datetime import timedelta

                            label_x = bar_left + timedelta(days=width / 2)
                        else:
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
