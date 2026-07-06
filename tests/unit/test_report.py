"""Tests for `stats --html` report shell: wiring, tiles, empty states (#32)."""

import json
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

import pytest
from freezegun import freeze_time

from brainkeeper.cli import main
from conftest import write_note as _write_note

_STATS_TODAY = date(2025, 6, 15)


@pytest.fixture
def frozen_today():
    """Pin `date.today()` for tests whose fixtures are built from relative dates."""
    with freeze_time(_STATS_TODAY.isoformat()):
        yield _STATS_TODAY


def _init_vault(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    return tmp_path / ".brainkeeper" / "vault"


def _tiles_section(html_text: str) -> str:
    match = re.search(r'<section class="tiles">.*?</section>', html_text, re.S)
    assert match, "tiles section not found"
    return match.group()


# --- C1/C2: file target + stdout path -----------------------------------------


def test_html_default_name_writes_to_cwd(tmp_path: Path, monkeypatch, capsys):
    _init_vault(tmp_path, monkeypatch)
    capsys.readouterr()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    exit_code = main(["stats", "--html"])
    out = capsys.readouterr().out
    report = cwd / "brainkeeper-stats.html"
    assert exit_code == 0
    assert report.is_file()
    assert "brainkeeper-stats.html" in out


def test_html_custom_path_creates_subdirs_and_skips_default(
    tmp_path: Path, monkeypatch, capsys
):
    _init_vault(tmp_path, monkeypatch)
    capsys.readouterr()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    target = tmp_path / "out" / "sub" / "report.html"

    exit_code = main(["stats", "--html", str(target)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert target.is_file()
    assert str(target) in out
    assert not (cwd / "brainkeeper-stats.html").exists()


# --- C3: no browser launch, static + no subprocess ------------------------------


def test_no_browser_launch_in_source():
    import brainkeeper.cli.report as report_mod
    import brainkeeper.cli.stats as stats_mod

    for mod in (stats_mod, report_mod):
        src = Path(mod.__file__).read_text()
        assert "webbrowser" not in src
        assert "subprocess" not in src
        assert "os.startfile" not in src
        assert "xdg-open" not in src


# --- C4: exactly one doctype and one <html> element -----------------------------


def test_single_doctype_and_html_tag(tmp_path: Path, monkeypatch, capsys):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    text = report_path.read_text().lower()
    assert text.lstrip().startswith("<!doctype html")
    assert text.count("<!doctype html") == 1
    assert text.count("<html") == 1
    assert text.count("</html>") == 1


# --- C5: static external-request scan -------------------------------------------


def test_no_external_requests(tmp_path: Path, monkeypatch, capsys):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    text = report_path.read_text()
    assert not re.search(r"https?://", text)
    assert not re.search(r'(src|href)="//', text)
    assert not re.search(r"<script[^>]+src=", text, re.I)
    assert not re.search(r"<link[^>]+stylesheet", text, re.I)
    assert not re.search(r"url\(\s*['\"]?https?:", text, re.I)
    assert "@font-face" not in text
    assert "@import" not in text


# --- C7: zero <script> tags ------------------------------------------------------


def test_zero_script_tags(tmp_path: Path, monkeypatch, capsys):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    text = report_path.read_text()
    assert "<script" not in text.lower()


# --- C8/C9: streak + inbox-age tiles match --json --------------------------------


def test_tiles_match_json_values(tmp_path: Path, monkeypatch, capsys, frozen_today):
    vault = _init_vault(tmp_path, monkeypatch)
    today = frozen_today.isoformat()
    yesterday = (frozen_today - timedelta(days=1)).isoformat()
    five_days_ago = (frozen_today - timedelta(days=5)).isoformat()
    _write_note(vault / "10 Journal" / f"{today}.md", today)
    _write_note(vault / "10 Journal" / f"{yesterday}.md", yesterday)
    _write_note(vault / "00 Inbox" / "old.md", five_days_ago)
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)

    report_path = tmp_path / "report.html"
    main(["stats", "--html", str(report_path)])
    capsys.readouterr()
    text = report_path.read_text()

    assert payload["journal_streak"] == 2
    assert payload["health"]["inbox_oldest_age_days"] == 5
    assert re.search(
        rf'tile-value">{payload["journal_streak"]}</div>\s*'
        r'<div class="tile-label">Journal streak',
        text,
    )
    assert re.search(
        rf'tile-value">{payload["health"]["inbox_oldest_age_days"]}</div>\s*'
        r'<div class="tile-label">Inbox age',
        text,
    )
    assert re.search(
        rf'tile-value">{payload["total_notes"]}</div>\s*'
        r'<div class="tile-label">Total notes',
        text,
    )


# --- C10: empty inbox -> OK, no warn ---------------------------------------------


def test_empty_inbox_ok_no_warn(tmp_path: Path, monkeypatch, capsys):
    _init_vault(tmp_path, monkeypatch)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    tiles = _tiles_section(report_path.read_text())
    assert "warn" not in tiles
    assert "OK" in tiles


# --- C14: inbox-rot warn threshold -----------------------------------------------


def test_inbox_rot_warn_above_threshold(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    old = (frozen_today - timedelta(days=15)).isoformat()
    _write_note(vault / "00 Inbox" / "old.md", old)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    tiles = _tiles_section(report_path.read_text())
    assert "warn" in tiles


def test_inbox_rot_no_warn_at_or_under_threshold(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    recent = (frozen_today - timedelta(days=5)).isoformat()
    _write_note(vault / "00 Inbox" / "recent.md", recent)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    tiles = _tiles_section(report_path.read_text())
    assert "warn" not in tiles


# --- C11: dark-mode media query, no scripts --------------------------------------


def test_dark_mode_media_query_present(tmp_path: Path, monkeypatch, capsys):
    _init_vault(tmp_path, monkeypatch)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    text = report_path.read_text()
    assert "prefers-color-scheme" in text
    assert "<script" not in text.lower()


# --- C12: empty vault -> valid page, labeled empties, exit 0 --------------------


def test_empty_vault_valid_page_with_labeled_empties(
    tmp_path: Path, monkeypatch, capsys
):
    _init_vault(tmp_path, monkeypatch)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    exit_code = main(["stats", "--html", str(report_path)])
    text = report_path.read_text()

    assert exit_code == 0
    parser = HTMLParser()
    parser.feed(text)  # raises on parser-level errors
    parser.close()

    assert re.search(
        r'tile-value">0</div>\s*<div class="tile-label">Journal streak', text
    )
    assert 'class="empty"' in text


# --- C13: missing vault -> nonzero, init hint, no file --------------------------


def test_missing_vault_no_file_written(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    report_path = tmp_path / "report.html"

    exit_code = main(["stats", "--html", str(report_path)])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "brainkeeper init" in captured.err
    assert not report_path.exists()


# --- C36: byte-identical repeat runs same day ------------------------------------


def test_repeat_runs_byte_identical(tmp_path: Path, monkeypatch, capsys, frozen_today):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", frozen_today.isoformat())
    capsys.readouterr()
    a_path = tmp_path / "a.html"
    b_path = tmp_path / "b.html"

    main(["stats", "--html", str(a_path)])
    main(["stats", "--html", str(b_path)])
    assert a_path.read_bytes() == b_path.read_bytes()


# --- C37: --json --html combined -------------------------------------------------


def test_json_and_html_combined(tmp_path: Path, monkeypatch, capsys):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    exit_code = main(["stats", "--json", "--html", str(report_path)])
    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert isinstance(payload, dict)
    assert "<html" not in captured.out.lower()
    assert "<svg" not in captured.out.lower()
    assert str(report_path) in captured.err
    assert report_path.is_file()


# --- C39: --json alone still pure -------------------------------------------------


def test_json_only_still_pure(tmp_path: Path, monkeypatch, capsys):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()

    exit_code = main(["stats", "--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    assert isinstance(payload, dict)
    assert "<html" not in out.lower()


# =============================================================================
# T5: #33 (growth curve + bar charts) / #34 (heatmap) SVG tests
# =============================================================================

_BAR_ROW_RE = re.compile(
    r'<text class="bar-label"[^>]*>([^<]*)</text>'
    r'<rect class="bar"[^>]*width="([\d.]+)"[^>]*/>'
    r'<text class="bar-value"[^>]*>([^<]*)</text>'
)
_HM_CELL_RE = re.compile(
    r'<rect class="c(\d)" x="(\d+)" y="(\d+)" width="11" height="11"/>'
)


def _section(html_text: str, class_name: str) -> str:
    match = re.search(rf'<section class="{class_name}">.*?</section>', html_text, re.S)
    assert match, f"{class_name} section not found"
    return match.group()


def _chart_after_heading(section_html: str, heading: str) -> str:
    marker = f"<h2>{heading}</h2>"
    idx = section_html.index(marker)
    rest = section_html[idx + len(marker) :]
    next_h2 = rest.find("<h2>")
    return rest if next_h2 == -1 else rest[:next_h2]


def _hm_pos(days_ago: int) -> tuple[int, int]:
    """(col, row) for a day `days_ago` in the past, matching report.py's i=363-D grid."""
    i = 363 - days_ago
    return i // 7, i % 7


def _hm_cell(section_html: str, col: int, row: int) -> str | None:
    x, y = col * 13, row * 13
    match = re.search(
        rf'<rect class="c(\d)" x="{x}" y="{y}" width="11" height="11"/>', section_html
    )
    return match.group(1) if match else None


def _no_external_requests(text: str) -> None:
    assert not re.search(r"https?://", text)
    assert not re.search(r'(src|href)="//', text)
    assert not re.search(r"<script[^>]+src=", text, re.I)
    assert not re.search(r"<link[^>]+stylesheet", text, re.I)
    assert not re.search(r"url\(\s*['\"]?https?:", text, re.I)
    assert "@font-face" not in text
    assert "@import" not in text


# --- C15/C16/C24: growth series set == populated layers -------------------------


def test_growth_svg_series_match_populated_layers(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    today = frozen_today
    _write_note(vault / "40 Brain" / "a.md", today.isoformat())
    _write_note(vault / "20 Projects" / "b.md", (today - timedelta(days=5)).isoformat())
    _write_note(vault / "20 Projects" / "c.md", today.isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    growth = _section(report_path.read_text(), "growth")

    assert "<svg" in growth
    series = set(re.findall(r'<polyline class="line-(\w+)"', growth))
    assert series == {"brain", "projects"}
    for empty_layer in ("inbox", "journal", "areas", "archive"):
        assert f'<polyline class="line-{empty_layer}"' not in growth

    legend_layers = re.findall(r'legend-swatch line-(\w+)"', growth)
    assert legend_layers == ["projects", "brain"]  # LAYER_KEYS order among populated


# --- C41: cumulative monotonic, final value == layer total -----------------------


def test_growth_polyline_monotonic_and_matches_layer_total(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    today = frozen_today
    brain = vault / "40 Brain"
    _write_note(brain / "a.md", (today - timedelta(days=10)).isoformat())
    _write_note(brain / "b.md", (today - timedelta(days=5)).isoformat())
    _write_note(brain / "c.md", today.isoformat())
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)

    report_path = tmp_path / "report.html"
    main(["stats", "--html", str(report_path)])
    capsys.readouterr()
    growth = _section(report_path.read_text(), "growth")

    match = re.search(r'<polyline class="line-brain" points="([^"]*)"/>', growth)
    assert match
    points = [tuple(map(float, p.split(","))) for p in match.group(1).split()]
    ys = [y for _, y in points]
    assert all(a >= b for a, b in zip(ys, ys[1:]))  # y falls as cumulative rises

    brain_series = payload["series"]["growth_by_layer"]["brain"]
    assert len(points) == len(brain_series)
    assert brain_series[-1][1] == payload["notes_per_layer"]["brain"]


# --- C17/C19: notes-per-layer chart: 6 rows, all labels, zero-width bar ---------


def test_notes_per_layer_chart_has_six_rows(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", frozen_today.isoformat())
    _write_note(vault / "40 Brain" / "b.md", frozen_today.isoformat())
    _write_note(vault / "20 Projects" / "c.md", frozen_today.isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    bars = _section(report_path.read_text(), "bars")
    layer_chart = _chart_after_heading(bars, "Notes per layer")
    rows = _BAR_ROW_RE.findall(layer_chart)

    assert len(rows) == 6
    labels = [label for label, _, _ in rows]
    assert labels == ["Inbox", "Journal", "Projects", "Areas", "Brain", "Archive"]
    counts = {label: int(count) for label, _, count in rows}
    widths = {label: float(width) for label, width, _ in rows}
    assert counts == {
        "Inbox": 0,
        "Journal": 0,
        "Projects": 1,
        "Areas": 0,
        "Brain": 2,
        "Archive": 0,
    }
    assert widths["Inbox"] == 0.0  # zero count -> zero width
    assert widths["Brain"] > widths["Projects"] > 0  # widest for the largest count


# --- C18: top-tags chart: one row per tag, labels escaped -----------------------


def test_top_tags_chart_one_row_per_tag_and_escaped(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    brain = vault / "40 Brain"
    _write_note(brain / "a.md", frozen_today.isoformat(), tags=["<xss>", "plain"])
    _write_note(brain / "b.md", frozen_today.isoformat(), tags=["<xss>"])
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)

    report_path = tmp_path / "report.html"
    main(["stats", "--html", str(report_path)])
    capsys.readouterr()
    bars = _section(report_path.read_text(), "bars")
    tag_chart = _chart_after_heading(bars, "Top tags")
    rows = _BAR_ROW_RE.findall(tag_chart)

    assert len(rows) == len(payload["top_tags"])
    labels = [label for label, _, _ in rows]
    assert "&lt;xss&gt;" in labels
    assert "<xss>" not in tag_chart  # raw tag never lands unescaped


# --- C19: bar widths proportional to counts -------------------------------------


def test_bar_widths_proportional_to_counts(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    brain = vault / "40 Brain"
    for i in range(5):
        _write_note(brain / f"five{i}.md", frozen_today.isoformat(), tags=["five"])
    _write_note(brain / "one.md", frozen_today.isoformat(), tags=["one"])
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    bars = _section(report_path.read_text(), "bars")
    tag_chart = _chart_after_heading(bars, "Top tags")
    widths = {label: float(width) for label, width, _ in _BAR_ROW_RE.findall(tag_chart)}

    assert widths["five"] / widths["one"] == pytest.approx(5, rel=0.05)


# --- C22/C23: empty vault -> labeled empty states -------------------------------


def test_empty_vault_growth_and_bars_labeled_empty(tmp_path: Path, monkeypatch, capsys):
    _init_vault(tmp_path, monkeypatch)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    exit_code = main(["stats", "--html", str(report_path)])
    text = report_path.read_text()
    assert exit_code == 0

    growth = _section(text, "growth")
    assert "No growth data yet" in growth
    assert "<polyline" not in growth

    bars = _section(text, "bars")
    tag_chart = _chart_after_heading(bars, "Top tags")
    assert "No tags yet" in tag_chart

    layer_chart = _chart_after_heading(bars, "Notes per layer")
    rows = _BAR_ROW_RE.findall(layer_chart)
    assert len(rows) == 6
    assert all(int(count) == 0 for _, _, count in rows)


# --- C20: external-request scan still clean on a fully populated report ---------
# (C21's offline-vs-online visual parity is a browser-runtime check, not
# unit-testable; the contract's verify_how for it is manual observation.)


def test_no_external_requests_full_populated_report(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", frozen_today.isoformat(), tags=["x"])
    _write_note(
        vault / "20 Projects" / "b.md",
        (frozen_today - timedelta(days=5)).isoformat(),
        tags=["y"],
    )
    _write_note(
        vault / "10 Journal" / f"{frozen_today.isoformat()}.md",
        frozen_today.isoformat(),
    )
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    _no_external_requests(report_path.read_text())


# --- C25/C26: heatmap grid shape -------------------------------------------------


def test_heatmap_grid_shape_364_cells(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", frozen_today.isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    heatmap = _section(report_path.read_text(), "heatmap")

    assert "<svg" in heatmap
    cells = _HM_CELL_RE.findall(heatmap)
    assert len(cells) == 364
    assert len({x for _, x, _ in cells}) == 52
    assert len({y for _, _, y in cells}) == 7


# --- C27: shading follows created, not updated -----------------------------------


def test_heatmap_shading_follows_created_not_updated(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    created = (frozen_today - timedelta(days=100)).isoformat()
    _write_note(
        vault / "40 Brain" / "a.md", created=created, updated=frozen_today.isoformat()
    )
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    heatmap = _section(report_path.read_text(), "heatmap")

    col100, row100 = _hm_pos(100)
    assert _hm_cell(heatmap, col100, row100) != "0"
    col_today, row_today = _hm_pos(0)
    assert (col_today, row_today) == (51, 6)
    assert _hm_cell(heatmap, col_today, row_today) == "0"


# --- C28: discrete intensity levels from counts ----------------------------------


def test_heatmap_intensity_levels_from_counts(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    brain = vault / "40 Brain"
    count_to_days_ago = {1: 10, 2: 20, 3: 30, 5: 40}
    for count, days_ago in count_to_days_ago.items():
        day = (frozen_today - timedelta(days=days_ago)).isoformat()
        for i in range(count):
            _write_note(brain / f"d{days_ago}_{i}.md", day)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    heatmap = _section(report_path.read_text(), "heatmap")

    expected_level = {1: "1", 2: "2", 3: "3", 5: "4"}
    for count, days_ago in count_to_days_ago.items():
        col, row = _hm_pos(days_ago)
        assert _hm_cell(heatmap, col, row) == expected_level[count]


# --- C29: deterministic fixture -> exactly N shaded cells at expected positions --


def test_heatmap_exact_shaded_cells_at_expected_positions(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    brain = vault / "40 Brain"
    offsets = (10, 100, 300)
    for d in offsets:
        _write_note(brain / f"n{d}.md", (frozen_today - timedelta(days=d)).isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    heatmap = _section(report_path.read_text(), "heatmap")

    cells = _HM_CELL_RE.findall(heatmap)
    non_quiet = {(x, y) for level, x, y in cells if level != "0"}
    assert len(non_quiet) == 3
    expected = {
        (str(col * 13), str(row * 13)) for d in offsets for col, row in [_hm_pos(d)]
    }
    assert non_quiet == expected


# --- C30: heatmap section byte-identical across two runs same day ---------------


def test_heatmap_byte_identical_across_runs(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", frozen_today.isoformat())
    _write_note(
        vault / "20 Projects" / "b.md", (frozen_today - timedelta(days=30)).isoformat()
    )
    capsys.readouterr()
    a_path = tmp_path / "a.html"
    b_path = tmp_path / "b.html"

    main(["stats", "--html", str(a_path)])
    main(["stats", "--html", str(b_path)])
    heatmap_a = _section(a_path.read_text(), "heatmap")
    heatmap_b = _section(b_path.read_text(), "heatmap")
    assert heatmap_a == heatmap_b


# --- C31: empty vault -> all 364 cells at c0 -------------------------------------


def test_heatmap_empty_vault_all_quiet(tmp_path: Path, monkeypatch, capsys):
    _init_vault(tmp_path, monkeypatch)
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    exit_code = main(["stats", "--html", str(report_path)])
    heatmap = _section(report_path.read_text(), "heatmap")
    assert exit_code == 0

    cells = _HM_CELL_RE.findall(heatmap)
    assert len(cells) == 364
    assert all(level == "0" for level, _, _ in cells)


# --- C33: today's cell is the last cell and is shaded ----------------------------


def test_heatmap_today_cell_is_last_and_shaded(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", frozen_today.isoformat())
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    heatmap = _section(report_path.read_text(), "heatmap")

    assert _hm_cell(heatmap, 51, 6) != "0"


# --- C40: combined per-day total across layers -----------------------------------


def test_heatmap_combines_counts_across_layers(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    day = (frozen_today - timedelta(days=20)).isoformat()
    _write_note(vault / "40 Brain" / "a.md", day)
    _write_note(vault / "20 Projects" / "b.md", day)
    _write_note(vault / "20 Projects" / "c.md", day)
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["series"]["daily_created"][day] == 3

    report_path = tmp_path / "report.html"
    main(["stats", "--html", str(report_path)])
    capsys.readouterr()
    heatmap = _section(report_path.read_text(), "heatmap")

    col, row = _hm_pos(20)
    assert _hm_cell(heatmap, col, row) == "3"  # min(3,4); distinct from a lone 1 or 2


# =============================================================================
# T6: integration pass
# =============================================================================


# --- C34: all sections present together in one file ------------------------------


def test_report_contains_all_sections(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    vault = _init_vault(tmp_path, monkeypatch)
    _write_note(vault / "40 Brain" / "a.md", frozen_today.isoformat())
    _write_note(
        vault / "20 Projects" / "b.md", (frozen_today - timedelta(days=3)).isoformat()
    )
    _write_note(
        vault / "00 Inbox" / "c.md", (frozen_today - timedelta(days=2)).isoformat()
    )
    capsys.readouterr()
    report_path = tmp_path / "report.html"

    main(["stats", "--html", str(report_path)])
    text = report_path.read_text()

    assert 'class="tiles"' in text
    assert "<svg" in _section(text, "growth")
    assert "Notes per layer" in text
    assert "Top tags" in text
    assert "<svg" in _section(text, "heatmap")


# --- C35: HTML numbers agree with --json for the same vault ----------------------


def test_html_values_match_json_across_sections(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    import brainkeeper.cli.report as report_mod

    vault = _init_vault(tmp_path, monkeypatch)
    today = frozen_today.isoformat()
    yesterday = (frozen_today - timedelta(days=1)).isoformat()
    _write_note(vault / "10 Journal" / f"{today}.md", today)
    _write_note(vault / "10 Journal" / f"{yesterday}.md", yesterday)
    _write_note(vault / "40 Brain" / "a.md", today, tags=["alpha"])
    _write_note(vault / "40 Brain" / "b.md", today, tags=["alpha"])
    _write_note(vault / "20 Projects" / "c.md", today, tags=["beta"])
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)

    report_path = tmp_path / "report.html"
    main(["stats", "--html", str(report_path)])
    capsys.readouterr()
    text = report_path.read_text()

    assert re.search(rf'tile-value">{payload["journal_streak"]}</div>', text)
    assert re.search(rf'tile-value">{payload["total_notes"]}</div>', text)

    bars = _section(text, "bars")
    layer_chart = _chart_after_heading(bars, "Notes per layer")
    layer_rows = {
        label: int(count) for label, _, count in _BAR_ROW_RE.findall(layer_chart)
    }
    for key, count in payload["notes_per_layer"].items():
        assert layer_rows[report_mod._LAYER_LABELS[key]] == count

    tag_chart = _chart_after_heading(bars, "Top tags")
    tag_rows = {label: int(count) for label, _, count in _BAR_ROW_RE.findall(tag_chart)}
    for tag, count in payload["top_tags"]:
        assert tag_rows[tag] == count
