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
