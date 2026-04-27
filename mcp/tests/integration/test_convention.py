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
