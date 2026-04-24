#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-frontmatter",
#     "pyyaml",
# ]
# ///
"""Read-only audit of a vault against brainkeeper spec v0.1.

Usage:
    uv run tools/audit_vault.py <vault-path> [-o <report-path>]

The report is written to ~/vault-audit-YYYY-MM-DD.md by default.
Report may contain file paths from the vault; treat as local data and do not
commit to a public repo without redacting.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import frontmatter


CANONICAL_LAYERS: tuple[str, ...] = (
    "inbox", "journal", "projects", "areas", "brain", "archive",
)
REQUIRED_FRONTMATTER_FIELDS: tuple[str, ...] = (
    "type", "status", "created", "tags",
)
ALLOWED_TYPES: frozenset[str] = frozenset((
    "project", "area", "idea", "journal",
    "meeting", "note", "resource", "knowledge",
))
ALLOWED_STATUSES: frozenset[str] = frozenset((
    "active", "paused", "completed", "archived",
))

_JD_PREFIX = re.compile(r"^\d+\s+")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DAILY_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
_MEETING_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} - .+\.md$")
_LEADING_DIGIT = re.compile(r"^\d")
_WIKILINK_RE = re.compile(r"\[\[[^\]]+\]\]")
_INTERNAL_MD_LINK_RE = re.compile(r"\]\((?!https?://|mailto:)[^)]+\.md(?:#[^)]*)?\)")
_TAG_RE = re.compile(r"^[a-z][a-z0-9-]*(/[a-z][a-z0-9-]*)*$")


@dataclass
class Check:
    """One audit check's output: a short headline + a markdown detail block."""

    name: str
    headline: str
    details: str


def _iter_top_level_dirs(vault: Path) -> list[Path]:
    return sorted(
        p for p in vault.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def _iter_markdown_files(vault: Path) -> list[Path]:
    files = []
    for p in vault.rglob("*.md"):
        rel_parts = p.relative_to(vault).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        files.append(p)
    return sorted(files)


def _map_to_canonical(dirname: str) -> str | None:
    """Map a folder name to a canonical layer key, or None."""
    stripped = _JD_PREFIX.sub("", dirname).strip().lower()
    return stripped if stripped in CANONICAL_LAYERS else None


def _layer_mappings(vault: Path) -> dict[str, Path]:
    """Build a canonical-key -> top-level folder mapping (first match wins)."""
    result: dict[str, Path] = {}
    for d in _iter_top_level_dirs(vault):
        key = _map_to_canonical(d.name)
        if key and key not in result:
            result[key] = d
    return result


def _load_frontmatter(path: Path) -> dict | None:
    """Parse frontmatter metadata; return None on unreadable/malformed file."""
    try:
        post = frontmatter.load(path)
    except Exception:
        return None
    return post.metadata or {}


def check_structure(vault: Path) -> Check:
    """Map top-level folders to canonical layer keys."""
    dirs = _iter_top_level_dirs(vault)
    mapping: dict[str, Path] = {}
    duplicates: list[tuple[str, Path]] = []
    unmatched: list[Path] = []
    for d in dirs:
        key = _map_to_canonical(d.name)
        if key is None:
            unmatched.append(d)
        elif key in mapping:
            duplicates.append((key, d))
        else:
            mapping[key] = d

    missing = [k for k in CANONICAL_LAYERS if k not in mapping]
    loose_md = sorted(
        p for p in vault.iterdir()
        if p.is_file() and p.suffix == ".md" and not p.name.startswith(".")
    )

    present = len(mapping)
    if missing:
        headline = (
            f"**{present}/{len(CANONICAL_LAYERS)} canonical layers mapped.** "
            f"Missing: {', '.join(f'`{m}`' for m in missing)}."
        )
    else:
        headline = f"**All {len(CANONICAL_LAYERS)} canonical layers present.**"

    rows = ["| Canonical key | Folder | Status |", "|---|---|---|"]
    for key in CANONICAL_LAYERS:
        folder = mapping.get(key)
        if folder is None:
            rows.append(f"| `{key}` | _missing_ | **gap** |")
        else:
            rows.append(f"| `{key}` | `{folder.name}/` | ok |")

    if unmatched:
        rows += ["", "**Unmatched top-level folders** (not in canonical set):", ""]
        rows += [f"- `{d.name}/`" for d in unmatched]

    if duplicates:
        rows += ["", "**Duplicate mappings** (two folders mapped to same key):", ""]
        rows += [f"- `{d.name}/` -> `{key}`" for key, d in duplicates]

    if loose_md:
        rows += ["", "**Loose .md files at vault root** (should live inside a layer):", ""]
        rows += [f"- `{f.name}`" for f in loose_md]

    return Check("Structure", headline, "\n".join(rows))


def check_scale(vault: Path) -> Check:
    """Count markdown files, total and per top-level folder."""
    files = _iter_markdown_files(vault)
    total = len(files)
    per_dir: Counter[str] = Counter()
    for f in files:
        per_dir[f.relative_to(vault).parts[0]] += 1

    headline = f"**{total} markdown files** under visible (non-hidden) paths."

    rows = ["| Top-level folder | .md count |", "|---|---|"]
    for name, count in per_dir.most_common():
        rows.append(f"| `{name}` | {count} |")
    rows.append(f"| **total** | **{total}** |")
    return Check("Scale", headline, "\n".join(rows))


def check_frontmatter_coverage(vault: Path) -> Check:
    """Measure presence of the 4 required frontmatter fields."""
    files = _iter_markdown_files(vault)
    total = len(files)
    if total == 0:
        return Check("Frontmatter coverage", "_No markdown files found._", "")

    any_fm = 0
    fully_compliant = 0
    missing_counter: Counter[str] = Counter()
    parse_errors: list[Path] = []

    for f in files:
        try:
            post = frontmatter.load(f)
        except Exception:
            parse_errors.append(f)
            continue

        meta = post.metadata or {}
        if meta:
            any_fm += 1

        missing_here = [
            field for field in REQUIRED_FRONTMATTER_FIELDS
            if not meta.get(field)
        ]
        if not missing_here:
            fully_compliant += 1
        else:
            for field in missing_here:
                missing_counter[field] += 1

    pct_any = 100.0 * any_fm / total
    pct_full = 100.0 * fully_compliant / total

    headline = (
        f"**{pct_any:.0f}% have any frontmatter; "
        f"{pct_full:.0f}% have all 4 required fields** "
        f"({fully_compliant}/{total} fully compliant)."
    )

    rows = ["| Required field | Missing from | Share |", "|---|---|---|"]
    for field in REQUIRED_FRONTMATTER_FIELDS:
        count = missing_counter[field]
        pct = 100.0 * count / total
        rows.append(f"| `{field}` | {count} | {pct:.0f}% |")

    if parse_errors:
        rows += ["", f"**YAML parse errors:** {len(parse_errors)} files (first 5):", ""]
        rows += [f"- `{p.relative_to(vault)}`" for p in parse_errors[:5]]

    return Check("Frontmatter coverage", headline, "\n".join(rows))


def check_enums(vault: Path) -> Check:
    """Validate `type` and `status` frontmatter values against the spec enums."""
    bad_types: list[tuple[str, Path]] = []
    bad_statuses: list[tuple[str, Path]] = []
    for f in _iter_markdown_files(vault):
        meta = _load_frontmatter(f)
        if meta is None:
            continue
        t = meta.get("type")
        if t and str(t) not in ALLOWED_TYPES:
            bad_types.append((str(t), f))
        s = meta.get("status")
        if s and str(s) not in ALLOWED_STATUSES:
            bad_statuses.append((str(s), f))

    total = len(bad_types) + len(bad_statuses)
    if total == 0:
        return Check("Enum violations", "**No enum violations.**", "")

    headline = (
        f"**{len(bad_types)} invalid `type` values, "
        f"{len(bad_statuses)} invalid `status` values.**"
    )

    lines: list[str] = []
    if bad_types:
        lines.append("**Bad `type` values:**")
        lines.append("")
        counts = Counter(v for v, _ in bad_types)
        for value, n in counts.most_common():
            examples = [
                f"`{p.relative_to(vault)}`"
                for v, p in bad_types if v == value
            ][:3]
            lines.append(f"- `{value}` ({n}): {', '.join(examples)}")
    if bad_statuses:
        if lines:
            lines.append("")
        lines.append("**Bad `status` values:**")
        lines.append("")
        counts = Counter(v for v, _ in bad_statuses)
        for value, n in counts.most_common():
            examples = [
                f"`{p.relative_to(vault)}`"
                for v, p in bad_statuses if v == value
            ][:3]
            lines.append(f"- `{value}` ({n}): {', '.join(examples)}")

    return Check("Enum violations", headline, "\n".join(lines))


def check_dates(vault: Path) -> Check:
    """Check that `created`, `deadline`, `archived` parse as YYYY-MM-DD."""
    bad: list[tuple[str, str, Path]] = []
    for f in _iter_markdown_files(vault):
        meta = _load_frontmatter(f)
        if meta is None:
            continue
        for field in ("created", "deadline", "archived"):
            v = meta.get(field)
            if v in (None, "", False):
                continue
            if not _DATE_RE.match(str(v)):
                bad.append((field, str(v), f))

    if not bad:
        return Check(
            "Date format",
            "**All non-empty date fields match `YYYY-MM-DD`.**",
            "",
        )

    headline = f"**{len(bad)} date-field violations.**"
    per_field = Counter(field for field, _, _ in bad)

    lines = ["| Field | Violations |", "|---|---|"]
    for field in ("created", "deadline", "archived"):
        lines.append(f"| `{field}` | {per_field[field]} |")
    lines.append("")
    lines.append("**Examples (first 10):**")
    lines.append("")
    for field, value, path in bad[:10]:
        lines.append(f"- `{path.relative_to(vault)}` - `{field}: {value}`")
    return Check("Date format", headline, "\n".join(lines))


def check_naming(vault: Path) -> Check:
    """Check journal filename pattern and project/area folder prefixes."""
    mappings = _layer_mappings(vault)
    journal = mappings.get("journal")
    projects = mappings.get("projects")
    areas = mappings.get("areas")

    bad_journal: list[Path] = []
    if journal and journal.is_dir():
        for f in journal.iterdir():
            if not (f.is_file() and f.suffix == ".md"):
                continue
            if f.name.startswith("."):
                continue
            if _DAILY_FILE_RE.match(f.name) or _MEETING_FILE_RE.match(f.name):
                continue
            bad_journal.append(f)

    bad_layer_folders: dict[str, list[Path]] = {}
    for key, layer_dir in (("projects", projects), ("areas", areas)):
        if not (layer_dir and layer_dir.is_dir()):
            continue
        offenders = [
            d for d in layer_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and _LEADING_DIGIT.match(d.name)
        ]
        if offenders:
            bad_layer_folders[key] = sorted(offenders)

    total = len(bad_journal) + sum(len(v) for v in bad_layer_folders.values())
    if total == 0:
        return Check("Naming", "**All naming conventions look clean.**", "")

    headline = f"**{total} naming-convention violations.**"
    lines: list[str] = []

    if bad_journal:
        lines.append(
            f"**Journal files not matching `YYYY-MM-DD.md` or "
            f"`YYYY-MM-DD - <Slug>.md` ({len(bad_journal)}):**"
        )
        lines.append("")
        for p in bad_journal[:25]:
            lines.append(f"- `{p.relative_to(vault)}`")
        if len(bad_journal) > 25:
            lines.append(f"- _... {len(bad_journal) - 25} more_")

    for key, folders in bad_layer_folders.items():
        if lines:
            lines.append("")
        lines.append(
            f"**`{key}/` subfolders with numeric prefix "
            f"(Title Case without prefix expected) ({len(folders)}):**"
        )
        lines.append("")
        for p in folders:
            lines.append(f"- `{p.relative_to(vault)}`")

    return Check("Naming", headline, "\n".join(lines))


def check_links(vault: Path) -> Check:
    """Count wikilinks vs non-compliant markdown links to local .md files."""
    wikilinks = 0
    mdlinks = 0
    files_with_mdlinks: list[tuple[Path, int]] = []
    for f in _iter_markdown_files(vault):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        wl = len(_WIKILINK_RE.findall(content))
        ml = len(_INTERNAL_MD_LINK_RE.findall(content))
        wikilinks += wl
        mdlinks += ml
        if ml:
            files_with_mdlinks.append((f, ml))

    total = wikilinks + mdlinks
    if total == 0:
        return Check("Link style", "_No internal links detected._", "")

    pct_wiki = 100.0 * wikilinks / total
    headline = (
        f"**{wikilinks} wikilinks, {mdlinks} markdown links to .md files** "
        f"({pct_wiki:.0f}% wikilink-compliant)."
    )
    if mdlinks == 0:
        return Check("Link style", headline, "")

    files_with_mdlinks.sort(key=lambda x: -x[1])
    lines = [
        f"**Top files with non-compliant markdown links "
        f"({len(files_with_mdlinks)} files total):**",
        "",
    ]
    for path, n in files_with_mdlinks[:15]:
        lines.append(f"- `{path.relative_to(vault)}` ({n})")
    if len(files_with_mdlinks) > 15:
        lines.append(f"- _... {len(files_with_mdlinks) - 15} more files_")
    return Check("Link style", headline, "\n".join(lines))


def check_tags(vault: Path) -> Check:
    """Validate tag grammar: lowercase, kebab-case, optional hierarchical `dim/value`."""
    bad: list[tuple[str, Path]] = []
    for f in _iter_markdown_files(vault):
        meta = _load_frontmatter(f)
        if meta is None:
            continue
        tags = meta.get("tags")
        if tags in (None, "", False):
            continue
        if isinstance(tags, str):
            tags = [tags]
        if not isinstance(tags, (list, tuple)):
            bad.append((f"_non-list tags: {type(tags).__name__}_", f))
            continue
        for t in tags:
            if not isinstance(t, str):
                bad.append((f"_non-string tag: {t!r}_", f))
                continue
            value = t.lstrip("#").strip()
            if not value or not _TAG_RE.match(value):
                bad.append((t, f))

    if not bad:
        return Check(
            "Tag grammar",
            "**All tags pass grammar (lowercase kebab-case, optional `dim/value`).**",
            "",
        )

    headline = f"**{len(bad)} tag-grammar violations across the vault.**"
    counts = Counter(t for t, _ in bad)
    lines = [
        f"**{len(counts)} distinct violating tag values "
        f"(top 30 by frequency):**",
        "",
    ]
    for tag, n in counts.most_common(30):
        examples = [
            f"`{p.relative_to(vault)}`"
            for t, p in bad if t == tag
        ][:3]
        lines.append(f"- `{tag}` ({n} uses): {', '.join(examples)}")
    if len(counts) > 30:
        lines.append(f"- _... {len(counts) - 30} more distinct values_")
    return Check("Tag grammar", headline, "\n".join(lines))


def check_archive(vault: Path) -> Check:
    return Check("Archive scope", "_(not implemented)_", "")


def check_templates(vault: Path) -> Check:
    return Check("Templates", "_(not implemented)_", "")


def check_cruft(vault: Path) -> Check:
    return Check("Cruft", "_(not implemented)_", "")


CHECKS: tuple = (
    check_structure,
    check_scale,
    check_frontmatter_coverage,
    check_enums,
    check_dates,
    check_naming,
    check_links,
    check_tags,
    check_archive,
    check_templates,
    check_cruft,
)


def render(vault: Path, results: list[Check]) -> str:
    today = dt.date.today().isoformat()
    lines: list[str] = [
        "# Vault audit report",
        "",
        f"- **Vault:** `{vault}`",
        f"- **Generated:** {today}",
        f"- **Checks run:** {len(results)}",
        "",
        "---",
        "",
    ]
    for i, c in enumerate(results, start=1):
        lines.extend([
            f"## {i}. {c.name}",
            "",
            c.headline,
            "",
        ])
        if c.details:
            lines.extend([c.details, ""])
    return "\n".join(lines)


def default_output_path() -> Path:
    today = dt.date.today().isoformat()
    return Path.home() / f"vault-audit-{today}.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a vault against brainkeeper spec v0.1 (read-only).",
    )
    parser.add_argument("vault", type=Path, help="Path to the vault root.")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Report output path. Default: ~/vault-audit-YYYY-MM-DD.md",
    )
    args = parser.parse_args(argv)

    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"error: vault path is not a directory: {vault}", file=sys.stderr)
        return 1

    output = (args.output or default_output_path()).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    results = [check(vault) for check in CHECKS]
    output.write_text(render(vault, results), encoding="utf-8")
    print(f"wrote report: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
