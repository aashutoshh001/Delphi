"""Builds the LLM message list for the "Delphi Research Engine" chatbot on the
insight report page. Keeps the server endpoint thin and this logic unit-testable.

The bot answers questions ONLY about one specific insight, grounded in that
InsightPackage's content plus the SHL metric framework and a short org context.
It must decline anything unrelated to the report — the system prompt enforces
that; the LLM adapter does the actual call.
"""

from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from insight_pipeline.contracts.insight_package import InsightPackage

_MAX_HISTORY_TURNS = 12  # keep the last N prior messages for context


def _bullet(items: list[Any], limit: int = 6) -> str:
    lines = [f"  - {str(i).strip()}" for i in (items or []) if str(i).strip()]
    return "\n".join(lines[:limit]) if lines else "  (none)"


def _insight_context(pkg: InsightPackage) -> str:
    hp = pkg.hypothesis_package
    narrative = pkg.narrative
    insights = pkg.business_insights
    analytics = pkg.analytics_results
    root = pkg.root_cause_graph
    grounding = pkg.grounding_map

    parts: list[str] = []
    parts.append(f"HYPOTHESIS: {hp.headline or hp.hypothesis_statement}")
    if hp.hypothesis_statement:
        parts.append(f"Statement: {hp.hypothesis_statement}")
    if hp.mechanism_explanation:
        parts.append(f"Proposed mechanism: {hp.mechanism_explanation}")
    if hp.business_lens:
        parts.append(f"Business lens: {hp.business_lens}")

    if narrative:
        if narrative.executive_summary:
            parts.append(f"\nEXECUTIVE SUMMARY: {narrative.executive_summary}")
        if narrative.business_narrative:
            parts.append(f"NARRATIVE: {narrative.business_narrative}")
        if narrative.key_messages:
            parts.append("KEY MESSAGES:\n" + _bullet(narrative.key_messages))

    if analytics and analytics.methods_run:
        method_lines = []
        for m in analytics.methods_run[:8]:
            bits = [m.method]
            if getattr(m, "statistic", None) is not None:
                bits.append(f"stat={round(float(m.statistic), 3)}")
            if getattr(m, "p_value", None) is not None:
                bits.append(f"p={round(float(m.p_value), 4)}")
            note = (m.interpretation_notes or "").strip()
            method_lines.append(f"  - {', '.join(bits)} — {note[:200]}")
        parts.append("ANALYTICS RESULTS:\n" + ("\n".join(method_lines) or "  (none)"))

    if insights:
        if insights.findings:
            parts.append("FINDINGS:\n" + _bullet([f.statement for f in insights.findings]))
        if insights.risks:
            parts.append("RISKS:\n" + _bullet([r.description for r in insights.risks]))
        if insights.opportunities:
            parts.append("OPPORTUNITIES:\n" + _bullet([o.description for o in insights.opportunities]))
        if insights.strategic_recommendations:
            parts.append("RECOMMENDATIONS:\n" + _bullet([r.action for r in insights.strategic_recommendations]))

    if root:
        if root.edges:
            edge_lines = [f"  - {e.source} → {e.relationship_type} → {e.target}" for e in root.edges[:6]]
            parts.append("CAUSAL LINKS (evidence-backed):\n" + ("\n".join(edge_lines) or "  (none)"))
        if root.potential_mechanisms:
            parts.append("POTENTIAL MECHANISMS:\n" + _bullet(root.potential_mechanisms))

    if grounding and grounding.grounded:
        gm = [f"{g.construct_name} → {', '.join(g.columns)}" for g in grounding.grounded]
        parts.append("SHL GROUNDING (construct → real columns):\n" + _bullet(gm))

    return "\n".join(parts)


def build_research_messages(
    pkg: InsightPackage,
    framework_context: str,
    knowledge_excerpts: list[str] | None,
    message: str,
    history: list[dict] | None,
) -> LLMRequest:
    """Assemble the system + history + user messages for one chat turn.

    `framework_context` is a pre-rendered SHL-metric context string (from
    FrameworkRegistry.family_summary()/describe_for_prompt()); pass "" if
    unavailable. `knowledge_excerpts` are optional org-knowledge snippets.
    """
    org_id = pkg.hypothesis_package.organization_id or "the organization"
    knowledge_block = ""
    if knowledge_excerpts:
        knowledge_block = "\n\nORGANIZATION KNOWLEDGE:\n" + _bullet(knowledge_excerpts)

    framework_block = f"\n\nSHL ASSESSMENT FRAMEWORK / METRICS (what the data measures):\n{framework_context}" if framework_context else ""

    system = (
        "You are the Delphi Research Engine, an analytical assistant embedded in a single SHL people-analytics "
        "insight report. You help an executive reader understand THIS report and the SHL data behind it.\n\n"
        "Rules:\n"
        "- Answer ONLY using the insight context, the SHL framework, and the organization context provided below. "
        "Do not invent findings, numbers, metrics, or columns that are not present.\n"
        "- If the user asks something unrelated to this insight or to the organization's people-analytics data, "
        "politely reply that you can only discuss this specific insight report.\n"
        "- Be concise, precise, and professional. No emojis. Prefer plain, executive language.\n"
        "- When useful, ground statements in the specific finding, statistic, or SHL metric from the context.\n\n"
        f"ORGANIZATION: {org_id}\n\n"
        f"=== INSIGHT REPORT CONTEXT ===\n{_insight_context(pkg)}"
        f"{framework_block}{knowledge_block}"
    )

    messages: list[LLMMessage] = [LLMMessage(role="system", content=system)]
    for turn in (history or [])[-_MAX_HISTORY_TURNS:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append(LLMMessage(role=role, content=content))
    messages.append(LLMMessage(role="user", content=message))

    return LLMRequest(messages=messages, temperature=0.3, max_tokens=600)
