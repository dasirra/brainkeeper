"""Vault stats subcommand: progress, health, and structure summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from ..core.stats import (
    INBOX_ROT_DAYS,
    LAYER_KEYS,
    LAYER_LABELS,
    VaultStats,
    compute_stats,
    inbox_state,
)
from .report import render_report


def run(args) -> int:
    vault = args.vault
    if not vault.is_dir():
        print(
            f"error: no vault at {vault}. Run `brainkeeper init` to create it.",
            file=sys.stderr,
        )
        return 1

    try:
        stats = compute_stats(vault)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(
            f"error: could not read vault config ({exc}). "
            "Run `brainkeeper init` to create or repair it.",
            file=sys.stderr,
        )
        return 1

    html_requested = args.html is not None
    if html_requested:
        path = Path(args.html)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_report(stats), encoding="utf-8")
        except OSError as exc:
            print(f"error: could not write report to {path!r} ({exc})", file=sys.stderr)
            return 1
    if args.json:
        print(json.dumps(stats_json(stats), indent=2))
    if html_requested:
        print(str(path), file=sys.stderr if args.json else sys.stdout)
    if args.json or html_requested:
        return 0

    lines = [
        "Progress",
        *_progress_lines(stats),
        "Health",
        *_health_lines(stats),
        *(
            ["Project status", *_project_status_lines(stats)]
            if stats.project_status is not None
            else []
        ),
        "Structure",
        *_structure_lines(stats),
    ]
    print("\n".join(lines))
    return 0


def stats_json(stats: VaultStats) -> dict:
    """Serialize `stats` to the full JSON document (superset of the terminal view)."""
    payload = {
        "total_notes": stats.total_notes,
        "notes_per_layer": stats.notes_per_layer,
        "created_7d_per_layer": stats.created_7d_per_layer,
        "created_30d_per_layer": stats.created_30d_per_layer,
        "journal_streak": stats.journal_streak,
        "health": {
            "inbox_oldest_age_days": stats.inbox_oldest_age_days,
            "orphan_count": stats.orphan_count,
            "conflict_count": stats.conflict_count,
        },
        "top_tags": stats.top_tags,
        "tag_counts": stats.all_tag_counts,
        "tag_cooccurrence": stats.tag_cooccurrence,
        "series": {
            "daily_created": stats.daily_created,
            "daily_updated": stats.daily_updated,
            "weekly_created": stats.weekly_created,
            "monthly_created": stats.monthly_created,
            "growth_by_layer": stats.growth_by_layer,
        },
    }
    if stats.project_status is not None:
        payload["project_status"] = stats.project_status
    return payload


def _progress_lines(stats: VaultStats) -> list[str]:
    streak = (
        f"{stats.journal_streak} days"
        if stats.journal_streak
        else "0 days (no entries yet)"
    )
    return [
        f"  Total notes: {stats.total_notes}",
        f"  Created last 7 days: {sum(stats.created_7d_per_layer.values())} "
        f"({_sparse_layer_counts(stats.created_7d_per_layer)})",
        f"  Created last 30 days: {sum(stats.created_30d_per_layer.values())} "
        f"({_sparse_layer_counts(stats.created_30d_per_layer)})",
        f"  Journal streak: {streak}",
    ]


def _health_lines(stats: VaultStats) -> list[str]:
    age = stats.inbox_oldest_age_days
    state = inbox_state(age)
    if state == "empty":
        inbox = "OK (no inbox notes)"
    elif state == "rotting":
        inbox = f"WARN oldest {age}d (> {INBOX_ROT_DAYS}d)"
    else:
        inbox = f"OK (oldest {age}d)"

    orphans = "OK" if stats.orphan_count == 0 else f"WARN {stats.orphan_count} found"
    conflicts = (
        "OK" if stats.conflict_count == 0 else f"WARN {stats.conflict_count} found"
    )
    return [
        f"  Inbox rot: {inbox}",
        f"  Orphans: {orphans}",
        f"  Sync conflicts: {conflicts}",
    ]


def _project_status_lines(stats: VaultStats) -> list[str]:
    return [f"  {status}: {count}" for status, count in stats.project_status.items()]


def _structure_lines(stats: VaultStats) -> list[str]:
    tags = (
        ", ".join(f"{tag} ({count})" for tag, count in stats.top_tags)
        if stats.top_tags
        else "none yet"
    )
    layers = ", ".join(
        f"{LAYER_LABELS[key]} {stats.notes_per_layer[key]}" for key in LAYER_KEYS
    )
    return [
        f"  Top tags: {tags}",
        f"  Notes per layer: {layers}",
    ]


def _sparse_layer_counts(counts: dict[str, int]) -> str:
    parts = [f"{LAYER_LABELS[key]} {counts[key]}" for key in LAYER_KEYS if counts[key]]
    return ", ".join(parts) if parts else "none"
