from frjmp.plotting.assignment import plot_assignment_gantt
from frjmp.plotting.movement import plot_cumulative_movements
from frjmp.plotting.step_assignment import plot_timestep_assignment
import matplotlib.pyplot as plt


def plot_solution(problem, solver):
    # 1. Prepare unit color mapping in your main code:
    unit_names = sorted({job.unit.name for job in problem.jobs})
    color_map = {name: plt.cm.tab10(i % 10) for i, name in enumerate(unit_names)}

    # 2. Compute x_vals for both plots:
    use_real_dates = False
    time_indices = sorted(problem.index_to_date.keys())
    x_vals = [problem.index_to_date[t] if use_real_dates else t for t in time_indices]

    # 3. Pass ax, color_map, and x_vals to both plotting functions:
    fig, axs = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    plot_assignment_gantt(
        assigned_vars=problem.assigned_vars,
        solver=solver,
        positions=problem.positions,
        jobs=problem.jobs,
        ax=axs[0],
        x_vals=x_vals,
        color_map=color_map,
        use_real_dates=use_real_dates,
    )

    plot_cumulative_movements(
        unit_movement_vars=problem.unit_movement_vars,
        solver=solver,
        ax=axs[1],
        x_vals=x_vals,
        color_map=color_map,
        use_real_dates=use_real_dates,
    )

    # 5. Create a shared legend
    handles = [
        plt.Line2D([0], [0], color=color_map[name], lw=4, label=name)
        for name in unit_names
    ]
    fig.legend(
        handles=handles,
        title="Unit",
        loc="upper right",
        ncol=5,
        fontsize="small",
        title_fontsize="small",
    )

    plt.tight_layout()
    plt.show(block=True)
