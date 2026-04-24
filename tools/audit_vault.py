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
import sys
from dataclasses import dataclass
from pathlib import Path


CANONICAL_LAYERS: tuple[str, ...] = (
    "inbox", "journal", "projects", "areas", "brain", "archive",
)


@dataclass
class Check:
    """One audit check's output: a short headline + a markdown detail block."""

    name: str
    headline: str
    details: str


def check_structure(vault: Path) -> Check:
    return Check("Structure", "_(not implemented)_", "")


def check_scale(vault: Path) -> Check:
    return Check("Scale", "_(not implemented)_", "")


def check_frontmatter_coverage(vault: Path) -> Check:
    return Check("Frontmatter coverage", "_(not implemented)_", "")


def check_enums(vault: Path) -> Check:
    return Check("Enum violations", "_(not implemented)_", "")


def check_dates(vault: Path) -> Check:
    return Check("Date format", "_(not implemented)_", "")


def check_naming(vault: Path) -> Check:
    return Check("Naming", "_(not implemented)_", "")


def check_links(vault: Path) -> Check:
    return Check("Link style", "_(not implemented)_", "")


def check_tags(vault: Path) -> Check:
    return Check("Tag grammar", "_(not implemented)_", "")


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
