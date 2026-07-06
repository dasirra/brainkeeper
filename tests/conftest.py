"""Shared pytest fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_vault(tmp_path: Path) -> Path:
    """Copy of the minimal-vault fixture in a tmp dir for safe mutation."""
    src = FIXTURES / "minimal-vault"
    dst = tmp_path / "vault"
    shutil.copytree(src, dst)
    # .gitkeep files are noise in tests; remove
    for kp in dst.rglob(".gitkeep"):
        kp.unlink()
    return dst


def write_note(
    path: Path,
    created: str,
    updated: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
) -> None:
    """Write a minimal frontmatter'd note at `path` for stats fixtures."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tags = tags if tags is not None else ["x"]
    updated = updated or created
    tags_yaml = "[" + ", ".join(tags) + "]"
    status_line = f"status: {status}\n" if status is not None else ""
    path.write_text(
        f"---\ncreated: {created}\nupdated: {updated}\ntags: {tags_yaml}\n"
        f"{status_line}---\nbody\n"
    )


def write_status_config(vault: Path) -> None:
    """Overwrite the vault's brainkeeper.yaml with statuses configured on projects."""
    (vault / "brainkeeper.yaml").write_text(
        "layers:\n"
        '  inbox: "00 Inbox"\n'
        "  journal:\n"
        '    path: "10 Journal"\n'
        '    format: "YYYY-MM-DD.md"\n'
        "  projects:\n"
        '    path: "20 Projects"\n'
        "    status_field: status\n"
        "    statuses: [active, stalled, done]\n"
        '  areas: "30 Areas"\n'
        '  brain: "40 Brain"\n'
        "  archive:\n"
        '    path: "90 Archive"\n'
        "    year_subfolder: true\n"
    )
