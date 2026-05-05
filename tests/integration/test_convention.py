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
    assert "capture_routing" not in out


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


def test_resolve_path_tool_removed(srv):
    """resolve_path was removed in v0.2.0; verify it's not registered."""
    components = srv.mcp._local_provider._components
    tool_names = {t.name for k, t in components.items() if k.startswith("tool:")}
    assert "resolve_path" not in tool_names
