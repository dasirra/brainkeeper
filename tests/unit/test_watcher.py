import time
from pathlib import Path

from brainkeeper.core.index import Index
from brainkeeper.core.watcher import FileWatcher


def test_create_event_updates_index(minimal_vault: Path):
    idx = Index(minimal_vault)
    idx.build()
    w = FileWatcher(minimal_vault, idx, debounce_ms=50)
    w.start()
    try:
        n = minimal_vault / "40 Brain" / "live.md"
        n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n")
        time.sleep(0.5)
        assert idx.get(n) is not None
    finally:
        w.stop()


def test_delete_event_removes_from_index(minimal_vault: Path):
    n = minimal_vault / "40 Brain" / "live.md"
    n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n")
    idx = Index(minimal_vault)
    idx.build()
    w = FileWatcher(minimal_vault, idx, debounce_ms=50)
    w.start()
    try:
        n.unlink()
        time.sleep(0.5)
        assert idx.get(n) is None
    finally:
        w.stop()
