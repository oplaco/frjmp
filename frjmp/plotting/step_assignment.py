import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


def plot_timestep_assignment(
    background_path,
    position_geometry,
    assigned_vars,
    jobs,
    solver,
    t_indices,
    index_to_date,
    color_map,
):
    """
    Plots unit assignments over a spatial map for each t_idx given,
    using the assignment variables of the form assigned_vars[j_idx][p_idx][t_idx].

    Args:
        background_path: path to the background image.
        position_geometry: dict[position_name] -> list of (x, y) tuples.
        assigned_vars: dict[j_idx][p_idx][t_idx] = BoolVar.
        jobs: list of Job objects, indexed by j_idx.
        solver: resolved cp_model.CpSolver.
        t_indices: list of timesteps to render.
        index_to_date: dict[t_idx] -> datetime.
        color_map: dict[unit_name] -> matplotlib color.
    """

    assignments_by_t = {t: {} for t in t_indices}

    for j_idx in assigned_vars:
        for p_idx in assigned_vars[j_idx]:
            for t in assigned_vars[j_idx][p_idx]:
                if t in t_indices and solver.Value(assigned_vars[j_idx][p_idx][t]) == 1:
                    pos_name = list(position_geometry.keys())[p_idx]
                    unit_name = jobs[j_idx].unit.name
                    assignments_by_t[t][pos_name] = unit_name

    for t in t_indices:
        fig, ax = plt.subplots(figsize=(8, 6))
        img = plt.imread(background_path)
        extent = (0, 10, 0, 10)  # Ajusta según el tamaño real
        ax.imshow(img, extent=extent, zorder=0)

        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"Snapshot at t={t} ({index_to_date[t]})")

        for pos_name, coords in position_geometry.items():
            unit = assignments_by_t[t].get(pos_name)
            color = color_map.get(unit, None)

            poly = Polygon(
                coords,
                closed=True,
                edgecolor="black",
                facecolor=color if color else "none",
                linewidth=1.5,
                zorder=1,
            )
            ax.add_patch(poly)

            # Centered label
            xs, ys = zip(*coords)
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)

            if unit:
                label = f"{pos_name}\n{unit}"
                text_color = "white"
            else:
                label = pos_name
                text_color = "black"

            ax.text(
                cx,
                cy,
                label,
                ha="center",
                va="center",
                fontsize=8,
                color=text_color,
                zorder=2,
            )

        plt.tight_layout()
        plt.show(block=False)
        plt.pause(0.1)
