"""Observed run of the Hypothesis Agent using the NEW Workday landscape door.

Runs OFFLINE by default (MockLLMService + HashEmbeddingService) — no API key
needed — and writes a detailed, step-by-step log to ~/delphi_run.log so each
stage of the pipeline can be inspected afterward.

  * If LITELLM_API_KEY is set in hypothesis_agent/.env, uses the real LLM.
  * Sets employee_repository="workday" and workday_probe=True, so the agent's
    data landscape reflects the Workday HRIS + SHL assessment door and attempts
    a live worker-count confirmation (falls back to the offline count if the
    Workday token is missing/expired — the run still completes).

Run:  python run_observed.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load hypothesis_agent/.env so LITELLM_* and WORKDAY_* reach the process.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / "hypothesis_agent" / ".env")
except Exception:
    pass

LOG_PATH = Path.home() / "delphi_run.log"
USE_REAL_LLM = bool(os.getenv("LITELLM_API_KEY"))

fh = logging.FileHandler(LOG_PATH, mode="w")
fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"))
root = logging.getLogger("hypothesis_agent")
root.handlers = [fh, logging.StreamHandler(sys.stdout)]
root.setLevel(logging.DEBUG)
root.propagate = False


def banner(msg: str) -> None:
    line = f"\n{'=' * 70}\n=== {msg}\n{'=' * 70}"
    print(line)
    logging.getLogger("hypothesis_agent.observed").info("STEP: %s", msg)


async def main() -> None:
    banner(f"START  {datetime.now().isoformat(timespec='seconds')}")

    from hypothesis_agent.agent import HypothesisAgent
    from hypothesis_agent.config.settings import AgentConfig
    from hypothesis_agent.contracts.organization import OrganizationProfile
    from hypothesis_agent.di.container import build_dependencies

    banner(f"1. CONFIG  ({'REAL litellm' if USE_REAL_LLM else 'offline mock'} LLM + hash embeddings + WORKDAY door)")
    config = AgentConfig.load()
    config.backends.llm = "litellm" if USE_REAL_LLM else "mock"
    config.backends.embedding = "hash"
    config.backends.employee_repository = "workday"  # <-- the new door
    config.backends.workday_probe = True             # <-- attempt live worker-count confirmation
    config.logging.level = "DEBUG"
    print(f"   llm={config.backends.llm}  embedding={config.backends.embedding}  "
          f"employee_repository={config.backends.employee_repository}  "
          f"workday_probe={config.backends.workday_probe}  max_iterations={config.search.max_iterations}")

    deps = build_dependencies(config)

    banner("2. ORGANIZATION PROFILE  (registered for the SHL cohort)")
    deps.organization_repository.add(
        OrganizationProfile(
            organization_id="shl-cohort",
            name="SHL Sample Cohort (Workday-linked)",
            core_attributes={
                "industry": "assessment / talent intelligence",
                "headcount_band": "400",
                "structure": "single Workday tenant (cebshl_dpt2)",
                "business_goals": ["identify high-potentials", "close skill gaps",
                                   "fair compensation", "succession readiness"],
            },
        )
    )
    print("   org=shl-cohort registered")

    banner("3. DATA LANDSCAPE  (what the Workday door tells the LLM exists)")
    landscape = await deps.employee_repository.get_data_landscape("shl-cohort")
    print(f"   employees≈{landscape.employee_count_estimate}   fields={len(landscape.available_fields)}")
    for f in landscape.available_fields:
        print(f"     - {f.name:26} [{f.category:20}] coverage={f.coverage_ratio}")
    print(f"   notes: {landscape.notes}")

    banner("4. DISCOVER  (LLM runs the search loop: understand -> generate -> critique -> score -> improve -> loop)")
    agent = HypothesisAgent(deps)
    package = await agent.discover("shl-cohort")

    banner("5. RESULT  (the single best HypothesisPackage)")
    print(f"   headline : {getattr(package, 'headline', None)}")
    print(f"   statement: {package.hypothesis_statement}")
    print(f"   lens     : {package.business_lens}")
    print(f"   mechanism: {package.mechanism_explanation}")
    print(f"   targets  : {package.target_constructs}")
    sc = package.scorecard
    print("   scorecard:")
    for dim in ["business_value", "novelty", "depth", "actionability", "strategic_importance",
                "feasibility", "organizational_impact", "expected_insight", "confidence", "future_extensibility"]:
        v = getattr(sc, dim, None)
        if v is not None:
            print(f"     {dim:22} {v}")
    print(f"   composite: {getattr(sc, 'composite', None)}")

    banner(f"6. SEARCH TRACE  ({len(package.reasoning_path)} steps)")
    for i, step in enumerate(package.reasoning_path, 1):
        print(f"   {i:2}. {step}")

    banner(f"DONE — full log written to {LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
