"""Fetches the most recent hypothesis from the running Hypothesis Agent API
(port 8200) and POSTs it to the running Investigation Pipeline API (port
8300). Both servers must already be running — see the top-level README's
"Running the complete project" section.

    python examples/run_investigation_from_server.py
"""

from __future__ import annotations

import sys

import httpx

HYPOTHESIS_API = "http://127.0.0.1:8200"
PIPELINE_API = "http://127.0.0.1:8300"


def main() -> None:
    stories = httpx.get(f"{HYPOTHESIS_API}/api/stories", timeout=10).json()
    if not stories:
        print(
            f"No hypotheses yet at {HYPOTHESIS_API}/api/stories — "
            "generate one first (click '+ Generate hypothesis' in the UI, "
            f"or POST {HYPOTHESIS_API}/api/generate).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    story = stories[-1]  # most recently generated
    hypothesis_package = {
        "organization_id": story["organization_id"],
        "hypothesis_statement": story["statement"],
        "mechanism_explanation": story["mechanism"],
        "business_lens": story["lens"],
        "target_constructs": story.get("target_constructs", []),
        "scorecard": story["scorecard"],
        "critique": story["critique"],
        "search_stats": story["search_stats"],
        "headline": story.get("title", ""),
        "summary": story.get("description", ""),
    }

    print(f"Investigating: {hypothesis_package['headline'] or hypothesis_package['hypothesis_statement'][:80]}")
    print("This runs several real LLM calls plus real analytics/plotting — can take a few minutes...")

    response = httpx.post(
        f"{PIPELINE_API}/api/investigate",
        json={"hypothesis_package": hypothesis_package},
        timeout=1200,
    )
    response.raise_for_status()
    result = response.json()

    print()
    print(f"InsightPackage id: {result['insight_package_id']}")
    print(f"Executive summary: {result['executive_summary']}")
    print(f"Figures: {result['figures']}")
    print(f"\nFull report: {PIPELINE_API}/api/insights/{result['insight_package_id']}")


if __name__ == "__main__":
    main()
