from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import HypothesisCandidate


def best_of(archive: list[HypothesisCandidate]) -> HypothesisCandidate | None:
    """Best *viable* candidate — rejected candidates (discarded for being
    weak or a near-duplicate) are never eligible, however high their score."""
    scored = [c for c in archive if c.scorecard is not None and c.status != "rejected"]
    if not scored:
        return None
    return max(scored, key=lambda c: c.composite_score())


def diversity_score(archive: list[HypothesisCandidate]) -> float:
    if not archive:
        return 0.0
    distinct_lenses = len({c.lens for c in archive})
    return distinct_lenses / len(archive)


def explored_lens_summary(archive: list[HypothesisCandidate]) -> str:
    if not archive:
        return "(none yet)"
    counts: dict[str, int] = {}
    for c in archive:
        counts[c.lens] = counts.get(c.lens, 0) + 1
    return ", ".join(f"{lens}: {count}" for lens, count in sorted(counts.items()))
