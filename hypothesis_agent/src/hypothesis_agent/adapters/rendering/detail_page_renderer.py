"""Renders the static 'read more' detail page for one stored hypothesis.
Self-contained HTML (inline CSS, no external requests) so it works served
from a plain static file server alongside the rest of the Delphi site."""

from __future__ import annotations

import html

from hypothesis_agent.contracts.hypothesis import EVALUATION_DIMENSIONS
from hypothesis_agent.contracts.memory import HistoricalHypothesisRecord

_DIMENSION_LABELS = {
    "business_value": "Business value",
    "novelty": "Novelty",
    "depth": "Depth",
    "actionability": "Actionability",
    "strategic_importance": "Strategic importance",
    "feasibility": "Feasibility",
    "organizational_impact": "Organizational impact",
    "expected_insight": "Expected insight",
    "confidence": "Confidence",
    "future_extensibility": "Future extensibility",
}


def _esc(value: object) -> str:
    return html.escape(str(value))


def _dimension_bars(record: HistoricalHypothesisRecord) -> str:
    if record.scorecard is None:
        return "<p>Not yet scored.</p>"
    rows = []
    for dim in EVALUATION_DIMENSIONS:
        value = getattr(record.scorecard, dim)
        pct = round(value * 100)
        note = record.scorecard.dimension_notes.get(dim, "")
        row = (
            f'<div class="dim-row">'
            f'<span class="dim-label">{_esc(_DIMENSION_LABELS[dim])}</span>'
            f'<div class="dim-track"><div class="dim-fill" style="width:{pct}%"></div></div>'
            f'<span class="dim-value">{value:.2f}</span>'
            f'</div>'
        )
        if note:
            row += f'<p class="dim-note">{_esc(note)}</p>'
        rows.append(row)
    composite_pct = round(record.scorecard.composite * 100)
    header = (
        f'<div class="composite">Composite score: '
        f'<strong>{record.scorecard.composite:.3f}</strong> ({composite_pct}%)</div>'
    )
    return header + "\n".join(rows)


def _critique_section(record: HistoricalHypothesisRecord) -> str:
    if record.critique is None:
        return "<p>Not yet critiqued.</p>"
    c = record.critique
    flags = []
    if c.is_obvious:
        flags.append("Flagged as obvious")
    if c.similar_to_prior:
        flags.append("Flagged as similar to a prior hypothesis")
    if not c.creates_actionable_decision:
        flags.append("Does not clearly create an actionable decision")
    if not c.reveals_hidden_mechanism:
        flags.append("Does not clearly reveal a hidden mechanism")
    flags_html = "".join(f"<li>{_esc(f)}</li>" for f in flags) or "<li>No red flags raised.</li>"
    issues_html = "".join(f"<li>{_esc(i)}</li>" for i in c.issues) or "<li>None recorded.</li>"
    suggestions_html = "".join(f"<li>{_esc(s)}</li>" for s in c.suggested_improvements) or "<li>None.</li>"
    return (
        f'<h3>Flags</h3><ul>{flags_html}</ul>'
        f'<h3>Issues raised</h3><ul>{issues_html}</ul>'
        f'<h3>Suggested improvements</h3><ul>{suggestions_html}</ul>'
    )


def render_detail_page(record: HistoricalHypothesisRecord) -> str:
    constructs_html = "".join(f'<span class="chip">{_esc(c)}</span>' for c in record.target_constructs)
    search_stats_html = ""
    if record.search_stats is not None:
        s = record.search_stats
        search_stats_html = (
            f"<p>Iterations run: {s.iterations_run} &middot; "
            f"Candidates generated: {s.candidates_generated} &middot; "
            f"Candidates discarded: {s.candidates_discarded} &middot; "
            f"Lenses explored: {_esc(', '.join(s.lenses_explored))} &middot; "
            f"Diversity score: {s.diversity_score:.2f} &middot; "
            f"Termination reason: {_esc(s.termination_reason)}</p>"
        )

    headline = record.headline or record.statement
    summary = record.summary or record.mechanism

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(headline[:70])} — Delphi Hypothesis</title>
<style>
  :root {{ --green: #78D64B; --grey: #4A4A4A; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2.5rem 1.5rem; background: #fafafa; color: var(--grey);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.55;
  }}
  main {{ max-width: 720px; margin: 0 auto; }}
  .lens-tag {{
    display: inline-block; background: var(--green); color: #fff;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
    text-transform: uppercase; padding: 0.25rem 0.6rem; border-radius: 999px;
    margin-bottom: 1rem;
  }}
  h1 {{ font-size: 1.75rem; line-height: 1.3; margin: 0 0 0.6rem; color: #191919; font-weight: 750; }}
  .subtitle {{ font-size: 1.05rem; color: #555; margin: 0 0 1rem; }}
  h2 {{ font-size: 1.05rem; margin-top: 2rem; color: #222; }}
  h3 {{ font-size: 0.9rem; margin: 1rem 0 0.35rem; color: #333; }}
  .statement, .mechanism {{ font-size: 1rem; }}
  .statement {{
    background: #fff; border: 1px solid var(--border, #e6e6e6); border-left: 3px solid var(--green);
    padding: 0.9rem 1.1rem; border-radius: 6px; font-weight: 500;
  }}
  .meta {{ font-size: 0.85rem; color: #777; margin-bottom: 1.5rem; }}
  .chip {{
    display: inline-block; background: #eef; border: 1px solid #dde;
    font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 6px;
    margin: 0 0.35rem 0.35rem 0;
  }}
  .composite {{ font-size: 1rem; margin-bottom: 1rem; }}
  .dim-row {{ display: flex; align-items: center; gap: 0.6rem; margin: 0.3rem 0; }}
  .dim-label {{ width: 170px; font-size: 0.85rem; flex-shrink: 0; }}
  .dim-track {{ flex: 1; background: #e6e6e6; border-radius: 4px; height: 8px; overflow: hidden; }}
  .dim-fill {{ background: var(--green); height: 100%; }}
  .dim-value {{ width: 40px; text-align: right; font-size: 0.85rem; font-variant-numeric: tabular-nums; }}
  .dim-note {{ font-size: 0.78rem; color: #888; margin: 0 0 0.4rem 182px; }}
  ul {{ margin: 0.25rem 0; padding-left: 1.3rem; font-size: 0.9rem; }}
  a.back {{ font-size: 0.85rem; color: var(--grey); text-decoration: none; }}
  a.back:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<main>
  <a class="back" href="../../index.html">&larr; Back to feed</a>
  <div class="lens-tag">{_esc(record.lens)}</div>
  <h1>{_esc(headline)}</h1>
  <p class="subtitle">{_esc(summary)}</p>
  <div class="meta">Organization: {_esc(record.organization_id or 'unknown')} &middot; Generated: {_esc(record.created_at.isoformat())}</div>

  <h2>The hypothesis</h2>
  <p class="statement">{_esc(record.statement)}</p>

  <h2>Hidden mechanism</h2>
  <p class="mechanism">{_esc(record.mechanism)}</p>

  <h2>Target constructs</h2>
  <div>{constructs_html or '<em>none recorded</em>'}</div>

  <h2>Evaluation</h2>
  {_dimension_bars(record)}

  <h2>Internal critique</h2>
  {_critique_section(record)}

  <h2>Search statistics</h2>
  {search_stats_html or '<p>Not recorded.</p>'}
</main>
</body>
</html>
"""
