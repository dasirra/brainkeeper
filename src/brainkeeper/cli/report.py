"""Render a self-contained, offline HTML report from a `VaultStats` snapshot.

Pure `VaultStats -> str`; no disk I/O (the caller in `cli/stats.py` writes the
file). Fully self-contained: zero external requests, theming is CSS-only via
`prefers-color-scheme`, and the only script is a small inline block driving
the growth chart's hover tooltip and cumulative/daily toggle. There is no
run-varying content (no clocks, no randomness) so the same vault renders
byte-identical output on the same day.
"""

from __future__ import annotations

import html
from datetime import date, timedelta

from ..core.stats import LAYER_KEYS, LAYER_LABELS, VaultStats, inbox_state

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
.dot-inbox { fill: var(--line-inbox); }
.dot-journal { fill: var(--line-journal); }
.dot-projects { fill: var(--line-projects); }
.dot-areas { fill: var(--line-areas); }
.dot-brain { fill: var(--line-brain); }
.dot-archive { fill: var(--line-archive); }
.growth { position: relative; }
.growth-header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
.toggle-btn { background: var(--tile-bg); color: var(--fg); border: 1px solid var(--muted); border-radius: 6px; padding: 0.3rem 0.8rem; font: inherit; font-size: 0.8rem; cursor: pointer; }
.toggle-btn:hover { border-color: var(--fg); }
.tooltip { position: absolute; background: var(--tile-bg); color: var(--fg); border: 1px solid var(--muted); border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.8rem; pointer-events: none; white-space: nowrap; z-index: 1; }
.hover-strip { fill: transparent; }
.hover-strip:hover { fill: var(--fg); fill-opacity: 0.05; }
svg g[hidden] { display: none; }
.axis { stroke: var(--muted); stroke-width: 1; }
.axis-label { fill: var(--muted); font-size: 0.7rem; }
.tile.accent-inbox { border-left: 4px solid var(--line-inbox); }
.tile.accent-journal { border-left: 4px solid var(--line-journal); }
.tile.accent-projects { border-left: 4px solid var(--line-projects); }
.tile.accent-areas { border-left: 4px solid var(--line-areas); }
.tile.accent-brain { border-left: 4px solid var(--line-brain); }
.tile.accent-archive { border-left: 4px solid var(--line-archive); }
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


_SCRIPT = """
(function () {
  "use strict";
  var btn = document.getElementById("growth-toggle");
  var tip = document.getElementById("growth-tip");
  var cum = document.getElementById("growth-cum");
  var day = document.getElementById("growth-day");
  var section = document.getElementById("growth-section");
  if (!btn || !tip || !cum || !day || !section) { return; }
  var mode = "cum";
  btn.addEventListener("click", function () {
    mode = mode === "cum" ? "day" : "cum";
    cum.toggleAttribute("hidden", mode !== "cum");
    day.toggleAttribute("hidden", mode !== "day");
    btn.textContent = mode === "cum" ? "Daily" : "Cumulative";
    tip.hidden = true;
  });
  Array.prototype.forEach.call(
    document.querySelectorAll(".hover-strip"),
    function (strip) {
      strip.addEventListener("mousemove", function (ev) {
        var rows = strip.getAttribute(mode === "cum" ? "data-cum" : "data-day");
        tip.innerHTML =
          "<strong>" + strip.getAttribute("data-date") + "</strong><br>" +
          rows.split("|").join("<br>");
        tip.hidden = false;
        var box = section.getBoundingClientRect();
        tip.style.left = ev.clientX - box.left + 14 + "px";
        tip.style.top = ev.clientY - box.top - 10 + "px";
      });
      strip.addEventListener("mouseleave", function () { tip.hidden = true; });
    }
  );
})();
""".strip()


def render_report(stats: VaultStats) -> str:
    """Assemble the full self-contained HTML document for `stats`."""
    body = "".join(
        [
            "<h1>Brainkeeper Vault Stats</h1>",
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
        "<title>Brainkeeper Vault Stats</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n"
        f"<body><main>{body}</main>\n"
        f"<script>{_SCRIPT}</script>\n"
        "</body>\n"
        "</html>\n"
    )


def _tiles_section(stats: VaultStats) -> str:
    age = stats.inbox_oldest_age_days
    state = inbox_state(age)
    if state == "empty":
        inbox_class, inbox_value, inbox_label = "tile", "OK", "Inbox (empty)"
    else:
        inbox_class = "tile warn" if state == "rotting" else "tile"
        inbox_value, inbox_label = str(age), "Inbox age (days)"

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

    parsed = {
        layer: [(date.fromisoformat(d), v) for d, v in stats.growth_by_layer[layer]]
        for layer in populated
    }
    # x domain: from the first data point through the end of the daily window
    # (today), one point per calendar day
    min_date = min(points[0][0] for points in parsed.values())
    end_date = max(points[-1][0] for points in parsed.values())
    if stats.daily_created:
        last_daily = date.fromisoformat(next(reversed(stats.daily_created)))
        end_date = max(end_date, last_daily)
    span_days = (end_date - min_date).days
    domain = [min_date + timedelta(days=i) for i in range(span_days + 1)]
    cum_max = max(parsed[layer][-1][1] for layer in populated)

    # dense per-day series per layer, starting at the layer's own first note:
    # cumulative carries forward, daily is the created count that day
    day_at: dict[str, dict[date, int]] = {}
    cum_at: dict[str, dict[date, int]] = {}
    first_at: dict[str, date] = {}
    for layer in populated:
        events = dict(parsed[layer])
        first_at[layer] = parsed[layer][0][0]
        prev = 0
        day_at[layer] = {}
        for d, v in parsed[layer]:
            day_at[layer][d] = v - prev
            prev = v
        running = 0
        cum_at[layer] = {}
        for d in domain:
            running = events.get(d, running)
            cum_at[layer][d] = running
    day_max = max(max(day_at[layer].values()) for layer in populated)

    def x_of(d: date) -> float:
        if span_days == 0:
            return _GROWTH_X1
        return _GROWTH_X0 + (d - min_date).days / span_days * (_GROWTH_X1 - _GROWTH_X0)

    def y_of(value: int, maxval: int) -> float:
        return _GROWTH_Y1 - (value / maxval) * (_GROWTH_Y1 - _GROWTH_Y0)

    def chart_group(group_id: str, maxval: int, hidden: bool) -> str:
        parts = [f'<g id="{group_id}"' + (" hidden>" if hidden else ">")]
        for tick in (0, maxval // 2, maxval) if maxval > 1 else (0, maxval):
            parts.append(
                f'<text class="axis-label" text-anchor="end" x="{_GROWTH_X0 - 6}" '
                f'y="{y_of(tick, maxval) + 3:.1f}">{tick}</text>'
            )
        for layer in populated:
            days = [d for d in domain if d >= first_at[layer]]
            if group_id == "growth-cum":
                pts = [(x_of(d), y_of(cum_at[layer][d], maxval)) for d in days]
            else:
                pts = [(x_of(d), y_of(day_at[layer].get(d, 0), maxval)) for d in days]
            poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            parts.append(f'<polyline class="line-{layer}" points="{poly}"/>')
            # dots only on days with created notes; every day has a line point
            parts.extend(
                f'<circle class="dot-{layer}" cx="{x_of(d):.1f}" '
                f'cy="{y_of(v if group_id == "growth-cum" else day_at[layer][d], maxval):.1f}" '
                'r="1.5"/>'
                for d, v in parsed[layer]
            )
        parts.append("</g>")
        return "".join(parts)

    # invisible per-day strips carrying the tooltip data for both modes
    strips = []
    half = (
        (_GROWTH_X1 - _GROWTH_X0) / span_days / 2
        if span_days
        else (_GROWTH_X1 - _GROWTH_X0) / 2
    )
    for d in domain:
        x = x_of(d)
        left = max(x - half, _GROWTH_X0)
        right = min(x + half, _GROWTH_X1)
        cum_rows = "|".join(
            f"{LAYER_LABELS[layer]}: {cum_at[layer][d]}" for layer in populated
        )
        day_rows = "|".join(
            f"{LAYER_LABELS[layer]}: {day_at[layer].get(d, 0)}" for layer in populated
        )
        strips.append(
            f'<rect class="hover-strip" x="{left:.1f}" y="{_GROWTH_Y0}" '
            f'width="{max(right - left, 1):.1f}" height="{_GROWTH_Y1 - _GROWTH_Y0}" '
            f'data-date="{d.isoformat()}" data-cum="{cum_rows}" data-day="{day_rows}"/>'
        )

    x_ticks = sorted({min_date, domain[len(domain) // 2], end_date})
    # anchor edge labels inward so they stay inside the viewBox
    anchors = {min_date: "start", end_date: "end"}
    x_labels = "".join(
        f'<text class="axis-label" text-anchor="{anchors.get(d, "middle")}" '
        f'x="{x_of(d):.1f}" y="{_GROWTH_Y1 + 18}">{d.isoformat()}</text>'
        for d in x_ticks
    )
    axes = (
        f'<line class="axis" x1="{_GROWTH_X0}" y1="{_GROWTH_Y1}" '
        f'x2="{_GROWTH_X1}" y2="{_GROWTH_Y1}"/>'
        f'<line class="axis" x1="{_GROWTH_X0}" y1="{_GROWTH_Y0}" '
        f'x2="{_GROWTH_X0}" y2="{_GROWTH_Y1}"/>'
    )

    svg = (
        '<svg viewBox="0 0 720 250" role="img" aria-label="Growth by layer">'
        + axes
        + x_labels
        + chart_group("growth-cum", cum_max, hidden=False)
        + chart_group("growth-day", day_max, hidden=True)
        + "".join(strips)
        + "</svg>"
    )
    legend_items = [
        '<li class="legend-item">'
        f'<span class="legend-swatch line-{layer}"></span>'
        f"{html.escape(LAYER_LABELS[layer])}</li>"
        for layer in populated
    ]
    legend = '<ul class="legend">' + "".join(legend_items) + "</ul>"
    header = (
        '<div class="growth-header"><h2>Growth by layer</h2>'
        '<button type="button" class="toggle-btn" id="growth-toggle">Daily</button>'
        "</div>"
    )
    tooltip = '<div class="tooltip" id="growth-tip" hidden></div>'
    return (
        '<section class="growth" id="growth-section">'
        + header
        + svg
        + legend
        + tooltip
        + "</section>"
    )


def _bars_section(stats: VaultStats) -> str:  # T2
    layer_tiles = "".join(
        f'<div class="tile accent-{layer}">'
        f'<div class="tile-value">{stats.notes_per_layer[layer]}</div>'
        f'<div class="tile-label">{html.escape(LAYER_LABELS[layer])}</div></div>'
        for layer in LAYER_KEYS
    )

    if stats.top_tags:
        tag_chart = _bar_chart(list(stats.top_tags), "Top tags")
    else:
        tag_chart = _empty_state("No tags yet")

    return (
        '<section class="bars"><h2>Notes per layer</h2>'
        + f'<div class="tiles">{layer_tiles}</div>'
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
    # ponytail: column-major i//7,i%7 fill (not Sunday-anchored GitHub weeks):
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
