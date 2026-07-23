"""Visualization Planner + Plot Generation Tool contracts — see
docs/PLATFORM_ARCHITECTURE.md §13-14. The planner decides WHAT; the tool
executes HOW. `ResolvedChartData` is the only thing that crosses back from
adapter-land into a contract — small, aggregated, framework-agnostic."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class VisualizationSpec(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("viz"))
    title: str
    business_objective: str = ""
    variables: list[str] = Field(default_factory=list)
    visualization_type: str  # registry key — see tools/plot_generation, not a hardcoded enum
    reason: str = ""
    priority: int = 3
    executive_message: str = ""
    expected_insight: str = ""
    data_requirements: list[str] = Field(default_factory=list)


class VisualizationPlan(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("vizplan"))
    specs: list[VisualizationSpec] = Field(default_factory=list)


class ResolvedChartData(BaseModel):
    categories: list[str] = Field(default_factory=list)
    series: dict[str, list[float]] = Field(default_factory=dict)
    raw_points: list[tuple[float, float]] | None = None
    matrix: list[list[float]] | None = None  # e.g. correlation matrices, heatmaps
    matrix_labels: list[str] | None = None
    # Quadrant-divergence charts only (see tools/plot_generation and
    # framework/derived_metrics.quadrant_divergence) — threshold lines
    # dividing raw_points into four quadrants.
    x_threshold: float | None = None
    y_threshold: float | None = None


class ChartTheme(BaseModel):
    """Configuration-driven professional styling — applied consistently by
    every PlottingEngine adapter, never hardcoded per chart."""

    palette: list[str] = Field(
        default_factory=lambda: [
            "#2E5B4C", "#78D64B", "#4A4A4A", "#B8D8C8", "#1F3A2E", "#8FA89B",
        ]
    )
    font_family: str = "DejaVu Sans"
    background_color: str = "#FFFFFF"
    title_font_size: int = 15
    label_font_size: int = 10
    grid_color: str = "#E6E6E6"


class GeneratedFigure(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("fig"))
    spec_id: str
    format: Literal["png", "svg", "pdf", "html"] = "png"
    file_ref: str
    caption: str = ""
    alt_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
