<p align="center">
  <img src="docs/branding/logo.svg" alt="brainkeeper" width="480">
</p>

# brainkeeper

[![CI](https://github.com/dasirra/brainkeeper/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/dasirra/brainkeeper/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](./pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A standard for structured Markdown Second Brain vaults, plus a Python reference implementation that exposes the vault to LLMs through the Model Context Protocol (MCP).

A brainkeeper vault is just a folder of Markdown files with YAML frontmatter, organized into six PARA-style layers (`inbox`, `journal`, `projects`, `areas`, `brain`, `archive`). The conventions are encoded once in a `brainkeeper.yaml` config at the vault root. From there, any tool that speaks the spec, including this MCP server, can read, write, and validate notes without breaking your structure.

The package ships a CLI (`brainkeeper init`, `brainkeeper serve`), an MCP server, and a Python library. It runs locally, holds no state outside your vault, and is tool-agnostic at the format layer (Obsidian, Logseq, plain editors all work).

## Quick start

### 1. Install

The recommended way to run brainkeeper is with `uvx`, which fetches and executes the package on demand without polluting your environment:

```bash
# No install needed; uvx handles it.
uvx brainkeeper --help
```

If you prefer a persistent install:

```bash
pip install brainkeeper
```

Either way, you need Python 3.11 or newer.

### 2. Bootstrap a vault

If you don't already have a brainkeeper vault, create one:

```bash
uvx brainkeeper init ~/MyVault
```

This creates the six layer directories and drops a `brainkeeper.yaml` (the minimal reference config) at the vault root. Open the YAML to adjust folder names, capture routes, and area substructure to taste. Validate against the schema at any time:

```bash
uvx check-jsonschema \
  --schemafile https://raw.githubusercontent.com/dasirra/brainkeeper/main/spec/schema/brainkeeper.schema.json \
  ~/MyVault/brainkeeper.yaml
```

### 3. Configure your MCP client

The MCP server is launched by your LLM harness over stdio. Pick the snippet for your client.

**Claude Code** (one command):

```bash
claude mcp add --scope user brainkeeper -- uvx brainkeeper serve --vault ~/MyVault
```

**Claude Desktop**: edit the config file at

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

and add:

```json
{
  "mcpServers": {
    "brainkeeper": {
      "command": "uvx",
      "args": ["brainkeeper", "serve", "--vault", "/Users/you/MyVault"]
    }
  }
}
```

Then restart Claude Desktop. Use an absolute path; `~` is not expanded inside this JSON.

**Other clients**: any MCP-capable harness that speaks stdio works. The command is `uvx brainkeeper serve --vault /absolute/path/to/vault` (or `brainkeeper serve --vault ...` if you `pip install`ed).

### 4. Verify

Once your client restarts, the LLM gains a `brainkeeper` toolset (`mcp__brainkeeper__list_layers`, `mcp__brainkeeper__find_by_tag`, etc.). Ask it something like "list the layers in my vault" or "find all notes tagged `pkm`" to confirm the connection.

## What's in the package

The `brainkeeper` distribution installs four Python modules:

| Module | Purpose |
| --- | --- |
| `brainkeeper.core` | Vault engine: parser, validator, indexer, atomic writer. Usable as a library. |
| `brainkeeper.mcp` | FastMCP server that exposes the vault to LLMs over stdio. |
| `brainkeeper.cli` | The `brainkeeper` command (`init`, `serve`). |
| `brainkeeper.spec` | Bundled spec data: `SPEC.md`, JSON Schema, reference configs. |

The CLI is the user surface. The MCP server is what your LLM talks to. The library is for anyone building their own tooling on top of brainkeeper-shaped vaults.

## MCP tool surface

The server registers thirteen tools across three layers. All vault access goes through these; bypassing them with raw filesystem tools produces non-compliant data.

**Primitives** (file operations):

| Tool | Description |
| --- | --- |
| `read_note` | Read a note. Returns parsed frontmatter, body, and mtime. |
| `list_notes` | List managed notes, optionally filtered by layer or path glob. |
| `write_note_atomic` | Create or overwrite a note. Auto-fills `created` and `updated`. |
| `move_note` | Move or rename a note. Does not rewrite wikilinks (v1 limitation). |
| `delete_note` | Delete a note. `soft=True` (default) moves it to `<archive>/<YYYY>/`. |

**Convention** (spec-aware lookups):

| Tool | Description |
| --- | --- |
| `read_convention` | Return the parsed `brainkeeper.yaml`. |
| `list_layers` | Resolve the six canonical layer keys to their on-disk folder names. |
| `get_template` | Fetch a per-layer template from `<layer>/_templates/`. |
| `resolve_path` | Map a capture intent to a target path according to the config's routing rules. |

**Semantic** (spec-level queries):

| Tool | Description |
| --- | --- |
| `find_by_tag` | Find notes by tag. Prefix match by default; exact match optional. |
| `find_orphans` | List notes that fail spec validation. |
| `validate_frontmatter` | Validate a single note against the spec contract. |
| `update_frontmatter` | Patch frontmatter fields on an existing note. Refreshes `updated`. |
| `list_tags` | List all tags in the vault, optionally filtered by prefix. |

The server's `instructions` block (sent to every connected client) covers the recommended workflow and the access rule.

## The spec

The format and lifecycle rules live in [`spec/SPEC.md`](./spec/SPEC.md). It is a standalone document. You do not need this Python package to build a brainkeeper-compatible tool: implement against the spec, validate `brainkeeper.yaml` against the [JSON Schema](./spec/schema/brainkeeper.schema.json), and you can interoperate.

The current spec version is **v0.1.4**. See [`CHANGELOG.md`](./CHANGELOG.md) for revision history. Spec and package version independently.

## Limitations

This is the first public release. Known constraints:

- **One vault per server instance.** Each MCP process serves a single `--vault`. Multi-vault setups need multiple server entries in your client config.
- **`move_note` does not rewrite wikilinks.** Inbound links to a moved note become stale until you fix them manually. Planned for a later release.
- **No always-on indexing.** The MCP runs only while its host (Claude Code, Claude Desktop, etc.) is running. There is no background daemon.
- **The MCP encodes the spec contract.** If you let an LLM use raw filesystem tools (Read, Write, Edit) on the vault path, it will produce notes that violate the frontmatter contract or land in the wrong layer. Tell your agent to use only the brainkeeper tools when working inside the vault.

## Project layout

```
brainkeeper/
├── spec/                   # the standard (versioned independently)
│   ├── SPEC.md
│   ├── schema/             # JSON Schema for brainkeeper.yaml
│   └── examples/           # reference configs
├── src/brainkeeper/
│   ├── core/               # vault engine library
│   ├── mcp/                # MCP server + tools/
│   ├── cli/                # `brainkeeper` command
│   └── spec/               # bundled spec assets (installed alongside code)
├── tests/
├── docs/                   # design notes, plans
│   └── branding/           # logo and brand assets
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## Links

- **Spec**: [`spec/SPEC.md`](./spec/SPEC.md)
- **Changelog**: [`CHANGELOG.md`](./CHANGELOG.md)
- **Issues**: <https://github.com/dasirra/brainkeeper/issues>
- **Repository**: <https://github.com/dasirra/brainkeeper>

## License

MIT. See [`LICENSE`](./LICENSE).
