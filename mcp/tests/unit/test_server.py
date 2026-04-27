from pathlib import Path

from brainkeeper_mcp.server import BrainkeeperServer


def test_server_constructs(minimal_vault: Path):
    srv = BrainkeeperServer(vault=minimal_vault)
    assert srv.vault == minimal_vault
    assert srv.config.layers.inbox.path == "00 Inbox"
    assert srv.index is not None
    assert srv.mcp is not None


def test_server_starts_and_indexes_existing_notes(minimal_vault: Path):
    n = minimal_vault / "40 Brain" / "preexisting.md"
    n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n")
    srv = BrainkeeperServer(vault=minimal_vault)
    srv.start_infrastructure()
    try:
        assert srv.index.get(n) is not None
    finally:
        srv.stop_infrastructure()
