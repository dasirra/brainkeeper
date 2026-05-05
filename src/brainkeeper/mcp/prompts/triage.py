"""Prompts that guide the agent through brainkeeper workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import BrainkeeperServer


def _build_triage_inbox_body(
    older_than_days: int | None,
    limit: int,
    dry_run: bool,
) -> str:
    age_filter = (
        f"   - Filter to notes whose `created` frontmatter is at least "
        f"{older_than_days} days old (compare each `created` date to today; "
        f"skip newer ones).\n"
        if older_than_days is not None
        else ""
    )
    apply_clause = (
        "Do NOT call `move_note` or `delete_note` during this triage. "
        "Only propose. The user must re-invoke this prompt with "
        "`dry_run=false` to apply."
        if dry_run
        else "After presenting the table, ask the user to confirm in chat. "
        "On their explicit approval, apply each row: use `move_note(src, dst)` "
        "for moves and `delete_note(path, soft=True)` for archive actions. "
        "Skip any row the user rejects."
    )

    return f"""# Triage the inbox

Process notes in the brainkeeper `inbox` layer and propose a destination for each.

## Procedure

1. Call `list_layers` and capture the `path` value of the entry with `key="inbox"`. Call this `INBOX`.
2. List managed notes under that path: `list_notes(glob=f"{{INBOX}}/**/*.md")`.
{age_filter}3. For each of the first {limit} notes (in the order returned):
   - Read it with `read_note(path)`.
   - Validate the frontmatter with `validate_frontmatter(path)`. If invalid, set this note aside as "needs frontmatter" and do not propose a move.
   - Gather signals from tags, filename, and body content:
     - Tag prefixes like `project/<slug>` suggest folders inside the `projects` layer.
     - Tag prefixes like `area/<slug>` suggest folders inside the `areas` layer.
     - Filename pattern `YYYY-MM-DD` suggests `journal/`.
     - Filename ending in `Index.md` suggests an area or project entry-point.
     - Body content is context only, not authoritative.
   - To verify a candidate folder exists, list its contents with `list_notes(glob=f"{{candidate}}/**/*.md")`. Only propose paths inside folders that return at least one note (or whose parent layer you have already inspected and confirmed contains the folder).
   - Propose ONE of:
     - `move`: a path inside an *existing* folder in one of the configured layers.
     - `archive`: soft-delete (the file moves to `<archive>/<YYYY>/`).
     - `keep`: leave in inbox if no clear destination yet.

## Output

Present a markdown table to the user:

| Source | Proposal | Confidence | Reasoning |
| --- | --- | --- | --- |

Use `high`, `medium`, or `low` for confidence. Reasoning is one sentence.

After the main table, list any notes that were set aside:

**Notes needing frontmatter (skipped):** bullet list of paths.

## Constraints

- Destinations MUST be inside folders that already exist in the vault. Never propose a path that would require creating a new folder or a new layer.
- brainkeeper has no capture-routing or intent mechanism; do not invent one. The destination decision is yours, grounded in the signals listed above.
- Surface the full table to the user before applying anything.
- {apply_clause}
"""


def _coerce_optional_int(value: str | int | None) -> int | None:
    """Coerce a prompt arg to optional int. Treats None and empty string as None.

    MCP transmits prompt args as strings; some clients send `""` for unfilled
    positionals, which Pydantic cannot coerce to `int | None` directly.
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    return int(value)


def _coerce_int(value: str | int | None, default: int) -> int:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    return int(value)


def _coerce_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = value.strip().lower()
    if s == "":
        return default
    if s in ("true", "1", "yes", "y", "on"):
        return True
    if s in ("false", "0", "no", "n", "off"):
        return False
    raise ValueError(f"cannot coerce {value!r} to bool")


def register_prompts(mcp: "FastMCP", _srv: "BrainkeeperServer") -> None:
    # `_srv` is unused: v1 prompts are static workflows that do not read live
    # vault state at render time. Kept in the signature for parity with the
    # tool registration functions.

    @mcp.prompt()
    def triage_inbox(
        older_than_days: str | None = None,
        limit: str | None = None,
        dry_run: str | None = None,
    ) -> str:
        """Walk the inbox layer and propose a destination for each managed note. The prompt returns a workflow the agent follows using existing tools (`list_layers`, `list_notes`, `read_note`, `validate_frontmatter`, `move_note`, `delete_note`); it does not embed live inbox state. `older_than_days` filters to notes at least N days old (omit to disable). `limit` caps the per-invocation count (default 20). `dry_run=true` (default) forbids `move_note`/`delete_note`; pass `false` to apply after user confirmation. Args are accepted as strings to play well with MCP clients that send empty positionals."""
        days = _coerce_optional_int(older_than_days)
        n = _coerce_int(limit, 20)
        apply_dry_run = _coerce_bool(dry_run, True)
        return _build_triage_inbox_body(days, n, apply_dry_run)
