import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from freezegun import freeze_time

from brainkeeper.cli import main
from conftest import write_note as _write_note

_LAYER_DIRS = [
    "00 Inbox",
    "10 Journal",
    "20 Projects",
    "30 Areas",
    "40 Brain",
    "90 Archive",
]

_STATS_TODAY = date(2025, 6, 15)


@pytest.fixture
def frozen_today():
    """Pin `date.today()` for tests whose fixtures are built from relative dates."""
    with freeze_time(_STATS_TODAY.isoformat()):
        yield _STATS_TODAY


def test_init_creates_layers_and_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert main(["init"]) == 0
    vault = tmp_path / ".brainkeeper" / "vault"
    for layer in _LAYER_DIRS:
        assert (vault / layer).is_dir()
    assert (vault / "brainkeeper.yaml").exists()


def test_reinit_warns_and_preserves_config(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    config_path = tmp_path / ".brainkeeper" / "vault" / "brainkeeper.yaml"
    config_path.write_text("# user edit\n")

    assert main(["init"]) == 0
    assert "already exists" in capsys.readouterr().err
    assert config_path.read_text() == "# user edit\n"


def test_serve_missing_vault_exits_1(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert main(["serve"]) == 1
    assert "brainkeeper init" in capsys.readouterr().err


def test_init_blocked_by_file_exits_1(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".brainkeeper").write_text("not a directory\n")
    assert main(["init"]) == 1
    assert "error" in capsys.readouterr().err


# --- stats: C01 missing vault -----------------------------------------------


def test_stats_missing_vault_exits_nonzero(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    exit_code = main(["stats"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "brainkeeper init" in captured.err
    assert "Traceback" not in captured.err


def test_stats_malformed_yaml_exits_nonzero(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    config_path = tmp_path / ".brainkeeper" / "vault" / "brainkeeper.yaml"
    config_path.write_text("layers: [unbalanced\n")
    capsys.readouterr()

    exit_code = main(["stats"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "brainkeeper init" in captured.err
    assert "Traceback" not in captured.err


# --- stats: C02/C28 empty vault -----------------------------------------------


def test_stats_empty_vault_friendly_zero(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    capsys.readouterr()

    assert main(["stats"]) == 0
    out = capsys.readouterr().out
    assert "Total notes: 0" in out
    assert "no entries yet" in out  # friendly streak wording
    assert "Traceback" not in out
    assert "error" not in out.lower()


def test_stats_empty_vault_health_all_clean(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    capsys.readouterr()

    assert main(["stats"]) == 0
    out = capsys.readouterr().out
    assert "WARN" not in out
    assert "Inbox rot: OK" in out
    assert "Orphans: OK" in out
    assert "Sync conflicts: OK" in out


# --- stats: C13 sparse vault -------------------------------------------------


def test_stats_sparse_vault_explicit_empty_sections(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()

    exit_code = main(["stats"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Traceback" not in out
    assert "no entries yet" in out  # empty journal streak, not an error
    assert "Notes per layer: Inbox 0" in out  # explicit zero, not blank
    assert "Brain 1" in out


# --- stats: C09/C19 zone order + three health checks -------------------------


def test_stats_zone_order_and_health_checks(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    _write_note(vault / "40 Brain" / "b.md", date.today().isoformat())
    capsys.readouterr()

    assert main(["stats"]) == 0
    out = capsys.readouterr().out
    progress_i = out.index("Progress")
    health_i = out.index("Health")
    structure_i = out.index("Structure")
    assert progress_i < health_i < structure_i
    assert "Inbox rot" in out
    assert "Orphans" in out
    assert "Sync conflicts" in out


# --- stats: C10 worst-case line budget ---------------------------------------


def test_stats_worst_case_stays_within_line_budget(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    today = frozen_today.isoformat()
    old_inbox = (frozen_today - timedelta(days=15)).isoformat()

    _write_note(vault / "00 Inbox" / "old.md", old_inbox, tags=["a", "b"])
    _write_note(vault / "10 Journal" / f"{today}.md", today, tags=["c"])
    _write_note(vault / "20 Projects" / "p.md", today, tags=["d"])
    _write_note(vault / "30 Areas" / "ar.md", today, tags=["e"])
    _write_note(vault / "40 Brain" / "br.md", today, tags=["f", "g"])
    _write_note(vault / "90 Archive" / "arc.md", today, tags=["h"])
    # orphan: no frontmatter
    (vault / "40 Brain" / "bad.md").write_text("no frontmatter here\n")
    # sync-conflict file
    (vault / "40 Brain" / "x.sync-conflict-20260101-000000-ABC.md").write_text(
        "conflict copy\n"
    )
    capsys.readouterr()

    exit_code = main(["stats"])
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert exit_code == 0
    assert len(lines) <= 25
    assert out.count("WARN") == 3  # inbox rot, orphan, sync-conflict all warn


# --- stats: E02 --help mentions local calendar days ---------------------------


def test_stats_help_mentions_local_calendar_days(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["stats", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "local" in out.lower()


# --- stats: C29 determinism across repeat runs --------------------------------


def test_stats_repeat_runs_identical_output(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    today = frozen_today.isoformat()
    yesterday = (frozen_today - timedelta(days=1)).isoformat()
    old_inbox = (frozen_today - timedelta(days=15)).isoformat()

    _write_note(vault / "10 Journal" / f"{yesterday}.md", yesterday)
    _write_note(vault / "10 Journal" / f"{today}.md", today)
    _write_note(vault / "00 Inbox" / "old.md", old_inbox)
    _write_note(vault / "40 Brain" / "a.md", today, tags=["x"])
    capsys.readouterr()

    assert main(["stats"]) == 0
    first = capsys.readouterr().out
    assert main(["stats"]) == 0
    second = capsys.readouterr().out
    assert first == second
    assert first != ""


# --- stats --json: shared helpers --------------------------------------------


def _write_status_config(vault: Path) -> None:
    """Overwrite the fixture's brainkeeper.yaml with statuses configured on projects."""
    (vault / "brainkeeper.yaml").write_text(
        "layers:\n"
        '  inbox: "00 Inbox"\n'
        '  journal: "10 Journal"\n'
        "  projects:\n"
        '    path: "20 Projects"\n'
        "    status_field: status\n"
        "    statuses: [active, stalled, done]\n"
        '  areas: "30 Areas"\n'
        '  brain: "40 Brain"\n'
        '  archive: "90 Archive"\n'
    )


def _write_project(path: Path, status: str, created: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ncreated: {created}\nupdated: {created}\ntags: [x]\n"
        f"status: {status}\n---\nbody\n"
    )


# --- stats --json: C1 valid JSON + exit 0 -------------------------------------


def test_stats_json_valid_and_exits_zero(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()

    exit_code = main(["stats", "--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert isinstance(json.loads(out), dict)


# --- C2: total_notes excludes conflict files -----------------------------------


def test_stats_json_total_notes_excludes_conflicts(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    today = date.today().isoformat()
    _write_note(vault / "40 Brain" / "a.md", today)
    _write_note(vault / "40 Brain" / "b.md", today)
    _write_note(vault / "20 Projects" / "c.md", today)
    _write_note(vault / "00 Inbox" / "d.md", today)
    (vault / "40 Brain" / "x.sync-conflict-20260101-000000-ABC.md").write_text(
        "conflict copy\n"
    )
    capsys.readouterr()

    exit_code = main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["total_notes"] == 4


# --- C3: notes_per_layer has all six keys, zero-filled --------------------------


def test_stats_json_notes_per_layer_six_keys(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    today = date.today().isoformat()
    _write_note(vault / "40 Brain" / "a.md", today)
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["notes_per_layer"] == {
        "inbox": 0,
        "journal": 0,
        "projects": 0,
        "areas": 0,
        "brain": 1,
        "archive": 0,
    }


# --- C4: journal_streak integer -------------------------------------------------


def test_stats_json_journal_streak(tmp_path: Path, monkeypatch, capsys, frozen_today):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    today = frozen_today.isoformat()
    yesterday = (frozen_today - timedelta(days=1)).isoformat()
    _write_note(vault / "10 Journal" / f"{today}.md", today)
    _write_note(vault / "10 Journal" / f"{yesterday}.md", yesterday)
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["journal_streak"] == 2


# --- C5/C6: health block (three checks + numeric inbox age) --------------------


def test_stats_json_health_block(tmp_path: Path, monkeypatch, capsys, frozen_today):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    old_inbox = (frozen_today - timedelta(days=15)).isoformat()
    _write_note(vault / "00 Inbox" / "old.md", old_inbox)
    (vault / "40 Brain" / "orphan.md").parent.mkdir(parents=True, exist_ok=True)
    (vault / "40 Brain" / "orphan.md").write_text("no frontmatter\n")
    (vault / "40 Brain" / "x.sync-conflict-20260101-000000-ABC.md").write_text(
        "conflict copy\n"
    )
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == {
        "inbox_oldest_age_days": 15,
        "orphan_count": 1,
        "conflict_count": 1,
    }


def test_stats_json_inbox_age_null_when_no_inbox_notes(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["health"]["inbox_oldest_age_days"] is None


# --- C7: top_tags ordered by descending count -----------------------------------


def test_stats_json_top_tags(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    today = date.today().isoformat()
    _write_note(vault / "40 Brain" / "n0.md", today, tags=["a"])
    _write_note(vault / "40 Brain" / "n1.md", today, tags=["a"])
    _write_note(vault / "40 Brain" / "n2.md", today, tags=["a", "b"])
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["top_tags"] == [["a", 3], ["b", 1]]


# --- C15: created vs updated series are distinct --------------------------------


def test_stats_json_created_vs_updated_series(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    today = frozen_today.isoformat()
    ten_days_ago = (frozen_today - timedelta(days=10)).isoformat()
    _write_note(vault / "40 Brain" / "x.md", created=ten_days_ago, updated=today)
    _write_note(vault / "40 Brain" / "y.md", created=today, updated=today)
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    series = payload["series"]
    assert series["daily_created"][ten_days_ago] == 1  # x, by created date
    assert series["daily_created"][today] == 1  # y, by created date
    assert series["daily_updated"][ten_days_ago] == 0  # x moved off this day
    assert series["daily_updated"][today] == 2  # x and y, by updated date


# --- C16/C17: JSON is a superset of the terminal, series are JSON-only ----------


def _write_summary_fixture(vault: Path, today: date) -> None:
    # old.md and the journal note keep the default tag "x" (2 total, below "a"/"b").
    _write_note(vault / "00 Inbox" / "old.md", (today - timedelta(days=15)).isoformat())
    _write_note(vault / "10 Journal" / f"{today.isoformat()}.md", today.isoformat())
    _write_note(
        vault / "20 Projects" / "p.md",
        (today - timedelta(days=3)).isoformat(),
        tags=["a"],
    )
    _write_note(vault / "40 Brain" / "b1.md", today.isoformat(), tags=["a", "b"])
    _write_note(vault / "40 Brain" / "b2.md", today.isoformat(), tags=["a"])


def test_stats_json_is_superset_of_terminal_metrics(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_summary_fixture(vault, frozen_today)
    capsys.readouterr()

    main(["stats"])
    text_out = capsys.readouterr().out
    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)

    # Known-by-construction fixture values, asserted against both surfaces
    # independently (not scraped from one to check the other).
    assert payload["total_notes"] == 5
    assert "Total notes: 5" in text_out

    assert sum(payload["created_7d_per_layer"].values()) == 4
    assert "Created last 7 days: 4 " in text_out
    assert sum(payload["created_30d_per_layer"].values()) == 5
    assert "Created last 30 days: 5 " in text_out

    assert payload["journal_streak"] == 1
    assert "Journal streak: 1 days" in text_out

    assert payload["health"]["inbox_oldest_age_days"] == 15
    assert "oldest 15d" in text_out
    assert payload["health"]["orphan_count"] == 0
    assert "Orphans: OK" in text_out
    assert payload["health"]["conflict_count"] == 0
    assert "Sync conflicts: OK" in text_out

    assert payload["top_tags"] == [["a", 3], ["x", 2], ["b", 1]]
    assert "Top tags: a (3), x (2), b (1)" in text_out

    assert payload["notes_per_layer"] == {
        "inbox": 1,
        "journal": 1,
        "projects": 1,
        "areas": 0,
        "brain": 2,
        "archive": 0,
    }
    assert (
        "Notes per layer: Inbox 1, Journal 1, Projects 1, Areas 0, Brain 2, Archive 0"
        in text_out
    )


def test_stats_json_extra_series_absent_from_terminal(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_summary_fixture(vault, frozen_today)
    capsys.readouterr()

    main(["stats"])
    text_out = capsys.readouterr().out
    with pytest.raises(json.JSONDecodeError):
        json.loads(text_out)

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    series = payload["series"]
    assert set(series) == {
        "daily_created",
        "daily_updated",
        "weekly_created",
        "monthly_created",
        "growth_by_layer",
    }
    # Exact values, known by construction from _write_summary_fixture, not just
    # key presence: a(p,b1,b2)=3, x(old,journal)=2, b(b1)=1; only b1 has 2+ tags.
    assert payload["tag_counts"] == {"a": 3, "x": 2, "b": 1}
    assert payload["tag_cooccurrence"] == [["a", "b", 1]]

    today = frozen_today.isoformat()
    three_days_ago = (frozen_today - timedelta(days=3)).isoformat()
    fifteen_days_ago = (frozen_today - timedelta(days=15)).isoformat()
    growth = series["growth_by_layer"]
    assert growth["brain"] == [[today, 2]]  # b1, b2 both created today
    assert growth["projects"] == [[three_days_ago, 1]]  # p
    assert growth["inbox"] == [[fifteen_days_ago, 1]]  # old
    assert growth["journal"] == [[today, 1]]
    assert growth["areas"] == []
    assert growth["archive"] == []

    # None of these JSON-only series surface as terminal text/lines.
    for date_key in series["daily_created"]:
        assert date_key not in text_out
    for week_key in series["weekly_created"]:
        assert week_key not in text_out
    for month_key in series["monthly_created"]:
        assert month_key not in text_out
    for layer_points in growth.values():
        for date_str, _count in layer_points:
            assert date_str not in text_out


# --- C18: empty vault, structurally complete JSON -------------------------------


def test_stats_json_empty_vault_structurally_complete(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    capsys.readouterr()

    exit_code = main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["total_notes"] == 0
    assert payload["notes_per_layer"] == dict.fromkeys(
        ["inbox", "journal", "projects", "areas", "brain", "archive"], 0
    )
    assert payload["journal_streak"] == 0
    assert payload["top_tags"] == []
    assert payload["tag_counts"] == {}
    assert payload["tag_cooccurrence"] == []
    assert payload["health"] == {
        "inbox_oldest_age_days": None,
        "orphan_count": 0,
        "conflict_count": 0,
    }
    series = payload["series"]
    assert len(series["daily_created"]) == 364
    assert all(v == 0 for v in series["daily_created"].values())
    assert len(series["daily_updated"]) == 364
    assert all(v == 0 for v in series["daily_updated"].values())
    assert series["weekly_created"] == {}
    assert series["monthly_created"] == {}
    assert series["growth_by_layer"] == {
        k: [] for k in ("inbox", "journal", "projects", "areas", "brain", "archive")
    }
    assert "project_status" not in payload


# --- C19: missing vault emits no stdout JSON ------------------------------------


def test_stats_json_missing_vault_no_stdout_json(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    exit_code = main(["stats", "--json"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "brainkeeper init" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


# --- C21: no word-count metric field --------------------------------------------


def _all_keys(obj) -> list[str]:
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(k)
            keys.extend(_all_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(_all_keys(item))
    return keys


def test_stats_json_no_word_count_field(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat(), tags=["x", "y"])
    capsys.readouterr()

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    keys = _all_keys(payload)
    assert "word_count" not in keys
    assert "words" not in keys
    assert "wordCount" not in keys


# --- C22: terminal zones unchanged without --json -------------------------------


def test_stats_terminal_zones_unchanged_without_json_flag(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(vault / "40 Brain" / "a.md", date.today().isoformat())
    capsys.readouterr()

    exit_code = main(["stats"])
    out = capsys.readouterr().out
    assert exit_code == 0
    progress_i = out.index("Progress")
    health_i = out.index("Health")
    structure_i = out.index("Structure")
    assert progress_i < health_i < structure_i
    assert "Project status" not in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


# --- C23/C24/C25: project status configured, terminal + JSON -------------------


def test_stats_project_status_configured_terminal_and_json(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_status_config(vault)
    today = frozen_today.isoformat()
    projects = vault / "20 Projects"
    _write_project(projects / "p1.md", "active", today)
    _write_project(projects / "p2.md", "active", today)
    _write_project(projects / "p3.md", "stalled", today)
    capsys.readouterr()

    exit_code = main(["stats"])
    text_out = capsys.readouterr().out
    assert exit_code == 0
    health_i = text_out.index("Health")
    status_i = text_out.index("Project status")
    structure_i = text_out.index("Structure")
    assert health_i < status_i < structure_i
    assert "active: 2" in text_out
    assert "stalled: 1" in text_out
    assert "done: 0" in text_out

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["project_status"] == {"active": 2, "stalled": 1, "done": 0}


# --- C26: configured but empty projects layer -----------------------------------


def test_stats_project_status_configured_but_empty_shows_zeros(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_status_config(vault)
    capsys.readouterr()

    exit_code = main(["stats"])
    text_out = capsys.readouterr().out
    assert exit_code == 0
    assert "Project status" in text_out
    assert "active: 0" in text_out
    assert "stalled: 0" in text_out
    assert "done: 0" in text_out

    exit_code = main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["project_status"] == {"active": 0, "stalled": 0, "done": 0}


# --- C27/C28: unconfigured projects layer, section absent everywhere -----------


def test_stats_project_status_absent_when_unconfigured(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])  # default minimal.yaml: no status_field/statuses
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(vault / "20 Projects" / "p1.md", date.today().isoformat())
    capsys.readouterr()

    main(["stats"])
    text_out = capsys.readouterr().out
    assert "Project status" not in text_out
    health_i = text_out.index("Health")
    structure_i = text_out.index("Structure")
    assert health_i < structure_i

    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "project_status" not in payload


# --- C29: created_7d/30d per-layer, JSON vs terminal ----------------------------


def test_stats_created_7d_30d_json_matches_terminal(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_note(
        vault / "40 Brain" / "recent.md",
        (frozen_today - timedelta(days=3)).isoformat(),
    )
    _write_note(
        vault / "20 Projects" / "old.md",
        (frozen_today - timedelta(days=20)).isoformat(),
    )
    capsys.readouterr()

    main(["stats"])
    text_out = capsys.readouterr().out
    main(["stats", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["created_7d_per_layer"]["brain"] == 1
    assert payload["created_7d_per_layer"]["projects"] == 0
    assert payload["created_30d_per_layer"]["brain"] == 1
    assert payload["created_30d_per_layer"]["projects"] == 1
    assert "Created last 7 days: 1 (Brain 1)" in text_out
    assert "Created last 30 days: 2 (Projects 1, Brain 1)" in text_out


# --- C30: byte-identical repeats for --json -------------------------------------


def test_stats_json_repeat_runs_identical_output(
    tmp_path: Path, monkeypatch, capsys, frozen_today
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    vault = tmp_path / ".brainkeeper" / "vault"
    _write_summary_fixture(vault, frozen_today)
    capsys.readouterr()

    assert main(["stats", "--json"]) == 0
    first = capsys.readouterr().out
    assert main(["stats", "--json"]) == 0
    second = capsys.readouterr().out
    assert first == second
    assert first != ""
