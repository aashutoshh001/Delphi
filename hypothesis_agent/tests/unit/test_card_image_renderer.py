from hypothesis_agent.adapters.rendering.card_image_renderer import render_card_image
from hypothesis_agent.contracts.hypothesis import EvaluationScorecard
from hypothesis_agent.contracts.memory import HistoricalHypothesisRecord


def _record(**overrides) -> HistoricalHypothesisRecord:
    defaults = dict(
        organization_id="org-1",
        headline="A few engineers may be carrying too much of Acme Labs' leadership load",
        statement="High performers show elevated burnout.",
        mechanism="Sustained overperformance without recovery time erodes resilience.",
        lens="skill_concentration",
        target_constructs=["burnout", "performance"],
        scorecard=EvaluationScorecard(business_value=0.8, composite=0.742),
    )
    defaults.update(overrides)
    return HistoricalHypothesisRecord(**defaults)


def test_render_card_image_is_valid_svg_with_expected_content():
    svg = render_card_image(_record())
    assert svg.strip().startswith("<svg")
    assert svg.strip().endswith("</svg>")
    assert "SKILL CONCENTRATION" in svg


def test_render_card_image_does_not_show_composite_signal():
    svg = render_card_image(_record())
    assert "COMPOSITE SIGNAL" not in svg
    assert "74%" not in svg  # composite value must not appear on the card


def test_render_card_image_escapes_headline_html():
    svg = render_card_image(_record(headline="Attrition risk <script>alert(1)</script> & burnout"))
    assert "<script>" not in svg
    assert "&amp;" in svg


def test_render_card_image_shows_complete_headline_without_truncation():
    # Every word must appear (headline is never cut off / ellipsised), and the
    # font is shrunk instead — a long headline wraps into more lines.
    words = [f"word{i}" for i in range(24)]
    svg = render_card_image(_record(headline=" ".join(words)))
    for word in words:
        assert word in svg
    assert "…" not in svg


def test_render_card_image_shrinks_font_for_longer_headlines():
    short = render_card_image(_record(headline="Short headline"))
    long = render_card_image(_record(headline=" ".join(f"word{i}" for i in range(24))))

    def font_size(svg: str) -> int:
        # the headline <text> is the one carrying font-weight="700" with the
        # dynamic size (the label texts are all fixed at 13)
        import re

        sizes = [int(m) for m in re.findall(r'font-size="(\d+)"', svg)]
        return max(sizes)  # headline uses the largest size on the card

    assert font_size(long) < font_size(short)


def test_render_card_image_handles_missing_scorecard():
    # Scorecard is no longer rendered on the card, but a missing one must still
    # not break rendering.
    svg = render_card_image(_record(scorecard=None))
    assert svg.strip().startswith("<svg")
    assert svg.strip().endswith("</svg>")
