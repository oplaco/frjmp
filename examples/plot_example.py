from frjmp.plotting.assignment import plot_assignment_gantt
from frjmp.plotting.movement import plot_cumulative_movements
from frjmp.plotting.step_assignment import plot_timestep_assignment
import matplotlib.pyplot as plt


def plot_solution(problem, solver):
    # 1. Prepare aircraft color mapping in your main code:
    aircraft_names = sorted({job.aircraft.name for job in problem.jobs})
    color_map = {name: plt.cm.tab10(i % 10) for i, name in enumerate(aircraft_names)}

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
        aircraft_movement_vars=problem.aircraft_movement_vars,
        solver=solver,
        ax=axs[1],
        x_vals=x_vals,
        color_map=color_map,
        use_real_dates=use_real_dates,
    )

    # 5. Create a shared legend
    handles = [
        plt.Line2D([0], [0], color=color_map[name], lw=4, label=name)
        for name in aircraft_names
    ]
    fig.legend(
        handles=handles,
        title="Aircraft",
        loc="upper right",
        ncol=5,
        fontsize="small",
        title_fontsize="small",
    )

    plt.tight_layout()
    plt.show(block=False)

    # 6. Plot step snapshots
    background_path = "data/background.PNG"
    position_geometry = {
        "H2_1": [(2.6, 4.6), (2.6, 4.2), (2.3, 4.2), (2.3, 4.6)],
        "H2_2": [(2.6, 4.1), (2.6, 3.7), (2.3, 3.7), (2.3, 4.1)],
        "H2_3": [(2.3, 4.6), (2.3, 4.2), (2, 4.2), (2, 4.6)],
        "H2_4": [(2.3, 4.1), (2.3, 3.7), (2, 3.7), (2, 4.1)],
        "H2_5": [(2, 4.6), (2, 4.2), (1.7, 4.2), (1.7, 4.6)],
        "H2_6": [(2, 4.1), (2, 3.7), (1.7, 3.7), (1.7, 4.1)],
        "ZA_4": [(7, 3.1), (7, 3.6), (6.7, 3.6), (6.7, 3.1)],
        "ZA_5": [(6.7, 3.1), (6.7, 3.6), (6.4, 3.6), (6.4, 3.1)],
        "ZA_6": [(6.4, 3.1), (6.4, 3.6), (6.1, 3.6), (6.1, 3.1)],
        "ZA_7": [(6.1, 3.1), (6.1, 3.6), (5.8, 3.6), (5.8, 3.1)],
        "ZA_8": [(5.8, 3.1), (5.8, 3.6), (5.5, 3.6), (5.5, 3.1)],
        "P_1": [(3.8, 1.5), (4.3, 1.5), (4.3, 1), (3.8, 1)],
        "P_2": [(3.8, 1), (4.3, 1), (4.3, 0.5), (3.8, 0.5)],
        "E_1": [(6.7, 2.3), (7.1, 2.3), (7.1, 2.7), (6.7, 2.7)],
        "PT_1": [(5, 1.2), (5.5, 1.2), (5.5, 0.7), (5, 0.7)],
        "SOL_1": [(3.2, 1.8), (3.7, 1.8), (3.7, 1.3), (3.2, 1.3)],
        "F_1": [(4.35, 2), (4.75, 2), (4.75, 1.6), (4.35, 1.6)],
        "F_2": [(4.75, 2), (5.15, 2), (5.15, 1.6), (4.75, 1.6)],
        "AG_1": [(5.5, 1.80), (5.9, 1.80), (5.9, 1.4), (5.5, 1.4)],
        "AG_2": [(5.9, 1.80), (6.3, 1.80), (6.3, 1.4), (5.9, 1.4)],
        "AG_3": [(5.5, 1.40), (5.9, 1.40), (5.9, 1), (5.5, 1)],
        "AG_4": [(5.9, 1.40), (6.3, 1.40), (6.3, 1), (5.9, 1)],
    }

    plot_timestep_assignment(
        background_path,
        position_geometry,
        problem.assigned_vars,
        problem.jobs,
        solver,
        [0, 1, 2],
        problem.index_to_date,
        color_map,
    )

    plt.show()  # Block the display
