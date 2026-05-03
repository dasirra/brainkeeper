from datetime import date
from pathlib import Path

import pytest

from brainkeeper.mcp.server import BrainkeeperServer


@pytest.fixture
def srv(minimal_vault: Path) -> BrainkeeperServer:
    s = BrainkeeperServer(minimal_vault)
    s.index.build()
    return s


def _call(srv: BrainkeeperServer, tool_name: str, **kwargs):
    """Invoke a registered FastMCP tool by calling the underlying function."""
    components = srv.mcp._local_provider._components
    tool = next(
        t
        for k, t in components.items()
        if k.startswith("tool:") and t.name == tool_name
    )
    return tool.fn(**kwargs)


def test_read_convention(srv):
    out = _call(srv, "read_convention")
    assert "layers" in out
    assert out["layers"]["inbox"] == "00 Inbox"
    assert "capture_routing" in out


def test_list_layers(srv):
    out = _call(srv, "list_layers")
    keys = {layer["key"] for layer in out}
    assert keys == {"inbox", "journal", "projects", "areas", "brain", "archive"}
    journal = next(layer for layer in out if layer["key"] == "journal")
    assert journal["path"] == "10 Journal"
    assert journal["options"].get("format") == "YYYY-MM-DD.md"


def test_get_template_with_layer(srv, minimal_vault):
    tdir = minimal_vault / "10 Journal" / "_templates"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "Daily.md").write_text("# {{today}}\n")
    out = _call(srv, "get_template", name="Daily", layer="journal")
    assert out["name"] == "Daily.md"
    assert "{{today}}" in out["content"]
    assert "{{today}}" in out["variables"]


def test_get_template_search_all_layers(srv, minimal_vault):
    tdir = minimal_vault / "20 Projects" / "_templates"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "Project.md").write_text("# {{title}}\n")
    out = _call(srv, "get_template", name="Project")
    assert out["name"] == "Project.md"


def test_get_template_missing(srv):
    with pytest.raises(FileNotFoundError):
        _call(srv, "get_template", name="Nonexistent")


def test_resolve_path_with_intent(srv, minimal_vault):
    srv.config.capture_routing["idea"] = "30 Areas/Ideas/Inbox.md"
    out = _call(srv, "resolve_path", intent="idea")
    assert out["path"] == "30 Areas/Ideas/Inbox.md"
    assert out["mode"] == "append"
    assert out["anchor"] is None


def test_resolve_path_fallback_to_default(srv):
    out = _call(srv, "resolve_path", intent="unknown")
    assert out["path"] == "00 Inbox/"
    assert out["mode"] == "create"


def test_resolve_path_anchor(srv):
    srv.config.capture_routing["meeting"] = "10 Journal/{today}.md#Meetings"
    out = _call(srv, "resolve_path", intent="meeting")
    assert out["anchor"] == "Meetings"
    assert out["mode"] == "append"
    assert date.today().isoformat() in out["path"]


def test_resolve_path_today_substitution(srv):
    srv.config.capture_routing["daily"] = "10 Journal/{today}.md"
    out = _call(srv, "resolve_path", intent="daily")
    assert out["path"].endswith(f"{date.today().isoformat()}.md")
