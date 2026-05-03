from pathlib import Path

from brainkeeper.core.index import Index
from brainkeeper.core.rescanner import PeriodicRescanner


def test_rescan_picks_up_added_file(minimal_vault: Path):
    idx = Index(minimal_vault)
    idx.build()
    rs = PeriodicRescanner(minimal_vault, idx, interval_seconds=999)
    n = minimal_vault / "40 Brain" / "added.md"
    n.write_text(
        "---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n"
    )
    assert idx.get(n) is None
    rs.rescan_once()
    assert idx.get(n) is not None


def test_rescan_removes_deleted_file(minimal_vault: Path):
    n = minimal_vault / "40 Brain" / "del.md"
    n.write_text(
        "---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n"
    )
    idx = Index(minimal_vault)
    idx.build()
    assert idx.get(n) is not None
    n.unlink()
    rs = PeriodicRescanner(minimal_vault, idx, interval_seconds=999)
    rs.rescan_once()
    assert idx.get(n) is None
