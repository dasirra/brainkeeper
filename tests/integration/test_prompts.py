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
    # Procedure mentions the right tools with their actual signatures.
    assert "list_layers" in body
    assert "list_notes(glob=" in body  # not list_notes(layer=...) which doesn't exist
    assert "read_note(path)" in body
    assert "validate_frontmatter(path)" in body
    # Default limit propagates.
    assert "first 20 notes" in body
    # Default dry_run guards against accidental writes.
    assert "Do NOT call `move_note`" in body
    # Constraint phrases are present.
    assert "folders that already exist" in body
    assert "capture-routing" in body or "capture_routing" in body


async def test_triage_inbox_does_not_reference_nonexistent_tool_args(srv):
    """Regression: an earlier draft instructed `list_notes(layer=...)` which
    is not a real signature (the tool only accepts `glob` and `with_frontmatter`).
    """
    body = await _render(srv, "triage_inbox")
    assert "list_notes(layer=" not in body


async def test_triage_inbox_apply_mode(srv):
    body = await _render(srv, "triage_inbox", dry_run="false")
    # Apply path activates explicit confirmation language.
    assert "ask the user to confirm" in body
    assert "move_note(src, dst)" in body
    assert "delete_note(path, soft=True)" in body
    # Dry-run guard text must NOT appear in apply mode.
    assert "Do NOT call `move_note`" not in body


async def test_triage_inbox_age_filter(srv):
    body = await _render(srv, "triage_inbox", older_than_days="7")
    assert "at least 7 days old" in body


async def test_triage_inbox_limit_propagates(srv):
    body = await _render(srv, "triage_inbox", limit="5")
    assert "first 5 notes" in body
    assert "first 20 notes" not in body


async def test_triage_inbox_no_new_folders_constraint(srv):
    body = await _render(srv, "triage_inbox")
    assert "Never propose a path that would require creating a new folder" in body


async def test_triage_inbox_string_arg_coercion(srv):
    """MCP transmits prompt args as strings over the wire. Verify the
    coercion helpers handle the string forms correctly.
    """
    body = await _render(
        srv,
        "triage_inbox",
        dry_run="false",
        limit="5",
        older_than_days="7",
    )
    assert "ask the user to confirm" in body
    assert "first 5 notes" in body
    assert "at least 7 days old" in body


async def test_triage_inbox_empty_string_args_use_defaults(srv):
    """Regression: some MCP clients send empty strings for unfilled positional
    args. Empty strings must be treated as "use default" rather than failing
    Pydantic int coercion.
    """
    body = await _render(
        srv,
        "triage_inbox",
        older_than_days="",
        limit="",
        dry_run="",
    )
    # Defaults applied: no age filter, limit=20, dry_run=true.
    # The age-filter sub-bullet is the only line with "days old"; absent here.
    assert "days old" not in body
    assert "first 20 notes" in body
    assert "Do NOT call `move_note`" in body  # dry_run default is true


async def test_triage_inbox_bool_coercion_variants(srv):
    """Verify common boolean-string variants for dry_run."""
    for false_value in ("false", "False", "0", "no", "off"):
        body = await _render(srv, "triage_inbox", dry_run=false_value)
        assert "ask the user to confirm" in body, (
            f"dry_run={false_value!r} should disable dry-run mode"
        )
    for true_value in ("true", "True", "1", "yes", "on"):
        body = await _render(srv, "triage_inbox", dry_run=true_value)
        assert "Do NOT call `move_note`" in body, (
            f"dry_run={true_value!r} should keep dry-run mode"
        )
