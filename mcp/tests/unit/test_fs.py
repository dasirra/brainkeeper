from pathlib import Path

import pytest

from brainkeeper_mcp.fs import AtomicWriter, StaleWriteError


def test_writes_new_file(tmp_path: Path):
    f = tmp_path / "n.md"
    w = AtomicWriter()
    mtime = w.write_atomic(f, "hello")
    assert f.read_text() == "hello"
    assert isinstance(mtime, float)


def test_overwrite_with_correct_expected_mtime(tmp_path: Path):
    f = tmp_path / "n.md"
    w = AtomicWriter()
    w.write_atomic(f, "first")
    cur = f.stat().st_mtime
    w.write_atomic(f, "second", expected_mtime=cur)
    assert f.read_text() == "second"


def test_stale_write_raises(tmp_path: Path):
    f = tmp_path / "n.md"
    w = AtomicWriter()
    w.write_atomic(f, "first")
    with pytest.raises(StaleWriteError):
        w.write_atomic(f, "second", expected_mtime=0.0)
    # original content preserved
    assert f.read_text() == "first"


def test_uses_tmp_then_rename(tmp_path: Path):
    """No partially-written file is ever visible at target path."""
    f = tmp_path / "n.md"
    w = AtomicWriter()
    w.write_atomic(f, "x")
    # No leftover .tmp files
    leftovers = list(tmp_path.glob("*.tmp*"))
    assert leftovers == []
