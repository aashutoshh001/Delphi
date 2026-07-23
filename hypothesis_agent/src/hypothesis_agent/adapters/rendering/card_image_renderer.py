"""Renders a small SVG 'insight card' image per hypothesis — used by the
frontend's Cards UI as the card image. Deliberately SVG text templating (no
Pillow/matplotlib dependency): stays consistent with `detail_page_renderer.py`'s
self-contained-markup approach and adds nothing to either package's dependency
footprint. Written once per hypothesis, filename keyed by the hypothesis's own
id — see `JsonHypothesisStore.save()`, which is the only caller.

The canvas is wide (800x450) so it fills a landscape card in Web mode, but the
frontend renders it with `object-fit: cover`, and Mobile mode's much narrower
card crops a large fraction off both left and right edges. All text is
therefore kept inside a centered SAFE_* zone well clear of those edges.

The headline is shown IN FULL (it is the card's title — there is no separate
text title beneath the image), so the font size is chosen dynamically: the
largest size at which the whole wrapped headline still fits the headline band.
Longer headlines simply render smaller rather than being truncated."""

from __future__ import annotations

import html
import textwrap

from hypothesis_agent.contracts.memory import HistoricalHypothesisRecord

_WIDTH = 800
_HEIGHT = 450
_SAFE_LEFT = 170
_SAFE_RIGHT = 630
_SAFE_WIDTH = _SAFE_RIGHT - _SAFE_LEFT

# Vertical band the headline may occupy — below the lens tag (~y=76), above the
# composite-signal label (~y=376).
_HEADLINE_TOP = 108
_HEADLINE_BOTTOM = 356
_HEADLINE_CENTER = (_HEADLINE_TOP + _HEADLINE_BOTTOM) / 2
_HEADLINE_BAND = _HEADLINE_BOTTOM - _HEADLINE_TOP

# Font sizes to try, largest first; the first that fits the full headline in
# the band (both per-line width and total height) wins. The smallest is used
# as-is if even it overflows (extremely long headline) — still complete, never
# truncated.
_FONT_CANDIDATES = (40, 36, 32, 28, 25, 22, 20, 18)
# Rough average glyph advance for a bold sans-serif, in ems — used only to
# estimate how many characters fit per line at a given font size.
_AVG_CHAR_EM = 0.54
_LINE_HEIGHT_FACTOR = 1.22


def _esc(value: object) -> str:
    return html.escape(str(value))


def _fit_headline(headline: str) -> tuple[list[str], int, float]:
    """Choose the largest font size whose wrapped headline fits the band.
    Returns (lines, font_size, line_height)."""
    headline = headline.strip() or "Untitled hypothesis"
    for font_size in _FONT_CANDIDATES:
        chars_per_line = max(8, int(_SAFE_WIDTH / (font_size * _AVG_CHAR_EM)))
        lines = textwrap.wrap(headline, width=chars_per_line)
        line_height = font_size * _LINE_HEIGHT_FACTOR
        if len(lines) * line_height <= _HEADLINE_BAND:
            return lines, font_size, line_height
    # Even the smallest font overflows — keep every line anyway (complete
    # headline is the priority), at the smallest size.
    font_size = _FONT_CANDIDATES[-1]
    chars_per_line = max(8, int(_SAFE_WIDTH / (font_size * _AVG_CHAR_EM)))
    lines = textwrap.wrap(headline, width=chars_per_line)
    return lines, font_size, font_size * _LINE_HEIGHT_FACTOR


def render_card_image(record: HistoricalHypothesisRecord) -> str:
    headline = record.headline or record.statement
    lens_label = (record.lens or "").replace("_", " ").upper()
    composite = record.scorecard.composite if record.scorecard else 0.0
    composite_pct = round(composite * 100)
    bar_max_width = 260
    bar_width = round(bar_max_width * composite)

    lines, font_size, line_height = _fit_headline(headline)
    # Vertically center the wrapped block on the band's midpoint.
    first_baseline = _HEADLINE_CENTER - (len(lines) - 1) * line_height / 2 + font_size * 0.34
    headline_tspans = "".join(
        f'<tspan x="{_SAFE_LEFT}" y="{first_baseline + i * line_height:.1f}">{_esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    tag_width = min(_SAFE_WIDTH, 34 + 10 * len(lens_label))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{_WIDTH}" height="{_HEIGHT}" viewBox="0 0 {_WIDTH} {_HEIGHT}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#12180f"/>
      <stop offset="100%" stop-color="#1d2b18"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="18%" r="70%">
      <stop offset="0%" stop-color="#78d64b" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#78d64b" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{_WIDTH}" height="{_HEIGHT}" fill="url(#bg)"/>
  <rect width="{_WIDTH}" height="{_HEIGHT}" fill="url(#glow)"/>
  <circle cx="60" cy="420" r="140" fill="none" stroke="#78d64b" stroke-opacity="0.12" stroke-width="1.5"/>
  <circle cx="740" cy="30" r="140" fill="none" stroke="#78d64b" stroke-opacity="0.12" stroke-width="1.5"/>

  <rect x="{_SAFE_LEFT}" y="46" width="{tag_width}" height="30" rx="15" fill="#78d64b"/>
  <text x="{_SAFE_LEFT + tag_width / 2}" y="66" text-anchor="middle"
        font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13" font-weight="700"
        letter-spacing="0.6" fill="#14320a">{_esc(lens_label)}</text>

  <text font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="{font_size}" font-weight="700"
        fill="#f4fbf1">{headline_tspans}</text>

  <text x="{_SAFE_LEFT}" y="376" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13"
        letter-spacing="0.4" fill="#9fb89a">COMPOSITE SIGNAL</text>
  <rect x="{_SAFE_LEFT}" y="388" width="{bar_max_width}" height="8" rx="4" fill="#2c3a27"/>
  <rect x="{_SAFE_LEFT}" y="388" width="{bar_width}" height="8" rx="4" fill="#78d64b"/>
  <text x="{_SAFE_LEFT + bar_max_width + 16}" y="396" font-family="Segoe UI, Helvetica, Arial, sans-serif"
        font-size="13" font-weight="700" fill="#78d64b">{composite_pct}%</text>

  <text x="{_SAFE_RIGHT}" y="{_HEIGHT - 30}" text-anchor="end" font-family="Segoe UI, Helvetica, Arial, sans-serif"
        font-size="13" font-weight="700" letter-spacing="0.4" fill="#5c7256">DELPHI</text>
</svg>
"""
