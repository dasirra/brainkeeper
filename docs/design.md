---
type: note
created: 2026-04-24
tags: [topic/mcp, topic/pkm, topic/obsidian, topic/design]
---

# brainkeeper - Design Document

**Status:** Draft, pending approval
**Date:** 2026-04-24
**Owner:** Daniel Sierra

## 1. Project overview

### 1.1 What we are building

Two linked artifacts, shipped together:

1. **`brainkeeper` spec.** A public standard defining the shape of a structured Second Brain vault. PARA-inspired, extended with Journal, System, numbered prefixes, hierarchical tags, and an explicit frontmatter contract. A single `SPEC.md` plus a JSON Schema for the config file. Tool-agnostic (not tied to Obsidian).
2. **`brainkeeper-mcp`.** A Python reference implementation. An MCP server that reads a `brainkeeper.yaml` config from a vault and enforces the spec through typed tool calls. Ships on PyPI, runs via `uvx`.

### 1.2 Why

- Milestone M1.2 of the 26-week LLM roadmap (public MCP artifact).
- Daily dogfooding: Daniel uses Obsidian + a structured vault already; the MCP plus spec formalize and automate the conventions.
- Future agent reuse: Phase 3 agents will consume this MCP.
- Publishable content: two articles (spec design, MCP implementation).

### 1.3 Scope

**In v1 (medium scope):** Layer 0 primitives, Layer 1 convention loader + domain mutations, Layer 2 semantic ops (capture, archive, promote, find queries, hygiene). 27 tools total.

**Deferred to v2:**
- Link graph (backlinks, outlinks, related notes)
- Vault-wide wikilink rewriting on move
- Full-text content search
- Obsidian URL scheme hook
- Domain-specific tools for Projects, Areas, and Brain (project_dashboard, kickoff_project, add_knowledge, etc.)

### 1.4 Budget

~40 hours across 3 weeks. Fits within the ~80h Phase 1 MCP budget of the roadmap.

## 2. Repository layout

Single monorepo at `github.com/dasirra/brainkeeper`:

```
brainkeeper/
├── README.md                     # project landing page
├── CHANGELOG.md
├── spec/
│   ├── SPEC.md                   # the canonical spec document
│   ├── schema/
│   │   └── brainkeeper.schema.json   # JSON Schema for brainkeeper.yaml
│   └── examples/
│       ├── daniels-vault.yaml    # reference config
│       ├── minimal.yaml          # smallest valid config
│       └── zettelkasten.yaml     # alternative style
├── mcp/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/brainkeeper_mcp/
│   │   ├── __init__.py
│   │   ├── server.py             # FastMCP entry
│   │   ├── cli.py                # entry point
│   │   ├── config.py             # config loader + JSON Schema validator
│   │   ├── index.py              # in-memory index
│   │   ├── watcher.py            # watchdog wrapper
│   │   ├── rescanner.py          # periodic full rescan
│   │   ├── fs.py                 # atomic write, mtime check
│   │   ├── frontmatter.py        # parser + validator
│   │   └── tools/
│   │       ├── primitives.py     # Layer 0
│   │       ├── convention.py     # Layer 1
│   │       └── semantic.py       # Layer 2
│   └── tests/
│       ├── unit/
│       ├── integration/
│       ├── spec/
│       └── fixtures/
│           ├── minimal-vault/
│           ├── anon-vault/       # anonymized snapshot
│           └── broken-vault/
└── docs/
    └── articles/                 # drafts of both articles
```

**Why monorepo:** single source of truth for spec and implementation (prevents drift), solo-maintainer friendly, atomic PRs across spec and code, citability is not lost (spec is still a markdown file that anyone can link). If a second independent implementation ever appears, extract `spec/` via `git filter-repo`.

**Publishing:**
- `brainkeeper-mcp` to PyPI (built from `mcp/`).
- Spec lives at `github.com/dasirra/brainkeeper/blob/main/spec/SPEC.md`, tagged via git.

## 3. Spec contents

A single `SPEC.md` of roughly 8 to 10 pages plus a JSON Schema file. 16 numbered sections organized in four parts.

### Part I - Structure

1. **Layers** - the six numbered folders (00 Inbox, 10 Journal, 20 Projects, 30 Areas, 40 Brain, 90 System) and their purpose.
2. **Numbered prefixes** - Johnny Decimal-inspired. 00/10/20/30/40/90 with gaps for expansion (50, 60, 70, 80).
3. **Reserved paths** - what the MCP auto-creates if missing (the six layer folders, `90 System/Archive/`, `90 System/Templates/`).
4. **Area substructure** - soft convention. Areas may have subfolders for domain-specific structure (Finanzas, Pipeline, Portfolio, Research). Allowed, not required.
5. **Bilingual, language-agnostic** - folder names are user-configurable strings in `brainkeeper.yaml`. Internal references use semantic keys (`layers.projects`), not literals.

### Part II - Content model

6. **Frontmatter contract** - required fields for managed notes:

    ```yaml
    ---
    type: project              # project | area | idea | journal | meeting | note | resource | knowledge
    status: active             # active | paused | completed | archived
    created: 2026-04-24
    deadline: 2026-06-30       # optional
    archived: null             # set on archival
    tags:                      # REQUIRED, min 1
      - topic/mcp
      - project/brainkeeper
    ---
    ```

7. **Tag taxonomy** - hierarchical, prescribed dimensions, open values:
    - Required: `domain/*` (fixed enum from config, extensible by edit).
    - Optional but recommended: `topic/*`, `project/*`, `person/*`.
    - Rules: lowercase, kebab-case, singular, at least 1 tag per doc, YAML list form without `#` prefix.
    - Principle: tag what the folder does not already encode.

8. **Naming conventions**
    - Dates: `YYYY-MM-DD` everywhere.
    - Daily notes: `10 Journal/YYYY-MM-DD.md`.
    - Meeting notes: `10 Journal/YYYY-MM-DD - <Slug>.md` (separate file, linked from the day's journal).
    - Index files: `<Name> Index.md` (reserved suffix).
    - Project/Area folders: Title Case, no prefixes.
    - Note filenames: Title Case with spaces.

9. **Linking convention**
    - Wikilinks only (`[[Note Name]]` or `[[Path/To/Note|Alias]]`).
    - No markdown links for internal references.
    - Relative paths when disambiguation is needed.

10. **Template contract** - templates live in `90 System/Templates/`:
    - `Daily.md`, `Project.md`, `Area Index.md`, `Idea.md`, `Meeting.md`.
    - Support simple `{{variable}}` substitution: `{{date}}`, `{{title}}`, `{{today}}`.

### Part III - Lifecycle

11. **Classification rules** - when creating a new note, it goes to `00 Inbox` unless a specific destination is obvious.

12. **Transition rules** - the only layer-to-layer moves the spec blesses:

    | From | To | Trigger |
    |---|---|---|
    | `00 Inbox` | any | Triage |
    | `30 Areas/Ideas` | `20 Projects` | Idea matures |
    | `20 Projects` | `90 System/Archive/YYYY` | Completed or abandoned |
    | `30 Areas/<Area>` | `90 System/Archive/YYYY` | Area retired |

13. **Status semantics** - active, paused, completed, archived. Represented in frontmatter `status` field. Archive also sets `archived: YYYY-MM-DD` frontmatter.

### Part IV - Implementation notes

14. **Config file format** - `brainkeeper.yaml` at vault root. Validated against `brainkeeper.schema.json`. Example structure:

    ```yaml
    layers:
      inbox: "00 Inbox"
      journal:
        path: "10 Journal"
        format: "YYYY-MM-DD.md"
        template: "90 System/Templates/Daily.md"
      projects:
        path: "20 Projects"
        status_field: status
        active_values: ["active", "🟢"]
      areas:
        path: "30 Areas"
      brain:
        path: "40 Brain"
      system:
        path: "90 System"
      archive:
        path: "90 System/Archive"
        year_subfolder: true
      templates: "90 System/Templates"

    domains:
      - freelance
      - fitizens
      - learning
      - teaching
      - content
      - personal
      - family
      - homelab
      - ideas

    capture_routing:
      idea:    "30 Areas/Ideas/Inbox.md"
      todo:    "00 Inbox/Todos.md"
      meeting: "10 Journal/{today}.md#Meetings"
      default: "00 Inbox/"
    ```

15. **Extension points** - adding new layers, templates, or domain tags is a config edit. The MCP code never needs to change.

16. **Obsidian notes** - the spec is tool-agnostic. No dependency on Obsidian. Compatibility notes only: wikilink syntax is Obsidian-compatible, frontmatter is Obsidian-compatible, folder names are arbitrary strings.

## 4. MCP architecture

### 4.1 Three-layer model

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 2 - Semantic ops (16 tools)                           │
│ capture, append_to_journal, archive_entry, promote,         │
│ find_by_status, find_by_tag, find_by_type, find_orphans,    │
│ validate_frontmatter, suggest_tags, list_tags,              │
│ detect_conflicts, vault_stats, update_frontmatter,          │
│ create_note, create_daily_note                              │
└─────────────────────────┬───────────────────────────────────┘
                          │ composes L0/L1
┌─────────────────────────▼───────────────────────────────────┐
│ Layer 1 - Convention (6 tools)                              │
│ read_convention, resolve_path, get_template, list_layers,   │
│ list_domains, add_domain                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ reads brainkeeper.yaml
┌─────────────────────────▼───────────────────────────────────┐
│ Layer 0 - Primitives (5 tools)                              │
│ read_note, write_note_atomic, move_note, list_notes,        │
│ delete_note                                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │ uses
┌─────────────────────────▼───────────────────────────────────┐
│ Infrastructure (internal, not exposed as MCP tools)         │
│ Index, FileWatcher, PeriodicRescanner,                      │
│ AtomicWriter, FrontmatterParser, ConfigLoader               │
└──────────────────────────────────────────────────────────────┘
```

**Rule:** Layer N only calls Layer N-1 or infrastructure. No upward calls, no peer cross-calls.

**All three layers are exposed as MCP tools.** Clients can call any layer directly. Fast paths exist for callers who know what they want; semantic ops exist for callers who delegate routing to brainkeeper.

### 4.2 Infrastructure components

- **`ConfigLoader`** - loads `brainkeeper.yaml` at startup, validates against JSON Schema, watches the file for live reload. Exposes a typed `Config` (pydantic model).
- **`Index`** - in-memory `dict[Path, NoteMeta]` where `NoteMeta = { path, frontmatter: dict, mtime: float, content_hash: str }`. Thread-safe via `RLock`. Queries: `by_tag`, `by_status`, `by_type`, `orphans`.
- **`FileWatcher`** - wraps `watchdog.Observer`. On create, modify, delete events, re-parses the changed file and updates Index. Debounced 200 ms to coalesce rapid Syncthing writes.
- **`PeriodicRescanner`** - every 5 min, walks the vault and reconciles against Index. Catches watchdog event drops on macOS under heavy sync load. Logs discrepancies.
- **`AtomicWriter`** - `write_atomic(path, content, expected_mtime=None)` uses tmp-file plus rename. If `expected_mtime` given, stat must match or raise `StaleWriteError`. Updates Index directly.
- **`FrontmatterParser`** - thin wrapper over `python-frontmatter`. Adds validation: required fields, tag grammar, domain in enum.

### 4.3 Startup sequence

1. Parse CLI args or env vars, resolve vault root.
2. Load `brainkeeper.yaml`, validate against JSON Schema, abort on failure.
3. Walk vault once, build Index (parallel with `ThreadPoolExecutor`, ~4 workers). Log warnings for malformed frontmatter but do not abort.
4. Start `FileWatcher` on vault root.
5. Start `PeriodicRescanner` background thread (5 min cadence).
6. Start FastMCP server on stdio.

Typical timing: under 500 ms on a 500-note vault, under 2 s on 3k notes.

### 4.4 Request flow - worked example

`capture(content="Idea: Flutter MCP", type="idea")`:

1. Layer 2 calls `resolve_path({type: "idea"})`.
2. Layer 1 reads config: `capture_routing.idea = "30 Areas/Ideas/Inbox.md"` with append mode. Returns `{path, mode: "append", template: "Idea.md"}`.
3. Layer 2 loads template, substitutes `{{date}}`, `{{content}}`.
4. Layer 0 calls `write_note_atomic` with `expected_mtime` from Index.
5. Infrastructure: AtomicWriter does tmp plus rename, updates Index directly.
6. Layer 2 returns `{path, action: "appended", frontmatter}`.

### 4.5 Concurrency and safety

Three write hazards this handles:

1. **MCP vs Syncthing from another machine.** `expected_mtime` check on every write. If mtime does not match, abort with `StaleWriteError`, client retries after re-reading.
2. **MCP vs user-in-Obsidian-on-same-machine.** Cannot fully prevent, but `expected_mtime` catches it if Obsidian saved at least once since MCP read. Mitigation: `detect_conflicts()` lists `*.sync-conflict-*.md` files for cleanup.
3. **Concurrent MCP tool calls in one session.** FastMCP handles requests sequentially per client by default. Not a hazard.

Not guarded: adversarial writers, OS-level advisory locks (unreliable on macOS), Syncthing merging mid-write (mitigated by atomic rename, not fully solved).

### 4.6 Error handling

- Validation errors (bad frontmatter, unknown domain tag): structured error to client, never crash.
- Filesystem errors: propagate with clear message.
- Stale writes: `StaleWriteError` special type, client is expected to retry.
- Config errors at startup: abort with actionable message.
- Index inconsistencies: periodic rescanner fixes silently, logs at INFO.

### 4.7 Config mutation

The domain enum in `brainkeeper.yaml` is expected to grow over time as the user's vault evolves. Two paths are supported:

**Path 1 - Manual edit.** User opens `brainkeeper.yaml` and adds to the `domains:` list. `ConfigLoader` watches the file and triggers a reload + `Index.revalidate_all()`. Previously-orphan notes using the newly-added domain become valid. No MCP call required.

**Path 2 - MCP-assisted.** Call Layer 1 tools `list_domains()` and `add_domain(name, description?)`. The `add_domain` tool:

1. Validates the name (lowercase, kebab-case, not already present).
2. Reads the current config file preserving comments and formatting (`ruamel.yaml` round-trip, not `pyyaml`).
3. Appends the new domain entry.
4. Writes atomically via `AtomicWriter`.
5. Triggers `ConfigLoader` reload.

**On removal (manual edit only in v1).** If a domain is removed from the list, `Index.revalidate_all()` flags every note using it. They surface in `find_orphans()` until re-tagged or the domain is re-added.

**Deferred to v2:** `remove_domain(name)` (needs migration tooling), `add_capture_route`, `add_template`, `set_layer_path`. All of these are low-frequency operations that can stay manual-edit-only until usage demands automation.

## 5. Tool surface (v1)

### Layer 0 - Primitives (5)

| Tool | Signature | Returns |
|---|---|---|
| `read_note` | `(path)` | `{path, frontmatter, content, mtime}` |
| `write_note_atomic` | `(path, content, frontmatter=None, expected_mtime=None)` | `{path, mtime, created}` |
| `move_note` | `(src, dst)` | `{from, to, wikilinks_broken}` (v1 does not rewrite links) |
| `list_notes` | `(glob="**/*.md", with_frontmatter=False)` | `[{path, mtime, frontmatter?}]` |
| `delete_note` | `(path, soft=True)` | `{path, destination}` |

### Layer 1 - Convention (6)

| Tool | Signature | Returns |
|---|---|---|
| `read_convention` | `()` | full parsed `brainkeeper.yaml` |
| `resolve_path` | `(intent, params)` | `{path, mode, template?, anchor?}` |
| `get_template` | `(name)` | `{name, content, variables}` |
| `list_layers` | `()` | `[{key, path, ...}]` |
| `list_domains` | `()` | `[{name, description?}, ...]` |
| `add_domain` | `(name, description=None)` | `{name, added, config_path}` |

### Layer 2 - Semantic (16)

**Capture and create**

| Tool | Signature |
|---|---|
| `capture` | `(content, type=None, title=None, tags=None)` |
| `append_to_journal` | `(content, date="today", section=None)` |
| `create_note` | `(type, title, body, tags, frontmatter_extra=None)` |
| `create_daily_note` | `(date="today")` |

**Lifecycle**

| Tool | Signature |
|---|---|
| `archive_entry` | `(path, end_year=current_year)` |
| `promote` | `(path, to)` |
| `update_frontmatter` | `(path, patch)` |

**Query**

| Tool | Signature |
|---|---|
| `find_by_tag` | `(tag, prefix_match=True)` |
| `find_by_status` | `(status, type=None)` |
| `find_by_type` | `(type)` |
| `find_orphans` | `()` |

**Hygiene**

| Tool | Signature |
|---|---|
| `validate_frontmatter` | `(path)` |
| `suggest_tags` | `(content, n=5)` |
| `list_tags` | `(dimension=None)` |
| `detect_conflicts` | `()` |
| `vault_stats` | `()` |

Total: 5 + 6 + 16 = **27 tools** in v1.

### 5.1 Deferred to v2

- Link graph: `backlinks`, `outlinks`, `related_notes`.
- `move_note` with `update_wikilinks=True` (vault-wide rewriting).
- `search_content(query)` - full-text search beyond frontmatter and tags.
- `open_in_obsidian(path)` - URL scheme UX polish.
- Config mutation tools: `remove_domain`, `add_capture_route`, `add_template`, `set_layer_path`. Manual edit supported in v1.
- Domain-specific tools for Projects, Areas, Brain:
    - `project_dashboard`, `kickoff_project`, `project_context`, `extract_tasks`
    - `area_overview`, `list_indexes`
    - `add_knowledge`, `list_knowledge`, knowledge frontmatter sub-schema

Rationale for deferral: ship v1 on generic tools, let real usage surface which domain-specific operations add value vs sound good in theory.

## 6. Testing strategy

### 6.1 Fixture vaults

- `minimal-vault/` - smallest valid brainkeeper vault. Tests basic primitive correctness.
- `anon-vault/` - anonymized snapshot of Daniel's vault (~100 notes). Tests realistic scale and edge cases.
- `broken-vault/` - deliberately malformed. Tests validators and error paths.

### 6.2 Test layers

- **Unit** (`tests/unit/`) - pure functions: frontmatter parser, tag grammar, path resolver, config validator. No filesystem.
- **Integration** (`tests/integration/`) - each MCP tool against a fixture vault in a `tmp_path` copy. Tests atomic writes, index updates, watchdog events.
- **Spec conformance** (`tests/spec/`) - runs every example in `spec/examples/` through the MCP, verifies config parses and tools operate correctly.

### 6.3 Coverage and tooling

- Coverage target: 85% for Layers 0 and 2 (enforced in CI), 70% for infrastructure.
- Tools: `pytest`, `pytest-asyncio`, `freezegun` for date tools, `pyfakefs` for some fs tests (real tmp dirs for atomic write and watchdog tests).

## 7. Build sequence

### Week 1 (~15h) - Spec + Vault reorganization

Deliverable: `brainkeeper` v0.1 (spec) + Daniel's vault conforming to it.

| Task | Hours | Output |
|---|---|---|
| Write `SPEC.md` (16 sections) | 4 | `spec/SPEC.md` |
| Author JSON Schema | 2 | `spec/schema/brainkeeper.schema.json` |
| Write 3 reference configs | 1 | `spec/examples/*.yaml` |
| Vault audit | 2 | Audit report |
| Vault reorganization | 4 | Vault validates |
| README + repo setup | 1 | `brainkeeper` on GitHub |
| Spec article first draft | 1 | `docs/articles/spec.md` |

Exit: Vault validates against schema. Spec tagged v0.1.0 on GitHub. First article drafted.

### Week 2 (~15h) - MCP core

Deliverable: `brainkeeper-mcp` v0.1 alpha. Layers 0 and 1 working end to end.

| Task | Hours |
|---|---|
| Project scaffold (`uv init`, `pyproject.toml`) | 0.5 |
| `ConfigLoader` + JSON Schema validation | 1 |
| `FrontmatterParser` + tag grammar validator | 1 |
| `AtomicWriter` with mtime check | 1 |
| `Index` + walk at startup | 1.5 |
| `FileWatcher` with debounce | 1.5 |
| `PeriodicRescanner` | 0.5 |
| FastMCP server skeleton + stdio | 1 |
| Layer 0 tools (5) | 2 |
| Layer 1 tools (6, incl. list_domains + add_domain) | 2 |
| Unit tests | 2.5 |
| Smoke test against real vault | 1 |

Exit: `uvx brainkeeper-mcp --vault ~/Vault` starts, indexes, responds. Layer 0 and 1 tools pass tests. Watchdog correctly updates index on live edits.

### Week 3 (~10h) - Layer 2 + ship

Deliverable: `brainkeeper-mcp` v1.0 on PyPI.

| Task | Hours |
|---|---|
| Layer 2 tools (16) | 4 |
| Integration tests | 2 |
| Spec conformance tests | 0.5 |
| CLI entry | 0.5 |
| README + quickstart | 1 |
| GitHub Actions CI | 0.5 |
| PyPI publish + tagged release | 0.5 |
| MCP article first draft | 1 |

Exit: `pip install brainkeeper-mcp` works fresh. v1.0.0 tagged. Article drafted. Used daily in Daniel's workflow for at least 3 days by end of week 3.

## 8. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `watchdog` event drops on macOS under heavy Syncthing load | Medium | Medium | 5-min `PeriodicRescanner` safety net. Optional content-hash reconciliation in v1.1 if drops exceed threshold. |
| Vault reorganization reveals more cleanup than expected | Medium | Low | Time-box Week 1 audit to 2h. If larger, push Layer 2 tools into Week 3 or defer 2-3 tools to v1.1. |
| PyPI or GitHub name collision on `brainkeeper` | Low | Low | Check availability before Week 1. Have backup name ready (`structvault`, `vaultspec`). |
| Spec design gets controversy, pulling attention from MCP build | Low | Medium | Park controversial feedback in an issue tracker. Ship v1.0 first, engage after. |
| Phase 1 budget overrun (>40h) squeezes second MCP | Medium | Medium | Hard stop at 40h. Anything remaining pushes to v1.1 with a clean release. |

## 9. Acceptance criteria for v1.0

- `brainkeeper` repo public, spec at v1.0.0 tag.
- `brainkeeper-mcp` installable via `pip install brainkeeper-mcp` and runnable via `uvx brainkeeper-mcp --vault <path>`.
- All 27 tools functional against Daniel's vault and `minimal-vault` fixture.
- Test coverage meets targets.
- Daniel's vault is spec-compliant (validates against JSON Schema).
- Two article drafts exist (polish and publish later).
- CI green on GitHub Actions.
