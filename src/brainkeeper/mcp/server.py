"""FastMCP server wiring + tool registration."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from ..core.config import Config, ConfigLoader
from ..core.fs import AtomicWriter
from ..core.index import Index
from ..core.rescanner import PeriodicRescanner
from ..core.watcher import FileWatcher
from .prompts.triage import register_prompts
from .tools.convention import register_convention
from .tools.primitives import register_primitives
from .tools.semantic import register_semantic


INSTRUCTIONS = """\
brainkeeper MCP: structured markdown vault following the brainkeeper spec.

## Access rule

ALL vault access goes through these tools. Do NOT use filesystem tools
(Read, Write, Edit, Glob, Grep, Bash) on the vault path. The MCP encodes
the spec contract and bypassing it produces non-compliant data.

## Vault concepts

- **Six canonical layers** keyed by: `inbox, journal, projects, areas,
  brain, archive`. Resolve folder names via `list_layers` or
  `read_convention`. Never hardcode them.
- **Tags are the only classification axis.** Each managed note carries
  ≥1 tag. Tags are freeform strings, lowercase kebab-case (e.g. `mcp`,
  `pkm`, `obsidian`). A `prefix/value` form is allowed but not
  prescribed; use it if it helps you find notes later, skip it if it
  doesn't.
- **Frontmatter minimum**: every managed note requires `created` (ISO
  date), `updated` (ISO date, ≥ created), and `tags` (≥1 entry). Any
  other field is allowed and passed through unchanged.
- **`_templates/` is meta.** Templates live in `<layer>/_templates/`.
  They are excluded from indexing and content queries.

## Recommended workflow

- **Capture a new note**: pick a target path inside the appropriate
  layer (use `list_layers` if uncertain), optionally call
  `get_template(name)` for the layer's template, then
  `write_note_atomic(path, content, frontmatter)`. The tool auto-fills
  `created` (today on new file, on-disk value preserved on overwrite)
  and `updated` (always today). Do not compute these yourself.
- **Read content**: `read_note(path)`. Returns parsed frontmatter,
  content, mtime.
- **Find by tag**: `find_by_tag(tag, prefix_match=True)`. Default is
  literal prefix match (startswith); use `prefix_match=False` for exact.
  A leading `#` is normalized.
- **Hygiene**: `find_orphans()` returns every note failing spec
  validation; `validate_frontmatter(path)` checks a single note.
- **Explore**: `list_layers`, `list_notes`, `read_convention`.

## Defaults & limitations

- When the appropriate destination is not obvious, write to the `inbox`
  layer and triage later.
- `delete_note(soft=True)` archives to `<archive>/<YYYY>/`.
- `move_note` does NOT rewrite wikilinks (v1).
- Unknown template variables `{{var}}` are left untouched on
  substitution.
"""


class BrainkeeperServer:
    """Holds infrastructure + the FastMCP instance with tools registered."""

    def __init__(self, vault: Path) -> None:
        self.vault = Path(vault)
        self.config: Config = ConfigLoader(self.vault).load()
        self.index = Index(self.vault)
        self.writer = AtomicWriter()
        self.watcher = FileWatcher(self.vault, self.index)
        self.rescanner = PeriodicRescanner(self.vault, self.index)
        self.mcp = FastMCP("brainkeeper", instructions=INSTRUCTIONS)
        register_primitives(self.mcp, self)
        register_convention(self.mcp, self)
        register_semantic(self.mcp, self)
        register_prompts(self.mcp, self)

    def start_infrastructure(self) -> None:
        self.index.build()
        self.watcher.start()
        self.rescanner.start()

    def stop_infrastructure(self) -> None:
        self.rescanner.stop()
        self.watcher.stop()

    def run_stdio(self) -> None:
        self.start_infrastructure()
        try:
            self.mcp.run()
        finally:
            self.stop_infrastructure()
