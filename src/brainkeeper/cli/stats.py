"""Vault stats subcommand: progress, health, and structure summary."""

from __future__ import annotations

import sys

import yaml

from ..core.stats import INBOX_ROT_DAYS, LAYER_KEYS, VaultStats, compute_stats

_LAYER_LABELS = {
    "inbox": "Inbox",
    "journal": "Journal",
    "projects": "Projects",
    "areas": "Areas",
    "brain": "Brain",
    "archive": "Archive",
}


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

    lines = [
        "Progress",
        *_progress_lines(stats),
        "Health",
        *_health_lines(stats),
        "Structure",
        *_structure_lines(stats),
    ]
    print("\n".join(lines))
    return 0


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
    if stats.inbox_oldest_age_days is None:
        inbox = "OK (no inbox notes)"
    elif stats.inbox_warn:
        inbox = f"WARN oldest {stats.inbox_oldest_age_days}d (> {INBOX_ROT_DAYS}d)"
    else:
        inbox = f"OK (oldest {stats.inbox_oldest_age_days}d)"

    orphans = "OK" if stats.orphan_count == 0 else f"WARN {stats.orphan_count} found"
    conflicts = (
        "OK" if stats.conflict_count == 0 else f"WARN {stats.conflict_count} found"
    )
    return [
        f"  Inbox rot: {inbox}",
        f"  Orphans: {orphans}",
        f"  Sync conflicts: {conflicts}",
    ]


def _structure_lines(stats: VaultStats) -> list[str]:
    tags = (
        ", ".join(f"{tag} ({count})" for tag, count in stats.top_tags)
        if stats.top_tags
        else "none yet"
    )
    layers = ", ".join(
        f"{_LAYER_LABELS[key]} {stats.notes_per_layer[key]}" for key in LAYER_KEYS
    )
    return [
        f"  Top tags: {tags}",
        f"  Notes per layer: {layers}",
    ]


def _sparse_layer_counts(counts: dict[str, int]) -> str:
    parts = [f"{_LAYER_LABELS[key]} {counts[key]}" for key in LAYER_KEYS if counts[key]]
    return ", ".join(parts) if parts else "none"
