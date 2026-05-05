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
    age_clause = (
        f"Filter the list to notes whose `created` frontmatter is at least "
        f"{older_than_days} days old. Compare each note's `created` date "
        f"to today's date and skip newer ones.\n"
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

1. Resolve the inbox path: call `list_layers` and pick the entry with `key="inbox"`.
2. List managed notes in that layer with `list_notes(layer="inbox")`.
{age_clause}3. For each of the first {limit} notes (in the order returned):
   - Read it with `read_note(path)`.
   - Validate the frontmatter with `validate_frontmatter(path)`. If invalid, set this note aside as "needs frontmatter" and do not propose a move.
   - Gather signals from tags, filename, and body content:
     - Tag prefixes like `project/<slug>` suggest folders inside `projects/`.
     - Tag prefixes like `area/<slug>` suggest folders inside `areas/`.
     - Filename pattern `YYYY-MM-DD` suggests `journal/`.
     - Filename ending in `Index.md` suggests an area or project entry-point.
     - Body content is context only, not authoritative.
   - Verify each candidate folder actually exists with `list_notes(layer=...)` before proposing it.
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


def register_prompts(mcp: "FastMCP", srv: "BrainkeeperServer") -> None:
    # `srv` is captured for parity with tool registration; v1 prompts are
    # static workflows that don't read live vault state at render time.
    del srv

    @mcp.prompt()
    def triage_inbox(
        older_than_days: int | None = None,
        limit: int = 20,
        dry_run: bool = True,
    ) -> str:
        """Walk the inbox layer and propose a destination for each managed note.

        The prompt returns a workflow the agent should follow using existing
        brainkeeper tools (`list_layers`, `list_notes`, `read_note`,
        `validate_frontmatter`, `move_note`, `delete_note`). It does not embed
        live inbox state.

        Args:
            older_than_days: Only triage notes whose `created` frontmatter is
                at least this many days old. Default: no age filter.
            limit: Maximum number of notes to process per invocation. Default 20.
            dry_run: When true (default), propose moves but do not apply them.
                Re-invoke with `dry_run=false` to apply after user confirmation.
        """
        return _build_triage_inbox_body(older_than_days, limit, dry_run)
