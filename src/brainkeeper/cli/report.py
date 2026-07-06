"""Render a self-contained, offline HTML report from a `VaultStats` snapshot.

Pure `VaultStats -> str`; no disk I/O (the caller in `cli/stats.py` writes the
file). No `<script>` tags anywhere: theming is CSS-only via
`prefers-color-scheme`, and there is no run-varying content (no clocks,
no randomness) so the same vault renders byte-identical output on the same
day.
"""

from __future__ import annotations

import html
from datetime import date

from ..core.stats import INBOX_ROT_DAYS, LAYER_KEYS, VaultStats

# ponytail: duplicated from cli/stats.py rather than imported, to avoid a
# stats.py <-> report.py circular import (stats.py imports render_report).
_LAYER_LABELS = {
    "inbox": "Inbox",
    "journal": "Journal",
    "projects": "Projects",
    "areas": "Areas",
    "brain": "Brain",
    "archive": "Archive",
}

_STYLE = """
:root {
  --bg: #ffffff;
  --fg: #1a1a1a;
  --muted: #666666;
  --tile-bg: #f2f2f2;
  --warn-bg: #fff3e0;
  --warn-fg: #b34700;
  --line-inbox: #e63946;
  --line-journal: #457b9d;
  --line-projects: #2a9d8f;
  --line-areas: #f4a261;
  --line-brain: #6a4c93;
  --line-archive: #8d99ae;
  --bar-fill: #457b9d;
  --heat-0: #ebedf0;
  --heat-1: #c6e48b;
  --heat-2: #7bc96f;
  --heat-3: #239a3b;
  --heat-4: #196127;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117;
    --fg: #e6edf3;
    --muted: #9aa4af;
    --tile-bg: #161b22;
    --warn-bg: #4d2600;
    --warn-fg: #ffb877;
    --line-inbox: #ff6b6b;
    --line-journal: #6ea8d8;
    --line-projects: #4fd1c5;
    --line-areas: #f6b76b;
    --line-brain: #b18cff;
    --line-archive: #b6bfc9;
    --bar-fill: #6ea8d8;
    --heat-0: #161b22;
    --heat-1: #0e4429;
    --heat-2: #006d32;
    --heat-3: #26a641;
    --heat-4: #39d353;
  }
}
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--fg); font-family: system-ui, sans-serif; margin: 0; }
main { max-width: 900px; margin: 0 auto; padding: 1.5rem; }
h1 { font-size: 1.4rem; }
h2 { font-size: 1.05rem; margin-bottom: 0.5rem; }
section { margin-top: 2rem; }
.empty { color: var(--muted); font-style: italic; }
.tiles { display: flex; gap: 1rem; flex-wrap: wrap; padding: 0; list-style: none; margin: 0; }
.tile { background: var(--tile-bg); border-radius: 8px; padding: 1rem 1.5rem; min-width: 8rem; }
.tile.warn { background: var(--warn-bg); color: var(--warn-fg); }
.tile-value { font-size: 2rem; font-weight: 700; }
.tile-label { font-size: 0.85rem; color: var(--muted); }
.tile.warn .tile-label { color: var(--warn-fg); }
.line-inbox, .line-journal, .line-projects, .line-areas, .line-brain, .line-archive {
  fill: none;
  stroke-width: 2;
}
.line-inbox { stroke: var(--line-inbox); background-color: var(--line-inbox); }
.line-journal { stroke: var(--line-journal); background-color: var(--line-journal); }
.line-projects { stroke: var(--line-projects); background-color: var(--line-projects); }
.line-areas { stroke: var(--line-areas); background-color: var(--line-areas); }
.line-brain { stroke: var(--line-brain); background-color: var(--line-brain); }
.line-archive { stroke: var(--line-archive); background-color: var(--line-archive); }
.vertex { fill: var(--fg); }
.legend { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem; font-size: 0.85rem; padding: 0; list-style: none; }
.legend-item { display: flex; align-items: center; gap: 0.35rem; }
.legend-swatch { width: 0.75rem; height: 0.75rem; border-radius: 2px; display: inline-block; }
.bar { fill: var(--bar-fill); }
.bar-label { fill: var(--fg); font-size: 0.8rem; }
.bar-value { fill: var(--fg); font-size: 0.8rem; }
.c0 { fill: var(--heat-0); }
.c1 { fill: var(--heat-1); }
.c2 { fill: var(--heat-2); }
.c3 { fill: var(--heat-3); }
.c4 { fill: var(--heat-4); }
.hm-legend { fill: var(--muted); font-size: 0.7rem; }
""".strip()


def render_report(stats: VaultStats) -> str:
    """Assemble the full self-contained HTML document for `stats`."""
    body = "".join(
        [
            "<h1>brainkeeper vault stats</h1>",
            _tiles_section(stats),
            _growth_section(stats),
            _bars_section(stats),
            _heatmap_section(stats),
        ]
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        "<title>brainkeeper vault stats</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n"
        f"<body><main>{body}</main></body>\n"
        "</html>\n"
    )


def _tiles_section(stats: VaultStats) -> str:
    age = stats.inbox_oldest_age_days
    if age is None:
        inbox_class, inbox_value, inbox_label = "tile", "OK", "Inbox (empty)"
    elif age > INBOX_ROT_DAYS:
        inbox_class, inbox_value, inbox_label = (
            "tile warn",
            str(age),
            "Inbox age (days)",
        )
    else:
        inbox_class, inbox_value, inbox_label = "tile", str(age), "Inbox age (days)"

    return (
        '<section class="tiles">'
        f'<div class="tile"><div class="tile-value">{stats.journal_streak}</div>'
        '<div class="tile-label">Journal streak</div></div>'
        f'<div class="{inbox_class}"><div class="tile-value">{html.escape(inbox_value)}</div>'
        f'<div class="tile-label">{html.escape(inbox_label)}</div></div>'
        f'<div class="tile"><div class="tile-value">{stats.total_notes}</div>'
        '<div class="tile-label">Total notes</div></div>'
        "</section>"
    )


_GROWTH_X0, _GROWTH_X1 = 40, 700
_GROWTH_Y0, _GROWTH_Y1 = 20, 220  # y0 = top (max value), y1 = bottom (0)


def _growth_section(stats: VaultStats) -> str:  # T2
    populated = [layer for layer in LAYER_KEYS if stats.growth_by_layer.get(layer)]
    if not populated:
        return (
            '<section class="growth"><h2>Growth by layer</h2>'
            + _empty_state("No growth data yet")
            + "</section>"
        )

    all_dates = [
        date.fromisoformat(d)
        for layer in populated
        for d, _ in stats.growth_by_layer[layer]
    ]
    min_date, max_date = min(all_dates), max(all_dates)
    span_days = (max_date - min_date).days
    maxval = max(stats.growth_by_layer[layer][-1][1] for layer in populated)

    def x_of(d: date) -> float:
        if span_days == 0:
            return _GROWTH_X1
        return _GROWTH_X0 + (d - min_date).days / span_days * (_GROWTH_X1 - _GROWTH_X0)

    def y_of(value: int) -> float:
        return _GROWTH_Y1 - (value / maxval) * (_GROWTH_Y1 - _GROWTH_Y0)

    lines = []
    legend_items = []
    for layer in populated:
        points = [
            (x_of(date.fromisoformat(d)), y_of(v))
            for d, v in stats.growth_by_layer[layer]
        ]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        lines.append(f'<polyline class="line-{layer}" points="{poly}"/>')
        lines.extend(
            f'<circle class="vertex" cx="{x:.1f}" cy="{y:.1f}" r="2.5"/>'
            for x, y in points
        )
        legend_items.append(
            '<li class="legend-item">'
            f'<span class="legend-swatch line-{layer}"></span>'
            f"{html.escape(_LAYER_LABELS[layer])}</li>"
        )

    svg = (
        '<svg viewBox="0 0 720 240" role="img" aria-label="Growth by layer">'
        + "".join(lines)
        + "</svg>"
    )
    legend = '<ul class="legend">' + "".join(legend_items) + "</ul>"
    return (
        '<section class="growth"><h2>Growth by layer</h2>' + svg + legend + "</section>"
    )


def _bars_section(stats: VaultStats) -> str:  # T2
    layer_rows = [
        (_LAYER_LABELS[layer], stats.notes_per_layer[layer]) for layer in LAYER_KEYS
    ]
    layer_chart = _bar_chart(layer_rows, "Notes per layer")

    if stats.top_tags:
        tag_chart = _bar_chart(list(stats.top_tags), "Top tags")
    else:
        tag_chart = _empty_state("No tags yet")

    return (
        '<section class="bars"><h2>Notes per layer</h2>'
        + layer_chart
        + "<h2>Top tags</h2>"
        + tag_chart
        + "</section>"
    )


_BAR_LABEL_W = 140
_BAR_TRACK_W = 440
_BAR_ROW_H = 24


def _bar_chart(rows: list[tuple[str, int]], aria_label: str) -> str:
    max_count = max((count for _, count in rows), default=0)
    height = _BAR_ROW_H * len(rows) + 8
    width = _BAR_LABEL_W + _BAR_TRACK_W + 50
    lines = []
    for i, (label, count) in enumerate(rows):
        y = 8 + i * _BAR_ROW_H
        bar_w = (count / max_count * _BAR_TRACK_W) if max_count else 0
        lines.append(
            f'<text class="bar-label" x="0" y="{y + 14}">{html.escape(label)}</text>'
            f'<rect class="bar" x="{_BAR_LABEL_W}" y="{y}" '
            f'width="{bar_w:.1f}" height="16"/>'
            f'<text class="bar-value" x="{_BAR_LABEL_W + bar_w + 6:.1f}" '
            f'y="{y + 14}">{count}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(aria_label)}">'
        + "".join(lines)
        + "</svg>"
    )


_HM_CELL, _HM_GAP = 11, 2
_HM_STEP = _HM_CELL + _HM_GAP
_HM_COLS, _HM_ROWS = 52, 7
_HM_GRID_W = _HM_COLS * _HM_STEP - _HM_GAP
_HM_GRID_H = _HM_ROWS * _HM_STEP - _HM_GAP
_HM_LEGEND_Y = _HM_GRID_H + 16


def _heatmap_section(stats: VaultStats) -> str:  # T3
    cells = []
    # ponytail: column-major i//7,i%7 fill (not Sunday-anchored GitHub weeks) —
    # simplest deterministic mapping that still guarantees today lands in the
    # final cell; true weekday alignment isn't required by the contract.
    for i, count in enumerate(stats.daily_created.values()):
        col, row = i // _HM_ROWS, i % _HM_ROWS
        level = min(count, 4)
        x, y = col * _HM_STEP, row * _HM_STEP
        cells.append(
            f'<rect class="c{level}" x="{x}" y="{y}" width="{_HM_CELL}" height="{_HM_CELL}"/>'
        )

    legend = "".join(
        f'<rect class="c{lvl}" x="{40 + lvl * 14}" y="{_HM_LEGEND_Y}" width="10" height="10"/>'
        for lvl in range(5)
    )
    svg = (
        f'<svg viewBox="0 0 {_HM_GRID_W} {_HM_LEGEND_Y + 14}" role="img" '
        'aria-label="Activity heatmap">'
        + "".join(cells)
        + f'<text class="hm-legend" x="0" y="{_HM_LEGEND_Y + 9}">Less</text>'
        + legend
        + f'<text class="hm-legend" x="{40 + 5 * 14 + 4}" y="{_HM_LEGEND_Y + 9}">More</text>'
        + "</svg>"
    )
    return (
        '<section class="heatmap"><h2>Activity (last 52 weeks)</h2>'
        + svg
        + "</section>"
    )


def _empty_state(label: str) -> str:
    return f'<p class="empty">{html.escape(label)}</p>'
