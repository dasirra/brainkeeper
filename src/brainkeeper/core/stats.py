"""Pure vault metrics for `brainkeeper stats`. No I/O side effects beyond reading the vault."""

from __future__ import annotations

import fnmatch
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .config import ConfigLoader
from .index import Index, NoteMeta

LAYER_KEYS: tuple[str, ...] = (
    "inbox",
    "journal",
    "projects",
    "areas",
    "brain",
    "archive",
)
_CONFLICT_GLOB = "*.sync-conflict-*.md"
INBOX_ROT_DAYS = 14
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class VaultStats:
    """Snapshot of vault-wide metrics from a single one-shot index build."""

    total_notes: int
    notes_per_layer: dict[str, int]
    created_7d_per_layer: dict[str, int]
    created_30d_per_layer: dict[str, int]
    top_tags: list[tuple[str, int]]
    journal_streak: int
    inbox_oldest_age_days: int | None
    inbox_warn: bool
    orphan_count: int
    conflict_count: int


def compute_stats(vault: Path) -> VaultStats:
    """Build a one-shot Index over `vault` and derive all summary metrics.

    Sync-conflict files (`*.sync-conflict-*.md`) are counted separately and
    excluded from every other count, tag, and orphan check. Notes outside
    the six canonical layers still count toward `total_notes` but not
    toward any per-layer breakdown.
    """
    config = ConfigLoader(vault).load()
    index = Index(vault)
    index.build()

    all_paths = index.paths()
    conflict_count = sum(1 for p in all_paths if _is_conflict(p))
    real_notes: list[NoteMeta] = [
        meta
        for p in all_paths
        if not _is_conflict(p) and (meta := index.get(p)) is not None
    ]

    layer_dirs = {key: config.layer_path(key) for key in LAYER_KEYS}
    today = date.today()

    notes_per_layer = dict.fromkeys(LAYER_KEYS, 0)
    created_7d = dict.fromkeys(LAYER_KEYS, 0)
    created_30d = dict.fromkeys(LAYER_KEYS, 0)
    tag_counts: Counter[str] = Counter()
    journal_dates: set[date] = set()
    inbox_ages: list[int] = []

    for meta in real_notes:
        tags = meta.frontmatter.get("tags")
        if isinstance(tags, list):
            tag_counts.update(t for t in tags if isinstance(t, str))

        layer = _layer_for(meta.path, layer_dirs)
        if layer is None:
            continue
        notes_per_layer[layer] += 1

        created = _parse_iso_date(meta.frontmatter.get("created"))
        if created is not None:
            age = (today - created).days
            if age <= 7:
                created_7d[layer] += 1
            if age <= 30:
                created_30d[layer] += 1
            if layer == "inbox":
                inbox_ages.append(age)

        if layer == "journal":
            stem_date = _parse_iso_date(meta.path.stem)
            if stem_date is not None:
                journal_dates.add(stem_date)

    top_tags = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    inbox_oldest_age = max(inbox_ages) if inbox_ages else None

    return VaultStats(
        total_notes=len(real_notes),
        notes_per_layer=notes_per_layer,
        created_7d_per_layer=created_7d,
        created_30d_per_layer=created_30d,
        top_tags=top_tags,
        journal_streak=_compute_streak(journal_dates, today),
        inbox_oldest_age_days=inbox_oldest_age,
        inbox_warn=inbox_oldest_age is not None and inbox_oldest_age > INBOX_ROT_DAYS,
        orphan_count=sum(1 for m in real_notes if m.validation_errors),
        conflict_count=conflict_count,
    )


def _is_conflict(path: Path) -> bool:
    return fnmatch.fnmatch(path.name, _CONFLICT_GLOB)


def _layer_for(path: Path, layer_dirs: dict[str, Path]) -> str | None:
    for key, layer_path in layer_dirs.items():
        if path.is_relative_to(layer_path):
            return key
    return None


def _parse_iso_date(value: object) -> date | None:
    """Parse a strict YYYY-MM-DD string; skip anything else defensively."""
    if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _compute_streak(journal_dates: set[date], today: date) -> int:
    """Consecutive-day run ending today or yesterday; a gap breaks it."""
    if today in journal_dates:
        cursor = today
    elif today - timedelta(days=1) in journal_dates:
        cursor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while cursor in journal_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
