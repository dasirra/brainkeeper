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
/* "Terminal dashboard" theme: dark-first, monospaced, bordered panels.
   Light mode is a deliberate light-on-paper variant, not an auto flip. */
:root {
  --fg: #161a17; --fg-2: #565d55; --muted: #7c8378; --bg: #f5f6f4; --panel: #ffffff;
  --border: #d6dbd2; --grid: #e6e9e2; --accent: #1f8a3b;
  --warn-bg: #fbeecf; --warn-fg: #8a5a10; --bar-fill: #1f8a3b;
  --line-inbox: #e34948; --line-journal: #2a78d6; --line-projects: #1baf7a;
  --line-areas: #eb6834; --line-brain: #4a3aa7; --line-archive: #6b7280;
  --heat-0: #e6e9e2; --heat-1: #bfe3a3; --heat-2: #78c46b; --heat-3: #2f9d3c; --heat-4: #186226;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fg: #d7ddd4; --fg-2: #98a094; --muted: #6f766c; --bg: #0a0d0c; --panel: #10140f;
    --border: #20261f; --grid: #181d17; --accent: #3fb950;
    --warn-bg: #33280f; --warn-fg: #e3b657; --bar-fill: #3fb950;
    --line-inbox: #e66767; --line-journal: #3987e5; --line-projects: #199e70;
    --line-areas: #d95926; --line-brain: #9085e9; --line-archive: #9aa4b2;
    --heat-0: #12160f; --heat-1: #0f3d22; --heat-2: #1a6b32; --heat-3: #2ea043; --heat-4: #48d364;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font-size: 14px;
  font-family: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace; }
main { max-width: 880px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
svg { max-width: 100%; height: auto; display: block; }
h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: 0.02em; text-transform: uppercase; margin: 0; }
h1::before { content: "> "; color: var(--accent); }
main > h1 { border-bottom: 1px dashed var(--border); padding-bottom: 1.5rem; margin-bottom: 2.5rem; }
h2 { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.13em; color: var(--muted); margin: 0 0 0.95rem; }
h2::before { content: "# "; color: var(--accent); opacity: 0.7; }
h2:not(:first-of-type) { margin-top: 2.4rem; }
section { margin-top: 1.5rem; border: 1px solid var(--border); border-radius: 2px;
  padding: 1.35rem 1.55rem; background: var(--panel); }
main > h1 + section { margin-top: 0; }
.empty { color: var(--muted); font-style: italic; }
/* top stat tiles: bordered cells, generous padding so numbers clear the panel edge */
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 0; list-style: none; margin: 0; padding: 0; }
.tile { padding: 1.25rem 1.75rem; border-left: 2px solid var(--border); }
.tile:first-child { border-left: none; }
.tile-value { font-size: 2rem; font-weight: 700; line-height: 1;
  font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.tile-label { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.11em;
  color: var(--muted); margin-top: 0.5rem; }
.tile.warn { background: var(--warn-bg); }
.tile.warn .tile-value, .tile.warn .tile-label { color: var(--warn-fg); }
/* growth */
.growth { position: relative; }
.growth-header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 0.9rem; }
.growth-header h2 { margin: 0; }
.toggle-btn { font: inherit; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
  background: transparent; color: var(--accent); border: 1px solid var(--border); border-radius: 2px;
  padding: 0.3rem 0.7rem; cursor: pointer; }
.toggle-btn::before { content: "["; margin-right: 0.35em; color: var(--muted); }
.toggle-btn::after { content: "]"; margin-left: 0.35em; color: var(--muted); }
.toggle-btn:hover { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }
.axis { stroke: var(--border); stroke-width: 1; }
.axis-label { fill: var(--muted); font-size: 0.7rem; font-family: inherit; }
.line-inbox, .line-journal, .line-projects, .line-areas, .line-brain, .line-archive {
  fill: none;
  stroke-width: 2;
}
.line-inbox { stroke: var(--line-inbox); }
.line-journal { stroke: var(--line-journal); }
.line-projects { stroke: var(--line-projects); }
.line-areas { stroke: var(--line-areas); }
.line-brain { stroke: var(--line-brain); }
.line-archive { stroke: var(--line-archive); }
.dot-inbox { fill: var(--line-inbox); }
.dot-journal { fill: var(--line-journal); }
.dot-projects { fill: var(--line-projects); }
.dot-areas { fill: var(--line-areas); }
.dot-brain { fill: var(--line-brain); }
.dot-archive { fill: var(--line-archive); }
.hover-strip { fill: transparent; }
.hover-strip:hover { fill: var(--fg); fill-opacity: 0.06; }
svg g[hidden] { display: none; }
.legend { display: flex; gap: 1.1rem; flex-wrap: wrap; list-style: none; margin: 0.9rem 0 0; padding: 0;
  font-size: 0.74rem; color: var(--fg-2); }
.legend-item { display: flex; align-items: center; gap: 0.4rem; }
.legend-swatch { width: 0.65rem; height: 0.65rem; border-radius: 1px; display: inline-block; }
.legend-swatch.line-inbox { background-color: var(--line-inbox); }
.legend-swatch.line-journal { background-color: var(--line-journal); }
.legend-swatch.line-projects { background-color: var(--line-projects); }
.legend-swatch.line-areas { background-color: var(--line-areas); }
.legend-swatch.line-brain { background-color: var(--line-brain); }
.legend-swatch.line-archive { background-color: var(--line-archive); }
.tooltip { position: absolute; background: var(--bg); color: var(--fg); border: 1px solid var(--accent);
  border-radius: 2px; padding: 0.45rem 0.6rem; font-size: 0.72rem; line-height: 1.55;
  pointer-events: none; white-space: nowrap; z-index: 2; box-shadow: 0 0 0 1px var(--border); }
/* notes per layer: one stacked segmented bar + tabular legend */
.stack { display: flex; width: 100%; height: 34px; gap: 2px; padding: 2px; background: var(--grid);
  border: 1px solid var(--border); border-radius: 2px; overflow: hidden; }
.seg { flex-basis: 0; height: 100%; border-radius: 1px; min-width: 2px; }
.seg-inbox { background: var(--line-inbox); }
.seg-journal { background: var(--line-journal); }
.seg-projects { background: var(--line-projects); }
.seg-areas { background: var(--line-areas); }
.seg-brain { background: var(--line-brain); }
.seg-archive { background: var(--line-archive); }
.stack-legend { list-style: none; margin: 0.95rem 0 0; padding: 0;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0 1.6rem; }
.stack-legend li { display: grid; grid-template-columns: auto 1fr auto auto; align-items: center;
  gap: 0.6rem; padding: 0.32rem 0; border-bottom: 1px solid var(--grid); font-size: 0.8rem; }
.seg-swatch { width: 0.6rem; height: 0.6rem; border-radius: 1px; display: inline-block; }
.stack-name { color: var(--fg); }
.stack-count { font-variant-numeric: tabular-nums; font-weight: 700; text-align: right; }
.stack-pct { font-variant-numeric: tabular-nums; color: var(--muted); text-align: right; min-width: 3.4rem; }
/* top tags */
.bar { fill: var(--bar-fill); rx: 1px; }
.bar-label { fill: var(--fg-2); font-size: 0.8rem; font-family: inherit; }
.bar-value { fill: var(--fg); font-size: 0.8rem; font-weight: 700;
  font-variant-numeric: tabular-nums; font-family: inherit; }
/* heatmap */
.heatmap rect { rx: 1px; ry: 1px; }
.c0 { fill: var(--heat-0); }
.c1 { fill: var(--heat-1); }
.c2 { fill: var(--heat-2); }
.c3 { fill: var(--heat-3); }
.c4 { fill: var(--heat-4); }
.hm-legend { fill: var(--muted); font-size: 0.7rem; font-family: inherit; }
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
    # notes per layer as one stacked bar (share of total) + a tabular legend.
    # zero-count layers contribute no segment but still get a legend row.
    total = sum(stats.notes_per_layer.values())
    segments = "".join(
        f'<span class="seg seg-{layer}" style="flex-grow:{stats.notes_per_layer[layer]}"></span>'
        for layer in LAYER_KEYS
        if stats.notes_per_layer[layer] > 0
    )
    if total:
        stack = f'<div class="stack" role="img" aria-label="Notes per layer">{segments}</div>'
    else:
        stack = _empty_state("No notes yet")

    def legend_row(layer: str) -> str:
        count = stats.notes_per_layer[layer]
        pct = (count / total * 100) if total else 0.0
        return (
            f'<li><span class="seg-swatch seg-{layer}"></span>'
            f'<span class="stack-name">{html.escape(LAYER_LABELS[layer])}</span>'
            f'<span class="stack-count">{count}</span>'
            f'<span class="stack-pct">{pct:.1f}%</span></li>'
        )

    legend = (
        '<ul class="stack-legend">'
        + "".join(legend_row(layer) for layer in LAYER_KEYS)
        + "</ul>"
    )

    if stats.top_tags:
        tag_chart = _bar_chart(list(stats.top_tags), "Top tags")
    else:
        tag_chart = _empty_state("No tags yet")

    return (
        '<section class="bars"><h2>Notes per layer</h2>'
        + stack
        + legend
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
