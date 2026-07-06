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
