"""Pure vault metrics for `brainkeeper stats`. No I/O side effects beyond reading the vault."""

from __future__ import annotations

import fnmatch
import itertools
import re
from collections import Counter
from collections.abc import Callable
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
DAILY_WINDOW_DAYS = 364
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
    orphan_count: int
    conflict_count: int
    all_tag_counts: dict[str, int]
    daily_created: dict[str, int]
    daily_updated: dict[str, int]
    weekly_created: dict[str, int]
    monthly_created: dict[str, int]
    growth_by_layer: dict[str, list[tuple[str, int]]]
    tag_cooccurrence: list[tuple[str, str, int]]
    project_status: dict[str, int] | None


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

    conflict_count = 0
    real_notes: list[NoteMeta] = []
    for p in index.paths():
        if _is_conflict(p):
            conflict_count += 1
            continue
        meta = index.get(p)
        if meta is not None:
            real_notes.append(meta)

    layer_dirs = {key: config.layer_path(key) for key in LAYER_KEYS}
    today = date.today()

    project_opts = getattr(config.layers, "projects", None)
    status_field = getattr(project_opts, "status_field", None)
    statuses = getattr(project_opts, "statuses", None)
    project_status_counts: Counter[str] = Counter()

    notes_per_layer = dict.fromkeys(LAYER_KEYS, 0)
    created_7d = dict.fromkeys(LAYER_KEYS, 0)
    created_30d = dict.fromkeys(LAYER_KEYS, 0)
    tag_counts: Counter[str] = Counter()
    cooccurrence: Counter[tuple[str, str]] = Counter()
    journal_dates: set[date] = set()
    inbox_ages: list[int] = []
    created_counts: Counter[date] = Counter()
    updated_counts: Counter[date] = Counter()
    layer_created_counts: dict[str, Counter[date]] = {k: Counter() for k in LAYER_KEYS}

    for meta in real_notes:
        tags = meta.frontmatter.get("tags")
        normalized_tags: set[str] = set()
        if isinstance(tags, list):
            normalized_tags = {t.lstrip("#") for t in tags if isinstance(t, str)}
            tag_counts.update(normalized_tags)
        if len(normalized_tags) >= 2:
            for a, b in itertools.combinations(sorted(normalized_tags), 2):
                cooccurrence[(a, b)] += 1

        created = _parse_iso_date(meta.frontmatter.get("created"))
        if created is not None:
            created_counts[created] += 1
        updated = _parse_iso_date(meta.frontmatter.get("updated"))
        if updated is not None:
            updated_counts[updated] += 1

        layer = _layer_for(meta.path, layer_dirs)
        if layer is None:
            continue
        notes_per_layer[layer] += 1

        if created is not None:
            age = max(0, (today - created).days)
            if age <= 7:
                created_7d[layer] += 1
            if age <= 30:
                created_30d[layer] += 1
            if layer == "inbox":
                inbox_ages.append(age)
            layer_created_counts[layer][created] += 1

        if layer == "journal":
            stem_date = _parse_iso_date(meta.path.stem)
            if stem_date is not None:
                journal_dates.add(stem_date)

        if layer == "projects" and status_field and statuses:
            value = meta.frontmatter.get(status_field)
            if value in statuses:
                project_status_counts[value] += 1

    top_tags = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    all_tag_counts = dict(sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0])))
    inbox_oldest_age = max(inbox_ages) if inbox_ages else None

    project_status = (
        {s: project_status_counts.get(s, 0) for s in statuses}
        if status_field and statuses
        else None
    )

    return VaultStats(
        total_notes=len(real_notes),
        notes_per_layer=notes_per_layer,
        created_7d_per_layer=created_7d,
        created_30d_per_layer=created_30d,
        top_tags=top_tags,
        journal_streak=_compute_streak(journal_dates, today),
        inbox_oldest_age_days=inbox_oldest_age,
        orphan_count=sum(1 for m in real_notes if m.validation_errors),
        conflict_count=conflict_count,
        all_tag_counts=all_tag_counts,
        daily_created=_daily_window(created_counts, today),
        daily_updated=_daily_window(updated_counts, today),
        weekly_created=_aggregate_sorted(created_counts, _iso_week_key),
        monthly_created=_aggregate_sorted(created_counts, _month_key),
        growth_by_layer={
            layer: _cumulative_growth(layer_created_counts[layer])
            for layer in LAYER_KEYS
        },
        tag_cooccurrence=sorted(
            ((a, b, count) for (a, b), count in cooccurrence.items()),
            key=lambda t: (-t[2], t[0], t[1]),
        ),
        project_status=project_status,
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


def _daily_window(counts: Counter[date], today: date) -> dict[str, int]:
    """Zero-filled `DAILY_WINDOW_DAYS`-day window ending at `today`, ISO-date keyed."""
    start = today - timedelta(days=DAILY_WINDOW_DAYS - 1)
    return {
        (start + timedelta(days=i)).isoformat(): counts.get(
            start + timedelta(days=i), 0
        )
        for i in range(DAILY_WINDOW_DAYS)
    }


def _iso_week_key(d: date) -> str:
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _aggregate_sorted(
    counts: Counter[date], key_fn: Callable[[date], str]
) -> dict[str, int]:
    """Bucket `counts` by `key_fn`, over all dates present, keys sorted ascending."""
    buckets: Counter[str] = Counter()
    for d, n in counts.items():
        buckets[key_fn(d)] += n
    return dict(sorted(buckets.items()))


def _cumulative_growth(counts: Counter[date]) -> list[tuple[str, int]]:
    """Date-ascending cumulative count at each distinct date; `[]` if none."""
    cumulative = 0
    entries = []
    for d in sorted(counts):
        cumulative += counts[d]
        entries.append((d.isoformat(), cumulative))
    return entries


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
