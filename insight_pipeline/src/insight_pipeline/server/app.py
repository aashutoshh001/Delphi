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

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.di.container import build_dependencies as build_hypothesis_dependencies
from insight_pipeline.adapters.feedback_store.json_insight_feedback_store import (
    JsonInsightFeedbackStore,
)
from insight_pipeline.config.settings import PipelineConfig
from insight_pipeline.di.container import build_pipeline_dependencies
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.orchestrator.pipeline import InvestigationPipeline
from insight_pipeline.server.research_chat import build_research_messages

logger = get_logger("server")

_hypothesis_config = AgentConfig.load()
_hypothesis_deps = build_hypothesis_dependencies(_hypothesis_config)
_pipeline_config = PipelineConfig.load()
_pipeline_deps = build_pipeline_dependencies(_hypothesis_deps, _pipeline_config)
_pipeline = InvestigationPipeline(_pipeline_deps)

# --- Research Engine chat + expert feedback (see server/research_chat.py) ----
# The chat bot needs a real LLM; the offline mock returns gibberish, so treat
# "mock" as unavailable and serve a graceful fallback instead.
_LLM_AVAILABLE = _hypothesis_config.backends.llm != "mock"
_LLM_FALLBACK = "The research assistant is temporarily unavailable. Please try again shortly."

# Subject-matter-expert feedback gate. Server-side only — the password is never
# sent to the browser. Demo default; override via env for anything real.
_EXPERT_USER = os.environ.get("DELPHI_EXPERT_USER", "subjectexpert")
_EXPERT_PASS = os.environ.get("DELPHI_EXPERT_PASS", "delphie123")

_feedback_store = JsonInsightFeedbackStore(
    Path(_pipeline_config.backends.insight_store_path).parent / "insight_feedback.json"
)


def _expert_ok(username: str, password: str) -> bool:
    return username == _EXPERT_USER and password == _EXPERT_PASS

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


# --- Delphi Research Engine chat (per-insight, live LLM + graceful fallback) --


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


def _framework_context(package) -> str:
    """SHL-metric context for the bot — a compact family summary plus a
    description of the columns this insight is actually grounded on."""
    registry = getattr(_pipeline_deps, "framework_registry", None)
    if registry is None:
        return ""
    try:
        parts = [registry.family_summary()]
        grounded_cols: list[str] = []
        gm = getattr(package, "grounding_map", None)
        if gm is not None:
            grounded_cols = gm.all_grounded_columns()
        parts.append(registry.describe_for_prompt(grounded_cols or None, limit=60))
        return "\n".join(p for p in parts if p)
    except Exception:
        return ""


async def _knowledge_excerpts(message: str, organization_id: str | None) -> list[str]:
    retriever = getattr(_pipeline_deps, "knowledge_retriever", None)
    if retriever is None:
        return []
    try:
        docs = await retriever.retrieve(message, organization_id, top_k=3)
        return [f"{d.title}: {d.excerpt}" for d in docs]
    except Exception:
        return []


@app.post("/api/insights/{insight_id}/chat")
async def insight_chat(insight_id: str, body: ChatRequest) -> dict:
    package = await _pipeline_deps.insight_package_repository.get(insight_id)
    if package is None:
        raise HTTPException(status_code=404, detail="insight package not found")

    if not _LLM_AVAILABLE:
        return {"reply": _LLM_FALLBACK, "available": False}

    org_id = package.hypothesis_package.organization_id
    knowledge = await _knowledge_excerpts(body.message, org_id)
    request = build_research_messages(
        package,
        _framework_context(package),
        knowledge,
        body.message,
        [m.model_dump() for m in body.history],
    )
    try:
        response = await _pipeline_deps.llm_service.complete(request)
        return {"reply": response.content.strip(), "available": True}
    except Exception as exc:  # gateway down / misconfigured — never 500 the UI
        logger.warning("research chat LLM call failed", extra={"extra_fields": {"error": str(exc)}})
        return {"reply": _LLM_FALLBACK, "available": False}


# --- Expert-gated feedback (server-side credential check) ---------------------


class ExpertLogin(BaseModel):
    username: str
    password: str


class FeedbackRequest(BaseModel):
    username: str
    password: str
    feedback: str


@app.post("/api/expert/login")
async def expert_login(body: ExpertLogin) -> dict:
    return {"ok": _expert_ok(body.username, body.password)}


@app.post("/api/insights/{insight_id}/feedback")
async def insight_feedback(insight_id: str, body: FeedbackRequest) -> dict:
    if not _expert_ok(body.username, body.password):
        raise HTTPException(status_code=401, detail="expert credentials required")
    text = body.feedback.strip()
    if not text:
        raise HTTPException(status_code=400, detail="feedback text is empty")
    package = await _pipeline_deps.insight_package_repository.get(insight_id)
    if package is None:
        raise HTTPException(status_code=404, detail="insight package not found")
    await _feedback_store.add(insight_id, text)
    return {"ok": True}
