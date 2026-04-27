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
