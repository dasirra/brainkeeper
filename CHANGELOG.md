# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two artifacts are versioned independently:
- **`spec-vX.Y.Z`**: the brainkeeper specification (`spec/`).
- **`brainkeeper-vX.Y.Z`**: the `brainkeeper` Python package, which contains the vault engine library, the MCP server, and the CLI.

## [brainkeeper-v0.1.0] - 2026-05-02

First public release of the `brainkeeper` Python package. Implements spec v0.1.4.

### Added
- `brainkeeper.core` vault engine library: frontmatter parser and validator, atomic writer with mtime guard, in-memory note index with watchdog-based auto-update, periodic rescanner safety net, and config loader validated against the JSON Schema.
- `brainkeeper.mcp` server (FastMCP-based, stdio transport) exposing 13 tools across three layers:
  - Layer 0 primitives (5): `read_note`, `list_notes`, `write_note_atomic`, `move_note`, `delete_note`.
  - Layer 1 convention (4): `read_convention`, `list_layers`, `get_template`, `resolve_path`.
  - Layer 2 semantic (4): `find_by_tag`, `find_orphans`, `validate_frontmatter`, `update_frontmatter`, `list_tags`.
- `brainkeeper.cli` with two subcommands: `brainkeeper init <path>` to bootstrap a vault, `brainkeeper serve --vault <path>` to run the MCP server.
- MCP server `instructions=` block surfaced to connected clients, encoding the access rule, vault concepts, workflow, and limitations.
- Spec data (`SPEC.md`, JSON Schema, examples) bundled inside the wheel via hatch `force-include`.
- Auto-managed `created` and `updated` frontmatter on every write through the MCP. `created` defaults to today on new files, preserved from disk on overwrite. `updated` is always refreshed to today.
- Archive transition (`delete_note(soft=True)`) refreshes `updated` per spec §12.

### Notes
- This package was previously developed under the name `brainkeeper-mcp`. It was renamed to `brainkeeper` for v0.1.0 and restructured into the `core`/`mcp`/`cli`/`spec` subpackages described above.
- Single-vault per server instance. Multiple vaults need multiple `mcpServers` entries with distinct names.
- `move_note` does not rewrite wikilinks (deferred to v2).

## [spec-v0.1.4] - 2026-05-02

### Changed
- **Breaking:** §7 Tag taxonomy simplified. The prescribed dimensions table (`domain/`, `topic/`, `project/`, `person/`) is removed. Tags are now plain lowercase kebab-case strings; the `prefix/value` form is still allowed but no longer prescribed. The "domain vocabulary derived from folders" mechanism is gone. There is no implicit vocabulary, just freeform tags.
- MCP `list_domains` tool removed. Folder-derived domain vocabulary is no longer a spec concept; nothing replaces this tool. Use `list_notes` + `find_by_tag` for tag exploration.
- Spec cross-references (§3, §5, §10, §15, §16) cleaned up to drop "domain" terminology.
- MCP server now ships an `instructions=` block via FastMCP that surfaces to every connected client. Encodes the access rule, vault concepts, recommended workflow, and limitations.

### Migration
- No frontmatter changes needed. Existing tags with `domain/` or any other prefix continue to validate (the grammar regex is unchanged).
- Remove any tooling that calls `list_domains` (it no longer exists).

## [spec-v0.1.3] - 2026-05-01

### Changed
- **Breaking:** frontmatter contract pared down to three required fields. `type`, `status`, `deadline`, and `archived` are no longer recognised by the spec. The new required set is `created`, `updated`, `tags`. `updated` is set to `created` on first write and refreshed to today on every edit; it MUST be ≥ `created`. Any other field is allowed and passed through unchanged under the extension rule (vault- or tool-specific concerns like lifecycle status, deadlines, or course metadata live there).
- §11 capture flow now reads an explicit *intent* from the caller instead of the `type` frontmatter field.
- §12 archive transition no longer mutates `status` or `archived` in frontmatter. Only `updated` is refreshed; the file moves to `<archive>/<YYYY>/`.
- §13 (Status semantics) removed. Status is no longer part of the spec.
- Config schema: `layers.projects.status_field` and `layers.projects.active_values` removed (they configured filtering of the now-removed `status` field).

### Migration
- Drop `type`, `status`, `deadline`, `archived` from existing notes (or keep them; they become extension fields, ignored by spec validators).
- Add `updated` to every managed note. For notes never edited since creation, set `updated: <same as created>`.
- Remove `status_field` / `active_values` from `brainkeeper.yaml` if present.

## [spec-v0.1.2] - 2026-05-01

### Changed
- `status` frontmatter field is no longer required (moved from required to optional in §6). It remains meaningful for lifecycle types (`project`, `area`, `idea`) but is typically omitted on reference types (`knowledge`, `resource`, `note`) that have no lifecycle. The enum and §13 semantics are unchanged for notes that do carry a status. Tooling SHOULD treat a missing `status` as "no lifecycle" rather than a validation error. This is a constraint relaxation; v0.1.1 notes remain compliant.

## [spec-v0.1.1] - 2026-05-01

### Changed
- **Breaking:** template directory renamed from `.templates/` to `_templates/`. The hidden dot-folder broke the Obsidian editing workflow (templates were invisible in the sidebar). The underscore prefix keeps templates visible while still marking them as meta so tooling excludes them from indexing and domain derivation. Vaults adopting v0.1.0 must rename their `<layer>/.templates/` directories to `<layer>/_templates/`.

## [spec-v0.1.0] - 2026-04-24

### Added
- Initial public draft of the `brainkeeper` specification (`spec/SPEC.md`).
- JSON Schema for `brainkeeper.yaml` (`spec/schema/brainkeeper.schema.json`).
- Three reference configs: `minimal.yaml`, `daniels-vault.yaml`, `zettelkasten.yaml`.
- Negative-test fixtures under `spec/examples/.invalid/`.
- Six-layer structural model (`inbox`, `journal`, `projects`, `areas`, `brain`, `archive`) with colocated per-layer templates under `<layer>/.templates/`.
- Archive semantics narrowed to completed projects only; retired Areas are deleted or distilled into Brain, not archived.
- Domain tags: cardinality relaxed to 0..n (optional but recommended); vocabulary derived from folders under `projects/` and `areas/` rather than an enumerated list in the config.

[spec-v0.1.4]: https://github.com/dasirra/brainkeeper/releases/tag/spec-v0.1.4
[spec-v0.1.3]: https://github.com/dasirra/brainkeeper/releases/tag/spec-v0.1.3
[spec-v0.1.2]: https://github.com/dasirra/brainkeeper/releases/tag/spec-v0.1.2
[spec-v0.1.1]: https://github.com/dasirra/brainkeeper/releases/tag/spec-v0.1.1
[spec-v0.1.0]: https://github.com/dasirra/brainkeeper/releases/tag/spec-v0.1.0
