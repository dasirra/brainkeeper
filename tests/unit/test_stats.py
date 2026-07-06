"""Unit tests for `compute_stats` (core/stats.py) against contract criteria."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from freezegun import freeze_time

from brainkeeper.core.stats import INBOX_ROT_DAYS, LAYER_KEYS, compute_stats
from conftest import write_note as _write
from conftest import write_status_config as _write_status_config

TODAY = date(2025, 6, 15)


@pytest.fixture(autouse=True)
def _frozen_today():
    with freeze_time(TODAY.isoformat()):
        yield


def _d(delta: int) -> str:
    """ISO date string `delta` days from the frozen today (negative = past)."""
    return (TODAY + timedelta(days=delta)).isoformat()


# --- C03/C08: totals + per-layer breakdown -----------------------------------


def test_total_across_all_layers(minimal_vault: Path):
    _write(minimal_vault / "00 Inbox" / "a.md", _d(0))
    _write(minimal_vault / "40 Brain" / "b.md", _d(0))
    _write(minimal_vault / "30 Areas" / "c.md", _d(0))
    _write(minimal_vault / "20 Projects" / "d.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.total_notes == 4


def test_notes_per_layer_covers_all_six(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "a.md", _d(0))
    _write(minimal_vault / "40 Brain" / "b.md", _d(0))
    _write(minimal_vault / "00 Inbox" / "c.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.notes_per_layer == {
        "inbox": 1,
        "journal": 0,
        "projects": 0,
        "areas": 0,
        "brain": 2,
        "archive": 0,
    }


# --- C04-C06, E04: 7d/30d windows, inclusive edges ---------------------------


def test_created_windows_per_layer_edges(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "d0.md", _d(0))
    _write(brain / "d3.md", _d(-3))
    _write(brain / "d7.md", _d(-7))  # E04: exactly 7 counts in 7d window
    _write(brain / "d8.md", _d(-8))  # just outside 7d window
    _write(brain / "d20.md", _d(-20))
    _write(brain / "d30.md", _d(-30))  # E04: exactly 30 counts in 30d window
    _write(brain / "d31.md", _d(-31))  # just outside 30d window
    _write(minimal_vault / "00 Inbox" / "i0.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.created_7d_per_layer["brain"] == 3  # d0, d3, d7
    assert stats.created_30d_per_layer["brain"] == 6  # all but d31
    assert stats.created_7d_per_layer["inbox"] == 1
    assert stats.created_30d_per_layer["inbox"] == 1


def test_created_window_relativity_c06(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "a.md", _d(-3))
    _write(brain / "b.md", _d(-20))

    stats = compute_stats(minimal_vault)

    assert stats.created_7d_per_layer["brain"] == 1
    assert stats.created_30d_per_layer["brain"] == 2


# --- C07: top-5 tags capped -------------------------------------------------


def test_top_tags_capped_at_five(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    note_tags = [
        ["a", "b", "c", "d"],
        ["a", "b", "c", "e"],
        ["a", "b", "c"],
        ["a", "d"],
        ["e"],
        ["f"],
        ["g"],
    ]
    for i, tags in enumerate(note_tags):
        _write(brain / f"n{i}.md", _d(0), tags=tags)

    stats = compute_stats(minimal_vault)

    assert stats.top_tags == [
        ("a", 4),
        ("b", 3),
        ("c", 3),
        ("d", 2),
        ("e", 2),
    ]


def test_tags_normalized_and_deduped_per_note(minimal_vault: Path):
    """A repeated tag counts once per note; a leading '#' is stripped."""
    brain = minimal_vault / "40 Brain"
    n0 = brain / "n0.md"
    n0.parent.mkdir(parents=True, exist_ok=True)
    n0.write_text(
        f"---\ncreated: {_d(0)}\nupdated: {_d(0)}\n"
        'tags: ["mcp", "mcp", "#mcp"]\n---\nbody\n'
    )
    _write(brain / "n1.md", _d(0), tags=['"#mcp"'])

    stats = compute_stats(minimal_vault)

    assert stats.top_tags == [("mcp", 2)]


# --- C11/C12: exclusions -----------------------------------------------------


def test_templates_excluded(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "real.md", _d(0), tags=["real"])
    _write(
        minimal_vault / "40 Brain" / "_templates" / "note.md",
        _d(0),
        tags=["template-tag"],
    )

    stats = compute_stats(minimal_vault)

    assert stats.total_notes == 1
    assert all(tag != "template-tag" for tag, _ in stats.top_tags)


def test_dot_dirs_excluded(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "real.md", _d(0))
    _write(minimal_vault / "40 Brain" / ".obsidian" / "x.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.total_notes == 1


# --- C14-C18, E01: journal streak --------------------------------------------


def test_streak_empty_journal_is_zero(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "a.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.journal_streak == 0


def test_streak_run_ending_today(minimal_vault: Path):
    journal = minimal_vault / "10 Journal"
    for delta in (-2, -1, 0):
        _write(journal / f"{_d(delta)}.md", _d(delta))

    stats = compute_stats(minimal_vault)

    assert stats.journal_streak == 3


def test_streak_run_ending_yesterday_still_alive(minimal_vault: Path):
    journal = minimal_vault / "10 Journal"
    for delta in (-2, -1):
        _write(journal / f"{_d(delta)}.md", _d(delta))

    stats = compute_stats(minimal_vault)

    assert stats.journal_streak == 2


def test_streak_one_day_gap_breaks_it(minimal_vault: Path):
    journal = minimal_vault / "10 Journal"
    for delta in (-4, -3, -1, 0):  # gap at -2
        _write(journal / f"{_d(delta)}.md", _d(delta))

    stats = compute_stats(minimal_vault)

    assert stats.journal_streak == 2


def test_streak_filename_date_wins_over_created(minimal_vault: Path):
    journal = minimal_vault / "10 Journal"
    # Filename says today; frontmatter created disagrees (5 days ago).
    _write(journal / f"{_d(0)}.md", created=_d(-5), updated=_d(0))

    stats = compute_stats(minimal_vault)

    assert stats.journal_streak == 1


# --- C20-C23, E03: inbox rot --------------------------------------------------


@pytest.mark.parametrize(
    "age_days,expect_warn",
    [
        (13, False),  # C21
        (14, False),  # E03: strict boundary, no warn
        (15, True),  # C20/E03: just past boundary, warns
    ],
)
def test_inbox_warn_threshold(minimal_vault: Path, age_days: int, expect_warn: bool):
    _write(minimal_vault / "00 Inbox" / "note.md", _d(-age_days))

    stats = compute_stats(minimal_vault)

    assert (stats.inbox_oldest_age_days > INBOX_ROT_DAYS) is expect_warn
    assert stats.inbox_oldest_age_days == age_days


def test_inbox_oldest_age_is_numeric_max(minimal_vault: Path):
    inbox = minimal_vault / "00 Inbox"
    _write(inbox / "old.md", _d(-15))
    _write(inbox / "new.md", _d(-3))

    stats = compute_stats(minimal_vault)

    assert stats.inbox_oldest_age_days == 15
    assert stats.inbox_oldest_age_days > INBOX_ROT_DAYS


def test_inbox_empty_has_no_age(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "a.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.inbox_oldest_age_days is None


def test_inbox_future_dated_note_clamps_age_to_zero(minimal_vault: Path):
    """A future `created` date must not produce a negative age."""
    _write(minimal_vault / "00 Inbox" / "note.md", _d(5))

    stats = compute_stats(minimal_vault)

    assert stats.inbox_oldest_age_days == 0
    assert stats.inbox_oldest_age_days <= INBOX_ROT_DAYS


# --- C24-C27, E05: orphans and sync conflicts --------------------------------


def test_orphan_present_when_frontmatter_missing(minimal_vault: Path):
    bad = minimal_vault / "40 Brain" / "bad.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("just text, no frontmatter\n")

    stats = compute_stats(minimal_vault)

    assert stats.orphan_count == 1


def test_orphan_absent_when_all_valid(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "a.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.orphan_count == 0


def test_conflict_present_with_count_and_excluded_from_totals(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "note.md", _d(0))
    _write(brain / "a.sync-conflict-20260101-000000-ABC.md", _d(0))
    _write(brain / "b.sync-conflict-20260102-000000-DEF.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.conflict_count == 2  # E05: true count, not a boolean
    assert stats.total_notes == 1  # conflicts excluded from note totals


def test_conflict_absent_is_clean(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "a.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.conflict_count == 0


# --- C29: determinism ---------------------------------------------------------


def test_same_vault_two_calls_identical(minimal_vault: Path):
    journal = minimal_vault / "10 Journal"
    _write(journal / f"{_d(-1)}.md", _d(-1))
    _write(journal / f"{_d(0)}.md", _d(0))
    _write(minimal_vault / "00 Inbox" / "old.md", _d(-15))
    _write(minimal_vault / "40 Brain" / "a.md", _d(0), tags=["x"])
    _write(minimal_vault / "40 Brain" / "b.md", _d(-2), tags=["x", "y"])

    first = compute_stats(minimal_vault)
    second = compute_stats(minimal_vault)

    assert first == second


# --- C8: full tag map (superset of top-5) ------------------------------------


def test_all_tag_counts_is_full_superset_of_top_tags(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    tag_lists = [["a"], ["a"], ["a"], ["b"], ["b"], ["c"], ["d"], ["e"], ["f"], ["g"]]
    for i, tags in enumerate(tag_lists):
        _write(brain / f"n{i}.md", _d(0), tags=tags)

    stats = compute_stats(minimal_vault)

    assert stats.all_tag_counts == {
        "a": 3,
        "b": 2,
        "c": 1,
        "d": 1,
        "e": 1,
        "f": 1,
        "g": 1,
    }
    assert set(stats.top_tags) <= set(stats.all_tag_counts.items())
    assert list(stats.all_tag_counts) == sorted(
        stats.all_tag_counts, key=lambda t: (-stats.all_tag_counts[t], t)
    )


# --- C9/C10: daily created series window --------------------------------------


def test_daily_created_window_size_and_bounds(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "a.md", _d(0))
    _write(brain / "b.md", _d(-10))
    _write(brain / "c.md", _d(-363))

    stats = compute_stats(minimal_vault)

    assert len(stats.daily_created) == 364
    keys = sorted(stats.daily_created)
    assert keys[-1] == TODAY.isoformat()
    expected_start = TODAY - timedelta(days=363)
    assert abs((date.fromisoformat(keys[0]) - expected_start).days) <= 7
    assert stats.daily_created[_d(0)] == 1
    assert stats.daily_created[_d(-10)] == 1
    assert stats.daily_created[keys[0]] == 1  # -363 lands on window start


def test_daily_created_counts_only_authored_days(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "a.md", _d(-5))
    _write(brain / "b.md", _d(-5))
    _write(brain / "c.md", _d(-100))

    stats = compute_stats(minimal_vault)

    assert stats.daily_created[_d(-5)] == 2
    assert stats.daily_created[_d(-100)] == 1
    other_days = [
        v for k, v in stats.daily_created.items() if k not in (_d(-5), _d(-100))
    ]
    assert all(v == 0 for v in other_days)


# --- C11/C12: weekly + monthly aggregation -------------------------------------


def test_weekly_created_counts_and_sorted_keys(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "a.md", _d(0))
    _write(brain / "b.md", _d(0))
    _write(brain / "c.md", _d(-30))

    stats = compute_stats(minimal_vault)

    week_today = f"{TODAY.isocalendar()[0]}-W{TODAY.isocalendar()[1]:02d}"
    old_date = TODAY - timedelta(days=30)
    week_old = f"{old_date.isocalendar()[0]}-W{old_date.isocalendar()[1]:02d}"
    assert stats.weekly_created[week_today] == 2
    assert stats.weekly_created[week_old] == 1
    assert list(stats.weekly_created) == sorted(stats.weekly_created)


def test_monthly_created_counts_and_sorted_keys(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "a.md", _d(0))
    _write(brain / "b.md", _d(0))
    _write(brain / "c.md", _d(-60))

    stats = compute_stats(minimal_vault)

    month_today = f"{TODAY.year:04d}-{TODAY.month:02d}"
    old_date = TODAY - timedelta(days=60)
    month_old = f"{old_date.year:04d}-{old_date.month:02d}"
    assert stats.monthly_created[month_today] == 2
    assert stats.monthly_created[month_old] == 1
    assert list(stats.monthly_created) == sorted(stats.monthly_created)


# --- C13: per-layer cumulative growth ------------------------------------------


def test_growth_by_layer_monotonic_and_ends_at_layer_total(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    projects = minimal_vault / "20 Projects"
    _write(brain / "a.md", _d(-10))
    _write(brain / "b.md", _d(-5))
    _write(brain / "c.md", _d(0))
    _write(projects / "p.md", _d(-2))

    stats = compute_stats(minimal_vault)

    brain_growth = stats.growth_by_layer["brain"]
    counts = [c for _, c in brain_growth]
    assert counts == sorted(counts)
    assert brain_growth[-1][1] == stats.notes_per_layer["brain"] == 3

    projects_growth = stats.growth_by_layer["projects"]
    assert projects_growth[-1][1] == stats.notes_per_layer["projects"] == 1

    assert stats.growth_by_layer["areas"] == []
    assert set(stats.growth_by_layer) == {
        "inbox",
        "journal",
        "projects",
        "areas",
        "brain",
        "archive",
    }


# --- C14: tag co-occurrence -----------------------------------------------------


def test_tag_cooccurrence_pairs_and_single_tag_excluded(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "n0.md", _d(0), tags=["a", "b", "c"])
    _write(brain / "n1.md", _d(0), tags=["a", "b"])
    _write(brain / "n2.md", _d(0), tags=["solo"])

    stats = compute_stats(minimal_vault)

    pairs = {(a, b): count for a, b, count in stats.tag_cooccurrence}
    assert pairs == {("a", "b"): 2, ("a", "c"): 1, ("b", "c"): 1}
    assert all("solo" not in (a, b) for a, b, _ in stats.tag_cooccurrence)
    assert stats.tag_cooccurrence == sorted(
        stats.tag_cooccurrence, key=lambda t: (-t[2], t[0], t[1])
    )


# --- C15: created vs updated separation ----------------------------------------


def test_daily_created_vs_updated_separation(minimal_vault: Path):
    brain = minimal_vault / "40 Brain"
    _write(brain / "x.md", created=_d(-10), updated=_d(0))
    _write(brain / "y.md", created=_d(0), updated=_d(0))

    stats = compute_stats(minimal_vault)

    assert stats.daily_created[_d(-10)] == 1
    assert stats.daily_created[_d(0)] == 1
    assert stats.daily_updated[_d(-10)] == 0
    assert stats.daily_updated[_d(0)] == 2


# --- C18: empty vault series are structurally complete -------------------------


def test_empty_vault_new_fields_zeroed(minimal_vault: Path):
    stats = compute_stats(minimal_vault)

    assert stats.all_tag_counts == {}
    assert len(stats.daily_created) == 364
    assert all(v == 0 for v in stats.daily_created.values())
    assert len(stats.daily_updated) == 364
    assert all(v == 0 for v in stats.daily_updated.values())
    assert stats.weekly_created == {}
    assert stats.monthly_created == {}
    assert stats.growth_by_layer == {k: [] for k in LAYER_KEYS}
    assert stats.tag_cooccurrence == []
    assert stats.project_status is None


# --- C25/C26/C28: project status --------------------------------------------


def _write_project(path: Path, status: str) -> None:
    _write(path, _d(0), status=status)


def test_project_status_configured_counts(minimal_vault: Path):
    _write_status_config(minimal_vault)
    projects = minimal_vault / "20 Projects"
    _write_project(projects / "p1.md", "active")
    _write_project(projects / "p2.md", "active")
    _write_project(projects / "p3.md", "stalled")

    stats = compute_stats(minimal_vault)

    assert stats.project_status == {"active": 2, "stalled": 1, "done": 0}
    # ordered per configured statuses
    assert list(stats.project_status) == ["active", "stalled", "done"]


def test_project_status_configured_but_empty(minimal_vault: Path):
    _write_status_config(minimal_vault)

    stats = compute_stats(minimal_vault)

    assert stats.project_status == {"active": 0, "stalled": 0, "done": 0}


def test_project_status_unconfigured_is_none(minimal_vault: Path):
    projects = minimal_vault / "20 Projects"
    _write_project(projects / "p1.md", "active")

    stats = compute_stats(minimal_vault)

    assert stats.project_status is None


def test_project_status_value_outside_set_not_counted(minimal_vault: Path):
    _write_status_config(minimal_vault)
    projects = minimal_vault / "20 Projects"
    _write_project(projects / "p1.md", "active")
    _write_project(projects / "p2.md", "archived")  # not in configured statuses

    stats = compute_stats(minimal_vault)

    assert stats.project_status == {"active": 1, "stalled": 0, "done": 0}


def test_project_status_coerces_non_string_values(minimal_vault: Path):
    """Unquoted YAML scalars (e.g. `status: 1`) are matched via str(), like Index.by_status."""
    (minimal_vault / "brainkeeper.yaml").write_text(
        "layers:\n"
        '  inbox: "00 Inbox"\n'
        '  journal: "10 Journal"\n'
        "  projects:\n"
        '    path: "20 Projects"\n'
        "    status_field: status\n"
        '    statuses: ["1", active]\n'
        '  areas: "30 Areas"\n'
        '  brain: "40 Brain"\n'
        '  archive: "90 Archive"\n'
    )
    # write_note emits `status: 1` unquoted, which YAML parses as int 1
    _write_project(minimal_vault / "20 Projects" / "p1.md", "1")

    stats = compute_stats(minimal_vault)

    assert stats.project_status == {"1": 1, "active": 0}
