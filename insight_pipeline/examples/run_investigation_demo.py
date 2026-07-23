"""End-to-end demo: Hypothesis Agent -> Investigation Pipeline, offline
(MockLLMService, real Book1.xlsx cohort data, real scipy/matplotlib).

    cd insight_pipeline && python examples/run_investigation_demo.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from hypothesis_agent.adapters.shl_sample_cohort import load_organization_and_landscape
from hypothesis_agent.agent import HypothesisAgent
from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.di.container import build_dependencies as build_hypothesis_dependencies
from insight_pipeline.config.settings import PipelineConfig
from insight_pipeline.di.container import build_pipeline_dependencies
from insight_pipeline.orchestrator.pipeline import InvestigationPipeline

_XLSX_PATH = Path(__file__).parents[2] / "Book1.xlsx"


async def main() -> None:
    hypothesis_config = AgentConfig.load()
    hypothesis_config.backends.llm = "mock"
    hypothesis_config.backends.embedding = "hash"
    hypothesis_config.search.max_iterations = 4
    hypothesis_config.search.random_seed = 7
    hypothesis_deps = build_hypothesis_dependencies(hypothesis_config)

    profile, landscape = load_organization_and_landscape(_XLSX_PATH)
    hypothesis_deps.organization_repository.add(profile)
    hypothesis_deps.employee_repository.add(landscape)

    hypothesis_agent = HypothesisAgent(hypothesis_deps)
    print("=" * 80)
    print("Stage 1: Hypothesis Agent")
    print("=" * 80)
    hypothesis_package = await hypothesis_agent.discover(profile.organization_id)
    print(f"Headline: {hypothesis_package.headline}")
    print(f"Lens: {hypothesis_package.business_lens}")
    print(f"Composite: {hypothesis_package.scorecard.composite:.3f}")

    pipeline_config = PipelineConfig.load()
    pipeline_config.backends.excel_path = str(_XLSX_PATH)
    pipeline_deps = build_pipeline_dependencies(hypothesis_deps, pipeline_config)
    pipeline = InvestigationPipeline(pipeline_deps)

    print()
    print("=" * 80)
    print("Stage 2: Investigation Pipeline")
    print("=" * 80)
    insight_package = await pipeline.run(hypothesis_package)

    print(f"Investigation plan: {len(insight_package.investigation_plan.variables_required)} variables")
    print(f"Analytics: {[m.method for m in insight_package.analytics_results.methods_run]}")
    print(f"Root cause: {len(insight_package.root_cause_graph.nodes)} nodes, {len(insight_package.root_cause_graph.edges)} edges")
    print(f"Business insights: {len(insight_package.business_insights.findings)} findings, "
          f"{len(insight_package.business_insights.risks)} risks, "
          f"{len(insight_package.business_insights.opportunities)} opportunities")
    print(f"Narrative summary: {insight_package.narrative.executive_summary[:200]}")
    print(f"Figures generated: {[f.file_ref for f in insight_package.generated_figures]}")
    print(f"InsightPackage id: {insight_package.id}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
