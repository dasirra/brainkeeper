"""Unit tests for `compute_stats` (core/stats.py) against contract criteria."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from freezegun import freeze_time

from brainkeeper.core.stats import compute_stats

TODAY = date(2025, 6, 15)


@pytest.fixture(autouse=True)
def _frozen_today():
    with freeze_time(TODAY.isoformat()):
        yield


def _d(delta: int) -> str:
    """ISO date string `delta` days from the frozen today (negative = past)."""
    return (TODAY + timedelta(days=delta)).isoformat()


def _write(
    path: Path,
    created: str,
    updated: str | None = None,
    tags: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tags = tags if tags is not None else ["x"]
    updated = updated or created
    tags_yaml = "[" + ", ".join(tags) + "]"
    path.write_text(
        f"---\ncreated: {created}\nupdated: {updated}\ntags: {tags_yaml}\n---\nbody\n"
    )


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

    assert stats.inbox_warn is expect_warn
    assert stats.inbox_oldest_age_days == age_days


def test_inbox_oldest_age_is_numeric_max(minimal_vault: Path):
    inbox = minimal_vault / "00 Inbox"
    _write(inbox / "old.md", _d(-15))
    _write(inbox / "new.md", _d(-3))

    stats = compute_stats(minimal_vault)

    assert stats.inbox_oldest_age_days == 15
    assert stats.inbox_warn is True


def test_inbox_empty_has_no_age(minimal_vault: Path):
    _write(minimal_vault / "40 Brain" / "a.md", _d(0))

    stats = compute_stats(minimal_vault)

    assert stats.inbox_oldest_age_days is None
    assert stats.inbox_warn is False


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
