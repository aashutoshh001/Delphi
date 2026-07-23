"""Minimal local API for the Investigation Pipeline — extends the platform
alongside hypothesis_agent.server (a separate process/port; insight_pipeline
depends on hypothesis_agent, never the reverse, so it stays a standalone
FastAPI app rather than being bolted onto the Hypothesis Agent's).

Run from the Delphi/ repo root so relative paths (Book1.xlsx,
sample_data/insights.json) resolve correctly:

    cd Delphi/
    python -m insight_pipeline.server
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.di.container import build_dependencies as build_hypothesis_dependencies
from insight_pipeline.config.settings import PipelineConfig
from insight_pipeline.di.container import build_pipeline_dependencies
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.orchestrator.pipeline import InvestigationPipeline

logger = get_logger("server")

_hypothesis_config = AgentConfig.load()
_hypothesis_deps = build_hypothesis_dependencies(_hypothesis_config)
_pipeline_config = PipelineConfig.load()
_pipeline_deps = build_pipeline_dependencies(_hypothesis_deps, _pipeline_config)
_pipeline = InvestigationPipeline(_pipeline_deps)

logger.info(
    "investigation pipeline server starting",
    extra={
        "extra_fields": {
            "llm_backend": _hypothesis_config.backends.llm,
            "excel_path": _pipeline_config.backends.excel_path,
        }
    },
)

app = FastAPI(title="Delphi Investigation Pipeline API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class InvestigateRequest(BaseModel):
    hypothesis_package: HypothesisPackage


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/investigate")
async def investigate(body: InvestigateRequest) -> dict:
    logger.info(
        "investigate requested",
        extra={"extra_fields": {"hypothesis_package_id": body.hypothesis_package.package_id}},
    )
    package = await _pipeline.run(body.hypothesis_package)
    return {
        "insight_package_id": package.id,
        "executive_summary": package.narrative.executive_summary,
        "figures": [f.file_ref for f in package.generated_figures],
    }


@app.get("/api/insights/{insight_id}")
async def get_insight(insight_id: str) -> dict:
    package = await _pipeline_deps.insight_package_repository.get(insight_id)
    if package is None:
        raise HTTPException(status_code=404, detail="insight package not found")
    return package.model_dump(mode="json")


@app.get("/api/insights")
async def list_insights(limit: int = 20) -> list[dict]:
    packages = await _pipeline_deps.insight_package_repository.list_recent(limit)
    return [
        {
            "id": p.id,
            "generated_at": p.generated_at.isoformat(),
            "headline": p.hypothesis_package.headline,
            "executive_summary": p.narrative.executive_summary,
        }
        for p in packages
    ]
