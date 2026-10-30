from __future__ import annotations

import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


AXIS_LABELS = ["x", "y", "z"]


class SimulationRenderer:

    def __init__(
        self,
        figsize: tuple[int, int] = (6, 6),
        projection: str = "2d",
        xlim: list[float] | None = None,
        ylim: list[float] | None = None,
        zlim: list[float] | None = None,
        axes: tuple[int, int] = (0, 2),
        elev: float = 25.0,
        azim: float = -60.0,
        output_dir: str | None = None,
    ):
        self._figsize = figsize
        self._projection = projection
        self._xlim = xlim
        self._ylim = ylim
        self._zlim = zlim
        self._axes = axes
        self._elev = elev
        self._azim = azim
        self._output_dir = output_dir or tempfile.mkdtemp(prefix="sim_render_")
        os.makedirs(self._output_dir, exist_ok=True)

    @property
    def is_3d(self) -> bool:
        return self._projection == "3d"

    def _make_fig(self):
        if self.is_3d:
            fig = plt.figure(figsize=self._figsize)
            ax = fig.add_subplot(111, projection="3d")
            ax.view_init(elev=self._elev, azim=self._azim)
            return fig, ax
        return plt.subplots(figsize=self._figsize)

    def _apply_limits(self, ax) -> None:
        if self.is_3d:
            if self._xlim:
                ax.set_xlim3d(self._xlim)
            if self._ylim:
                ax.set_ylim3d(self._ylim)
            if self._zlim:
                ax.set_zlim3d(self._zlim)
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_zlabel("z")
        else:
            ax_x, ax_y = self._axes
            if self._xlim:
                ax.set_xlim(self._xlim)
            if self._ylim:
                ax.set_ylim(self._ylim)
            ax.set_xlabel(AXIS_LABELS[ax_x])
            ax.set_ylabel(AXIS_LABELS[ax_y])
            ax.set_aspect("equal")
            ax.grid(True, alpha=0.3)

    def _plot_object_2d(self, ax, name: str, pos: list[float], **kwargs) -> None:
        ax_x, ax_y = self._axes
        x, y = pos[ax_x], pos[ax_y]
        color = kwargs.get("color", "steelblue")
        radius = kwargs.get("radius", 0.1)
        circle = patches.Circle((x, y), radius, fill=True, color=color, alpha=0.8)
        ax.add_patch(circle)
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8)

    def _plot_object_3d(self, ax, name: str, pos: list[float], **kwargs) -> None:
        color = kwargs.get("color", "steelblue")
        size = kwargs.get("radius", 0.1) * 500
        ax.scatter(pos[0], pos[1], pos[2], s=size, color=color, alpha=0.8, depthshade=True)
        ax.text(pos[0], pos[1], pos[2], f"  {name}", fontsize=8)

    def _plot_marker_2d(self, ax, marker: dict) -> None:
        ax_x, ax_y = self._axes
        pos = marker["position"]
        x, y = pos[ax_x], pos[ax_y]
        radius = marker.get("radius", 0.2)
        color = marker.get("color", "red")
        style = marker.get("style", "open")
        if style == "open":
            circle = patches.Circle(
                (x, y), radius, fill=False, edgecolor=color, linewidth=2, linestyle="--",
            )
        else:
            circle = patches.Circle((x, y), radius, fill=True, color=color, alpha=0.3)
        ax.add_patch(circle)
        if "label" in marker:
            ax.annotate(
                marker["label"], (x, y),
                textcoords="offset points", xytext=(5, 5), fontsize=8, color=color,
            )

    def _plot_marker_3d(self, ax, marker: dict) -> None:
        pos = marker["position"]
        radius = marker.get("radius", 0.2)
        color = marker.get("color", "red")
        style = marker.get("style", "open")
        if style == "open":
            u = np.linspace(0, 2 * np.pi, 40)
            cx = pos[0] + radius * np.cos(u)
            cy = pos[1] + radius * np.sin(u)
            cz = np.full_like(u, pos[2])
            ax.plot(cx, cy, cz, color=color, linestyle="--", linewidth=1.5)
        else:
            ax.scatter(pos[0], pos[1], pos[2], s=radius * 500, color=color, alpha=0.3)
        if "label" in marker:
            ax.text(pos[0], pos[1], pos[2], f"  {marker['label']}", fontsize=8, color=color)

    def render_state(
        self,
        objects: dict[str, dict],
        time: float,
        extra_markers: list[dict] | None = None,
        filename: str | None = None,
    ) -> str:
        fig, ax = self._make_fig()

        for name, obj in objects.items():
            pos = obj["position"]
            kwargs = {k: obj[k] for k in ("color", "radius") if k in obj}
            if self.is_3d:
                self._plot_object_3d(ax, name, pos, **kwargs)
            else:
                self._plot_object_2d(ax, name, pos, **kwargs)

        if extra_markers:
            for marker in extra_markers:
                if self.is_3d:
                    self._plot_marker_3d(ax, marker)
                else:
                    self._plot_marker_2d(ax, marker)

        ax.set_title(f"t = {time:.4f}")
        self._apply_limits(ax)

        if filename is None:
            filename = f"frame_{time:.6f}.png"
        path = os.path.join(self._output_dir, filename)
        fig.savefig(path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        return path

    def render_trajectory(
        self,
        history: list[dict],
        step: int,
        trail_length: int = 50,
        extra_markers: list[dict] | None = None,
    ) -> str:
        if step < 0 or step >= len(history):
            raise IndexError(f"Step {step} out of range [0, {len(history) - 1}]")

        current = history[step]
        fig, ax = self._make_fig()

        obj_names = [k for k in current if k != "time" and isinstance(current[k], dict)]
        trail_start = max(0, step - trail_length)

        for name in obj_names:
            positions = [history[s][name]["position"] for s in range(trail_start, step + 1)]
            pos = current[name]["position"]

            if self.is_3d:
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]
                zs = [p[2] for p in positions]
                ax.plot(xs, ys, zs, "-", alpha=0.3, linewidth=1)
                ax.scatter(pos[0], pos[1], pos[2], s=40, depthshade=True)
                ax.text(pos[0], pos[1], pos[2], f"  {name}", fontsize=8)
            else:
                ax_x, ax_y = self._axes
                xs = [p[ax_x] for p in positions]
                ys = [p[ax_y] for p in positions]
                ax.plot(xs, ys, "-", alpha=0.3, linewidth=1)
                ax.plot(pos[ax_x], pos[ax_y], "o", markersize=8)
                ax.annotate(name, (pos[ax_x], pos[ax_y]),
                            textcoords="offset points", xytext=(5, 5), fontsize=8)

        if extra_markers:
            for marker in extra_markers:
                if self.is_3d:
                    self._plot_marker_3d(ax, marker)
                else:
                    self._plot_marker_2d(ax, marker)

        ax.set_title(f"Step {step} | t = {current['time']:.4f}")
        self._apply_limits(ax)

        path = os.path.join(self._output_dir, f"step_{step:06d}.png")
        fig.savefig(path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        return path
