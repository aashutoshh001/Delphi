"""Deterministic rendering only — see docs/PLATFORM_ARCHITECTURE.md §14. No
reasoning happens here; the Visualization Planner already decided WHAT, this
only decides HOW to draw it. Publication-quality static output (PNG/SVG/PDF).

Ships bar, scatter, heatmap/correlation-matrix, histogram, boxplot, and
quadrant-divergence (V2 architecture plan Part 4F — the generalized
two-dimension divergence chart: any two grounded dimensions, threshold lines,
points colored by quadrant) — the rest of the §14 chart catalog (waterfall,
sankey, network graph, ...) are future renderers, each a small addition to
`_RENDERERS` with zero change to VisualizationSpec, the resolver, or the
Visualization Planner."""

from __future__ import annotations

from pathlib import Path

from insight_pipeline.contracts.visualization import (
    ChartTheme,
    GeneratedFigure,
    ResolvedChartData,
    VisualizationSpec,
)
from insight_pipeline.ports.plotting_engine import PlottingEngine

_BAR_TYPES = {"bar", "grouped_bar", "bar_chart"}
_SCATTER_TYPES = {"scatter", "scatter_plot"}
_CORRELATION_TYPES = {"heatmap", "correlation_matrix"}
_HISTOGRAM_TYPES = {"histogram", "distribution"}
_BOXPLOT_TYPES = {"boxplot", "box_plot"}
_QUADRANT_TYPES = {"quadrant_divergence", "quadrant_scatter"}

_SUPPORTED = (
    _BAR_TYPES | _SCATTER_TYPES | _CORRELATION_TYPES | _HISTOGRAM_TYPES | _BOXPLOT_TYPES | _QUADRANT_TYPES
)

# adapters/plotting/matplotlib_engine.py -> Delphi/ repo root (same anchor as
# config/settings.py). `file_ref` needs to double as a URL path the static
# frontend can load a chart image from (`sample_data/insights/figures/x.png`),
# so it's kept repo-root-relative even though `output_dir` itself is now
# always an absolute, cwd-independent path.
_REPO_ROOT = Path(__file__).resolve().parents[5]


class MatplotlibPlottingEngine(PlottingEngine):
    def __init__(self, output_dir: Path | str) -> None:
        self._output_dir = Path(output_dir)

    def supports(self, visualization_type: str) -> bool:
        return visualization_type in _SUPPORTED

    async def render(
        self, spec: VisualizationSpec, data: ResolvedChartData, theme: ChartTheme
    ) -> GeneratedFigure:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        self._output_dir.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
        fig.patch.set_facecolor(theme.background_color)
        ax.set_facecolor(theme.background_color)

        vtype = spec.visualization_type
        if vtype in _CORRELATION_TYPES:
            self._draw_correlation_matrix(ax, data, theme)
        elif vtype in _QUADRANT_TYPES:
            self._draw_quadrant(ax, data, theme)
        elif vtype in _SCATTER_TYPES:
            self._draw_scatter(ax, data, theme)
        elif vtype in _HISTOGRAM_TYPES:
            self._draw_bar(ax, data, theme)
        elif vtype in _BOXPLOT_TYPES:
            self._draw_boxplot(ax, data, theme)
        else:
            self._draw_bar(ax, data, theme)

        ax.set_title(spec.title, fontsize=theme.title_font_size, fontweight="bold", color="#191919")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        fig.tight_layout()

        file_path = self._output_dir / f"{spec.id}.png"
        fig.savefig(file_path, facecolor=fig.get_facecolor())
        plt.close(fig)

        try:
            file_ref = str(file_path.resolve().relative_to(_REPO_ROOT))
        except ValueError:
            # output_dir isn't under the repo root (e.g. a test's tmp_path) —
            # an absolute path is still correct there, just not URL-shaped.
            file_ref = str(file_path)

        return GeneratedFigure(
            spec_id=spec.id,
            format="png",
            file_ref=file_ref,
            caption=spec.executive_message or spec.title,
            alt_text=spec.expected_insight or spec.title,
        )

    def _draw_bar(self, ax, data: ResolvedChartData, theme: ChartTheme) -> None:
        if not data.series:
            ax.text(0.5, 0.5, "no data", ha="center", va="center")
            return
        categories = data.categories or list(range(len(next(iter(data.series.values())))))
        width = 0.8 / max(len(data.series), 1)
        for i, (name, values) in enumerate(data.series.items()):
            positions = [x + i * width for x in range(len(categories))]
            ax.bar(positions, values, width=width, label=name, color=theme.palette[i % len(theme.palette)])
        ax.set_xticks([x + width * (len(data.series) - 1) / 2 for x in range(len(categories))])
        ax.set_xticklabels(categories, rotation=30, ha="right", fontsize=theme.label_font_size)
        if len(data.series) > 1:
            ax.legend(fontsize=theme.label_font_size)

    def _draw_scatter(self, ax, data: ResolvedChartData, theme: ChartTheme) -> None:
        if not data.raw_points:
            ax.text(0.5, 0.5, "no data", ha="center", va="center")
            return
        xs = [p[0] for p in data.raw_points]
        ys = [p[1] for p in data.raw_points]
        ax.scatter(xs, ys, color=theme.palette[0], alpha=0.6, edgecolors="none")
        if data.categories and len(data.categories) >= 2:
            ax.set_xlabel(data.categories[0], fontsize=theme.label_font_size)
            ax.set_ylabel(data.categories[1], fontsize=theme.label_font_size)

    def _draw_quadrant(self, ax, data: ResolvedChartData, theme: ChartTheme) -> None:
        """Generalized quadrant-divergence scatter (V2 architecture plan
        Part 4F) — threshold lines split the plot into four quadrants,
        points colored by which quadrant they fall in, so a systematic
        divergence (e.g. most points above the x=y line) reads at a glance
        rather than requiring the viewer to compute it themselves."""
        if not data.raw_points or data.x_threshold is None or data.y_threshold is None:
            ax.text(0.5, 0.5, "no data", ha="center", va="center")
            return
        xs = [p[0] for p in data.raw_points]
        ys = [p[1] for p in data.raw_points]
        x_thr, y_thr = data.x_threshold, data.y_threshold

        quadrant_colors = {
            "hi_hi": theme.palette[1 % len(theme.palette)],
            "hi_lo": theme.palette[2 % len(theme.palette)],
            "lo_hi": theme.palette[3 % len(theme.palette)],
            "lo_lo": theme.palette[4 % len(theme.palette)],
        }
        point_colors = [
            quadrant_colors["hi_hi" if x >= x_thr and y >= y_thr else
                            "hi_lo" if x >= x_thr else
                            "lo_hi" if y >= y_thr else "lo_lo"]
            for x, y in zip(xs, ys)
        ]
        ax.scatter(xs, ys, c=point_colors, alpha=0.65, edgecolors="none", s=28)
        ax.axvline(x_thr, color=theme.grid_color, linestyle="--", linewidth=1.2)
        ax.axhline(y_thr, color=theme.grid_color, linestyle="--", linewidth=1.2)

        # x=y reference diagonal — only meaningful when both dimensions
        # share a comparable scale, which is the common case for this
        # chart type (e.g. two rater perspectives on the same 0-5 item).
        lo = min(min(xs), min(ys))
        hi = max(max(xs), max(ys))
        ax.plot([lo, hi], [lo, hi], color=theme.palette[2 % len(theme.palette)], linewidth=1, linestyle=":", alpha=0.7)

        if data.categories and len(data.categories) >= 2:
            ax.set_xlabel(data.categories[0], fontsize=theme.label_font_size)
            ax.set_ylabel(data.categories[1], fontsize=theme.label_font_size)

    def _draw_correlation_matrix(self, ax, data: ResolvedChartData, theme: ChartTheme) -> None:
        if not data.matrix:
            ax.text(0.5, 0.5, "no data", ha="center", va="center")
            return
        im = ax.imshow(data.matrix, cmap="RdYlGn", vmin=-1, vmax=1)
        labels = data.matrix_labels or [str(i) for i in range(len(data.matrix))]
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=theme.label_font_size)
        ax.set_yticklabels(labels, fontsize=theme.label_font_size)
        ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    def _draw_boxplot(self, ax, data: ResolvedChartData, theme: ChartTheme) -> None:
        if not data.series:
            ax.text(0.5, 0.5, "no data", ha="center", va="center")
            return
        ax.boxplot(list(data.series.values()), labels=list(data.series.keys()))
        ax.tick_params(axis="x", rotation=30, labelsize=theme.label_font_size)
