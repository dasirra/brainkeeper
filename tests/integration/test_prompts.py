from pathlib import Path

import pytest

from brainkeeper.mcp.server import BrainkeeperServer


@pytest.fixture
def srv(minimal_vault: Path) -> BrainkeeperServer:
    s = BrainkeeperServer(minimal_vault)
    s.index.build()
    return s


def _find_prompt(srv: BrainkeeperServer, name: str):
    components = srv.mcp._local_provider._components
    return next(
        c for k, c in components.items() if k.startswith("prompt:") and c.name == name
    )


async def _render(srv: BrainkeeperServer, name: str, **kwargs) -> str:
    prompt = _find_prompt(srv, name)
    result = await prompt.render(kwargs)
    # PromptResult.messages is a list of Message; collect their text content.
    return "\n".join(
        msg.content.text for msg in result.messages if hasattr(msg.content, "text")
    )


def test_triage_inbox_registered(srv):
    prompt = _find_prompt(srv, "triage_inbox")
    assert prompt is not None
    assert "inbox" in (prompt.description or "").lower()


async def test_triage_inbox_default_render(srv):
    body = await _render(srv, "triage_inbox")
    # Procedure mentions the right tools.
    assert "list_layers" in body
    assert "list_notes" in body
    assert "read_note" in body
    assert "validate_frontmatter" in body
    # Default limit propagates.
    assert "first 20 notes" in body
    # Default dry_run guards against accidental writes.
    assert "Do NOT call `move_note`" in body
    # Constraint phrases are present.
    assert "folders that already exist" in body
    assert "capture-routing" in body or "capture_routing" in body


async def test_triage_inbox_apply_mode(srv):
    body = await _render(srv, "triage_inbox", dry_run=False)
    # Apply path activates explicit confirmation language.
    assert "ask the user to confirm" in body
    assert "move_note(src, dst)" in body
    assert "delete_note(path, soft=True)" in body
    # Dry-run guard text must NOT appear in apply mode.
    assert "Do NOT call `move_note`" not in body


async def test_triage_inbox_age_filter(srv):
    body = await _render(srv, "triage_inbox", older_than_days=7)
    assert "at least 7 days old" in body


async def test_triage_inbox_limit_propagates(srv):
    body = await _render(srv, "triage_inbox", limit=5)
    assert "first 5 notes" in body
    assert "first 20 notes" not in body


async def test_triage_inbox_no_new_folders_constraint(srv):
    body = await _render(srv, "triage_inbox")
    assert "Never propose a path that would require creating a new folder" in body
