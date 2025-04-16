import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def plot_assignment_gantt(assigned_vars, solver, positions, index_to_date, jobs):
    """
    Creates a Gantt-like chart showing which job is assigned to which position at which time.

    Args:
        assigned_vars: Dict[j][p][t] -> BoolVar from the solution
        solver: OR-Tools solver with solution
        positions: list of Position objects
        index_to_date: dict of {int: date}, mapping compressed time index to actual date
        jobs: list of Job objects
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    pos_index_map = {idx: pos.name for idx, pos in enumerate(positions)}
    y_labels = []
    y_ticks = []

    colors = plt.cm.get_cmap("tab10", len(jobs))

    for p_idx, pos_name in pos_index_map.items():
        y = p_idx
        y_labels.append(pos_name)
        y_ticks.append(y)

        for j_idx, job in enumerate(jobs):
            if p_idx not in assigned_vars.get(j_idx, {}):
                continue

            active_blocks = []
            for t_idx, var in assigned_vars[j_idx][p_idx].items():
                if solver.Value(var):
                    active_blocks.append(t_idx)

            if active_blocks:
                # Group into consecutive time blocks
                start = prev = active_blocks[0]
                for t in active_blocks[1:] + [None]:  # Add sentinel
                    if t is None or t != prev + 1:
                        # Plot from start to prev
                        ax.barh(
                            y,
                            prev - start + 1,
                            left=start,
                            height=0.4,
                            color=colors(j_idx),
                            edgecolor="black",
                        )
                        ax.text(
                            (start + prev) / 2,
                            y,
                            jobs[j_idx],
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
    ax.set_xlabel("Time Step Index (compressed)")
    ax.set_title("Aircraft Positioning Gantt Chart")

    plt.tight_layout()
    plt.show()
