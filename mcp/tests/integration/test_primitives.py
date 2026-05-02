from pathlib import Path

import pytest

from brainkeeper_mcp.server import BrainkeeperServer


@pytest.fixture
def srv(minimal_vault: Path) -> BrainkeeperServer:
    s = BrainkeeperServer(minimal_vault)
    s.index.build()
    return s


def _call(srv: BrainkeeperServer, tool_name: str, **kwargs):
    """Invoke a registered FastMCP tool by calling the underlying function."""
    components = srv.mcp._local_provider._components
    tool = next(t for k, t in components.items() if k.startswith("tool:") and t.name == tool_name)
    return tool.fn(**kwargs)


def test_read_note_returns_frontmatter_and_content(srv, minimal_vault):
    n = minimal_vault / "40 Brain" / "note.md"
    n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\nbody")
    srv.index.update(n)
    out = _call(srv, "read_note", path="40 Brain/note.md")
    assert out["frontmatter"]["type"] == "knowledge"
    assert out["content"].strip() == "body"
    assert isinstance(out["mtime"], float)
    assert out["path"] == "40 Brain/note.md"


def test_read_note_missing_raises(srv):
    with pytest.raises(FileNotFoundError):
        _call(srv, "read_note", path="40 Brain/nope.md")


def test_list_notes_glob(srv, minimal_vault):
    a = minimal_vault / "40 Brain" / "a.md"
    a.write_text("a")
    b = minimal_vault / "30 Areas" / "b.md"
    b.write_text("b")
    srv.index.update(a); srv.index.update(b)
    out = _call(srv, "list_notes", glob="40 Brain/**/*.md")
    paths = [item["path"] for item in out]
    assert "40 Brain/a.md" in paths
    assert "30 Areas/b.md" not in paths


def test_list_notes_with_frontmatter(srv, minimal_vault):
    a = minimal_vault / "40 Brain" / "a.md"
    a.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [t/x]\n---\nx")
    srv.index.update(a)
    out = _call(srv, "list_notes", glob="40 Brain/**/*.md", with_frontmatter=True)
    [item] = out
    assert item["frontmatter"]["type"] == "knowledge"


def test_write_creates_new(srv, minimal_vault):
    out = _call(
        srv, "write_note_atomic",
        path="40 Brain/new.md",
        content="hello",
        frontmatter={"type": "knowledge", "status": "active", "created": "2026-04-27", "tags": ["topic/x"]},
    )
    assert out["created"] is True
    assert (minimal_vault / "40 Brain" / "new.md").exists()


def test_write_with_correct_mtime(srv, minimal_vault):
    n = minimal_vault / "40 Brain" / "u.md"
    n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [t/x]\n---\nold")
    srv.index.update(n)
    cur = n.stat().st_mtime
    out = _call(
        srv, "write_note_atomic",
        path="40 Brain/u.md", content="new",
        expected_mtime=cur,
    )
    assert out["created"] is False
    assert "new" in n.read_text()


def test_write_stale_mtime_rejected(srv, minimal_vault):
    from brainkeeper_mcp.fs import StaleWriteError
    n = minimal_vault / "40 Brain" / "u.md"
    n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [t/x]\n---\nold")
    srv.index.update(n)
    with pytest.raises(StaleWriteError):
        _call(srv, "write_note_atomic",
              path="40 Brain/u.md", content="new", expected_mtime=0.0)


def test_move_note(srv, minimal_vault):
    n = minimal_vault / "00 Inbox" / "x.md"
    n.write_text("---\ntype: note\nstatus: active\ncreated: 2026-04-27\ntags: [t/x]\n---\nx")
    srv.index.update(n)
    out = _call(srv, "move_note", src="00 Inbox/x.md", dst="40 Brain/x.md")
    assert not n.exists()
    assert (minimal_vault / "40 Brain" / "x.md").exists()
    assert out["from"] == "00 Inbox/x.md"
    assert out["to"] == "40 Brain/x.md"
    assert out["wikilinks_broken"] == []


def test_delete_note_soft_moves_to_archive_year(srv, minimal_vault):
    from datetime import date
    n = minimal_vault / "20 Projects" / "old.md"
    n.write_text("---\ntype: project\nstatus: completed\ncreated: 2024-01-01\ntags: [p/old]\n---\n")
    srv.index.update(n)
    out = _call(srv, "delete_note", path="20 Projects/old.md", soft=True)
    assert not n.exists()
    yr = str(date.today().year)
    moved = minimal_vault / "90 Archive" / yr / "old.md"
    assert moved.exists()
    assert out["destination"] == f"90 Archive/{yr}/old.md"


def test_delete_note_hard_unlinks(srv, minimal_vault):
    n = minimal_vault / "00 Inbox" / "trash.md"
    n.write_text("trash")
    srv.index.update(n)
    out = _call(srv, "delete_note", path="00 Inbox/trash.md", soft=False)
    assert not n.exists()
    assert out["destination"] is None


def _read_fm(path: Path) -> dict:
    import frontmatter as fm_lib
    return dict(fm_lib.load(path).metadata or {})


def test_write_autofills_created_and_updated_on_new(srv, minimal_vault):
    from datetime import date
    today = date.today().isoformat()
    _call(
        srv, "write_note_atomic",
        path="40 Brain/auto.md",
        content="body",
        frontmatter={"tags": ["topic/x"]},  # no created/updated provided
    )
    fm = _read_fm(minimal_vault / "40 Brain" / "auto.md")
    assert fm.get("created") and str(fm["created"])[:10] == today
    assert fm.get("updated") and str(fm["updated"])[:10] == today


def test_write_preserves_caller_created(srv, minimal_vault):
    from datetime import date
    today = date.today().isoformat()
    _call(
        srv, "write_note_atomic",
        path="40 Brain/caller.md",
        content="body",
        frontmatter={"tags": ["topic/x"], "created": "2024-01-15"},
    )
    fm = _read_fm(minimal_vault / "40 Brain" / "caller.md")
    assert str(fm["created"])[:10] == "2024-01-15"
    # updated still refreshed to today regardless
    assert str(fm["updated"])[:10] == today


def test_write_preserves_ondisk_created_on_overwrite(srv, minimal_vault):
    """Overwriting existing note keeps its `created` from disk if not provided."""
    from datetime import date
    today = date.today().isoformat()
    n = minimal_vault / "40 Brain" / "exist.md"
    n.write_text("---\ncreated: 2025-06-01\nupdated: 2025-06-01\ntags: [t/x]\n---\nold")
    srv.index.update(n)
    _call(
        srv, "write_note_atomic",
        path="40 Brain/exist.md",
        content="new body",
        frontmatter={"tags": ["t/x"]},  # no created
    )
    fm = _read_fm(n)
    assert str(fm["created"])[:10] == "2025-06-01"  # preserved from disk
    assert str(fm["updated"])[:10] == today          # refreshed


def test_write_no_frontmatter_writes_raw_content(srv, minimal_vault):
    _call(
        srv, "write_note_atomic",
        path="40 Brain/raw.md",
        content="just bytes",
        frontmatter=None,
    )
    text = (minimal_vault / "40 Brain" / "raw.md").read_text()
    assert text == "just bytes"
    # no auto-injected frontmatter block
    assert not text.startswith("---")
