# brainkeeper Spec v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `brainkeeper` spec v0.1 - a public, tool-agnostic standard for structured Second Brain vaults. Deliverables: `spec/SPEC.md` + `spec/schema/brainkeeper.schema.json` + three reference configs, all cross-validated, tagged `spec-v0.1.0` on GitHub.

**Architecture:** Two coupled artifacts in one directory. `SPEC.md` is the human-readable standard. `brainkeeper.schema.json` is the machine-readable validation of a `brainkeeper.yaml` config at a vault's root. Examples prove the schema works and serve as copy-paste starting points for users. Validation is done via `check-jsonschema` (pip-installable CLI) so there is no language lock-in for the spec itself - the MCP implementation comes in a later plan.

**Tech Stack:**
- Markdown for `SPEC.md`
- JSON Schema Draft 2020-12 for `brainkeeper.schema.json`
- YAML for example configs
- `check-jsonschema` CLI (via `uvx`) for validation
- Git tags for spec versioning

**Source of truth for content:** `docs/design.md` in this repo contains all the design decisions. The tasks below transform those decisions into public-facing spec + schema content. Each prose section below includes the full substance pulled from `docs/design.md` - the executor should expand it into clear, publishable prose, not invent new content.

---

## File structure

Files created by this plan:

```
brainkeeper/
├── CHANGELOG.md                              # release notes
├── README.md                                 # MODIFY: add spec link + status update
├── spec/
│   ├── README.md                             # brief pointer into SPEC.md
│   ├── SPEC.md                               # the canonical spec
│   ├── schema/
│   │   └── brainkeeper.schema.json           # JSON Schema for brainkeeper.yaml
│   └── examples/
│       ├── minimal.yaml                      # smallest valid config
│       ├── daniels-vault.yaml                # full reference config
│       └── zettelkasten.yaml                 # alternative-style config
└── docs/
    └── plans/
        └── 2026-04-24-brainkeeper-spec.md    # this file
```

Responsibilities:
- `spec/SPEC.md` - prose definition of the standard (16 sections, 4 parts).
- `spec/schema/brainkeeper.schema.json` - enforces config shape. All config-format rules in the spec MUST be expressible here.
- `spec/examples/*.yaml` - three validated configs demonstrating range. Must all validate clean under the schema.
- `spec/README.md` - one-screen orientation: what the spec is, where to find it, how to validate.
- `CHANGELOG.md` - tracks spec + future MCP releases (Keep a Changelog format).
- Main `README.md` - updated to reflect spec exists and point at it.

---

## Validation commands (used throughout the plan)

Before starting, verify `uvx` is available:

```bash
uvx --version
```

Primary validation command (used in almost every task):

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json spec/examples/*.yaml
```

Schema self-check (verify the schema itself is well-formed JSON Schema 2020-12):

```bash
uvx check-jsonschema --check-metaschema spec/schema/brainkeeper.schema.json
```

---

## Part 1 - Scaffold

### Task 1: Create directory structure and placeholder files

**Files:**
- Create: `spec/SPEC.md` (empty placeholder, filled in Task 8+)
- Create: `spec/README.md`
- Create: `spec/schema/brainkeeper.schema.json` (empty `{}`, filled in Task 3)
- Create: `spec/examples/.gitkeep`

- [ ] **Step 1: Create directories**

```bash
mkdir -p spec/schema spec/examples
```

- [ ] **Step 2: Create `spec/README.md`**

```markdown
# brainkeeper spec

The canonical spec lives in [`SPEC.md`](./SPEC.md).

## Validate your config

From the repo root:

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json path/to/your/brainkeeper.yaml
```

## Examples

- [`examples/minimal.yaml`](./examples/minimal.yaml) - smallest valid config
- [`examples/daniels-vault.yaml`](./examples/daniels-vault.yaml) - full reference config
- [`examples/zettelkasten.yaml`](./examples/zettelkasten.yaml) - alternative style

## Versioning

Spec versions are tagged `spec-vX.Y.Z` on this repo. v0.1 is the first public release.
```

- [ ] **Step 3: Create placeholders**

Create `spec/SPEC.md` with a single placeholder line `# brainkeeper` (will be overwritten in Task 8).

Create `spec/schema/brainkeeper.schema.json` with contents `{}` (will be overwritten in Task 3).

Create `spec/examples/.gitkeep` (empty file, so the directory is tracked before examples are added).

- [ ] **Step 4: Verify**

```bash
ls spec spec/schema spec/examples
```

Expected: four files listed (`README.md`, `SPEC.md` under `spec/`, `brainkeeper.schema.json` under `spec/schema/`, `.gitkeep` under `spec/examples/`).

- [ ] **Step 5: Commit**

```bash
git add spec/
git commit -m "chore(spec): scaffold spec/ directory tree"
```

---

## Part 2 - Schema and examples (TDD-style)

Build the schema and examples together. Each step either adds an example then expands the schema to accept it, or tightens the schema then proves existing examples still pass. Every task ends with `check-jsonschema` passing.

### Task 2: Write `minimal.yaml` (smallest valid config)

**Files:**
- Create: `spec/examples/minimal.yaml`

- [ ] **Step 1: Write the minimal config**

```yaml
# Smallest valid brainkeeper config.
# All 8 layer keys are required (string shorthand allowed).
# At least one domain is required.
# capture_routing must include a `default`.

layers:
  inbox: "00 Inbox"
  journal: "10 Journal"
  projects: "20 Projects"
  areas: "30 Areas"
  brain: "40 Brain"
  system: "90 System"
  archive: "90 System/Archive"
  templates: "90 System/Templates"

domains:
  - personal

capture_routing:
  default: "00 Inbox/"
```

- [ ] **Step 2: YAML parse check**

```bash
uvx --from pyyaml python -c "import yaml,sys; yaml.safe_load(open('spec/examples/minimal.yaml'))"
```

Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add spec/examples/minimal.yaml
git commit -m "spec(examples): add minimal.yaml"
```

---

### Task 3: Write initial JSON Schema (layers string shorthand + domains + capture_routing)

**Files:**
- Modify: `spec/schema/brainkeeper.schema.json` (overwrite placeholder)

- [ ] **Step 1: Run validation first to confirm it currently fails**

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json spec/examples/minimal.yaml
```

Expected: **FAIL** - the schema is `{}`, which accepts everything, so it actually passes. We want to force a failure first. Instead, run the meta-schema check which *should* pass (schema is valid JSON Schema because `{}` is valid):

```bash
uvx check-jsonschema --check-metaschema spec/schema/brainkeeper.schema.json
```

Expected: PASS.

We'll treat "schema rejects a known-bad config" as the real test. Create a scratch bad config:

```bash
echo 'layers: "not an object"' > /tmp/bad.yaml
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json /tmp/bad.yaml
```

Expected: PASS (because schema is permissive). This is the failing test - after Task 3 it MUST FAIL.

- [ ] **Step 2: Write the initial schema**

Overwrite `spec/schema/brainkeeper.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/dasirra/brainkeeper/spec/schema/brainkeeper.schema.json",
  "title": "brainkeeper vault config",
  "description": "Configuration file format for a brainkeeper-compliant Second Brain vault.",
  "type": "object",
  "required": ["layers", "domains", "capture_routing"],
  "additionalProperties": false,
  "properties": {
    "layers": {
      "type": "object",
      "description": "Mapping of layer keys to filesystem paths. All 8 keys are required. Each value may be a string shorthand (path only) or an object with additional options.",
      "required": [
        "inbox", "journal", "projects", "areas",
        "brain", "system", "archive", "templates"
      ],
      "additionalProperties": false,
      "properties": {
        "inbox":     { "$ref": "#/$defs/layerEntry" },
        "journal":   { "$ref": "#/$defs/layerEntry" },
        "projects":  { "$ref": "#/$defs/layerEntry" },
        "areas":     { "$ref": "#/$defs/layerEntry" },
        "brain":     { "$ref": "#/$defs/layerEntry" },
        "system":    { "$ref": "#/$defs/layerEntry" },
        "archive":   { "$ref": "#/$defs/layerEntry" },
        "templates": { "$ref": "#/$defs/layerEntry" }
      }
    },
    "domains": {
      "type": "array",
      "description": "List of domain values used as the required `domain/*` tag dimension on every managed note.",
      "minItems": 1,
      "uniqueItems": true,
      "items": { "$ref": "#/$defs/domainName" }
    },
    "capture_routing": {
      "type": "object",
      "description": "Maps capture intent keys (idea, todo, meeting, ...) to a destination path. `default` is required.",
      "required": ["default"],
      "additionalProperties": { "$ref": "#/$defs/routeTarget" },
      "properties": {
        "default": { "$ref": "#/$defs/routeTarget" }
      }
    }
  },
  "$defs": {
    "relPath": {
      "type": "string",
      "minLength": 1,
      "description": "Vault-relative path. Must not start with '/' and must not contain '..' segments.",
      "pattern": "^(?!/)(?!.*(^|/)\\.\\.(/|$)).+"
    },
    "layerEntry": {
      "description": "Either a string (path shorthand) or an object with a required `path` and layer-specific options.",
      "oneOf": [
        { "$ref": "#/$defs/relPath" },
        {
          "type": "object",
          "required": ["path"],
          "additionalProperties": false,
          "properties": {
            "path":          { "$ref": "#/$defs/relPath" },
            "format":        { "type": "string" },
            "template":      { "$ref": "#/$defs/relPath" },
            "status_field":  { "type": "string" },
            "active_values": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
            "year_subfolder":{ "type": "boolean" }
          }
        }
      ]
    },
    "domainName": {
      "type": "string",
      "description": "Lowercase, kebab-case, singular. Used as the value of a `domain/*` tag.",
      "pattern": "^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
      "minLength": 2,
      "maxLength": 40
    },
    "routeTarget": {
      "type": "string",
      "description": "Destination for a captured entry. Trailing '/' indicates a folder (new file per capture). A bare path means append to that file. May include '#Anchor' to target a heading. Supports `{today}` substitution.",
      "minLength": 1,
      "pattern": "^(?!/)(?!.*(^|/)\\.\\.(/|$)).+"
    }
  }
}
```

- [ ] **Step 3: Meta-schema check**

```bash
uvx check-jsonschema --check-metaschema spec/schema/brainkeeper.schema.json
```

Expected: PASS (`ok -- all files valid`).

- [ ] **Step 4: Validate minimal.yaml passes**

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json spec/examples/minimal.yaml
```

Expected: PASS.

- [ ] **Step 5: Verify the scratch bad config now fails**

```bash
echo 'layers: "not an object"' > /tmp/bad.yaml
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json /tmp/bad.yaml
echo "exit=$?"
```

Expected: FAIL (non-zero exit), error message about `layers` not matching expected type.

Clean up: `rm /tmp/bad.yaml`.

- [ ] **Step 6: Commit**

```bash
git add spec/schema/brainkeeper.schema.json
git commit -m "spec(schema): initial JSON Schema (layers, domains, capture_routing)"
```

---

### Task 4: Write `daniels-vault.yaml` (full reference config)

**Files:**
- Create: `spec/examples/daniels-vault.yaml`

Exercises: object-form layer entries (`journal`, `projects`, `archive`), multiple domains, extended `capture_routing`.

- [ ] **Step 1: Write the full config**

```yaml
# Full reference config. Daniel Sierra's vault.
# Demonstrates the object-form for layers that accept options.

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
  areas: "30 Areas"
  brain: "40 Brain"
  system: "90 System"
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

- [ ] **Step 2: Validate**

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json spec/examples/*.yaml
```

Expected: PASS for both `minimal.yaml` and `daniels-vault.yaml`.

- [ ] **Step 3: Commit**

```bash
git add spec/examples/daniels-vault.yaml
git commit -m "spec(examples): add daniels-vault.yaml reference config"
```

---

### Task 5: Write `zettelkasten.yaml` (alternative style)

**Files:**
- Create: `spec/examples/zettelkasten.yaml`

Demonstrates that folder names are arbitrary strings (bilingual / alternate-convention friendly).

- [ ] **Step 1: Write the config**

```yaml
# Zettelkasten-style vault. Custom folder names.
# Proves the spec does not hardcode English or numeric prefixes.

layers:
  inbox:     "Fleeting"
  journal:
    path:    "Daily"
    format:  "YYYY-MM-DD.md"
  projects:  "Projects"
  areas:     "Permanent"
  brain:     "Literature"
  system:    "Meta"
  archive:
    path:    "Meta/Archive"
    year_subfolder: true
  templates: "Meta/Templates"

domains:
  - research
  - writing
  - reading
  - personal

capture_routing:
  idea:    "Fleeting/Ideas.md"
  default: "Fleeting/"
```

- [ ] **Step 2: Validate**

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json spec/examples/*.yaml
```

Expected: all three examples PASS.

- [ ] **Step 3: Commit**

```bash
git add spec/examples/zettelkasten.yaml
git commit -m "spec(examples): add zettelkasten.yaml alternative config"
```

---

### Task 6: Add negative-test config and verify rejection

**Files:**
- Create: `spec/examples/.invalid/missing-default.yaml` (negative test; hidden dir so it's ignored by primary validation)
- Create: `spec/examples/.invalid/bad-domain.yaml`
- Create: `spec/examples/.invalid/absolute-path.yaml`
- Create: `spec/examples/.invalid/README.md`

These exist to prove the schema rejects known-bad inputs. They live under `.invalid/` so they are skipped by the primary `examples/*.yaml` glob.

- [ ] **Step 1: Create the invalid-examples directory and README**

`spec/examples/.invalid/README.md`:

```markdown
# Invalid configs (negative test fixtures)

Every file in this directory MUST fail schema validation. See `../SPEC.md` for rules.

Run:

```bash
for f in spec/examples/.invalid/*.yaml; do
  uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json "$f" && {
    echo "ERROR: $f should have failed but passed" >&2
    exit 1
  } || echo "ok (rejected): $f"
done
```
```

- [ ] **Step 2: Write `missing-default.yaml`**

```yaml
# INVALID: capture_routing is missing `default`.
layers:
  inbox: "00 Inbox"
  journal: "10 Journal"
  projects: "20 Projects"
  areas: "30 Areas"
  brain: "40 Brain"
  system: "90 System"
  archive: "90 System/Archive"
  templates: "90 System/Templates"

domains: [personal]

capture_routing:
  idea: "30 Areas/Ideas.md"
```

- [ ] **Step 3: Write `bad-domain.yaml`**

```yaml
# INVALID: domain "Personal_Life" breaks the kebab-case lowercase rule.
layers:
  inbox: "00 Inbox"
  journal: "10 Journal"
  projects: "20 Projects"
  areas: "30 Areas"
  brain: "40 Brain"
  system: "90 System"
  archive: "90 System/Archive"
  templates: "90 System/Templates"

domains:
  - Personal_Life

capture_routing:
  default: "00 Inbox/"
```

- [ ] **Step 4: Write `absolute-path.yaml`**

```yaml
# INVALID: absolute path under layers.inbox.
layers:
  inbox: "/absolute/path/inbox"
  journal: "10 Journal"
  projects: "20 Projects"
  areas: "30 Areas"
  brain: "40 Brain"
  system: "90 System"
  archive: "90 System/Archive"
  templates: "90 System/Templates"

domains: [personal]

capture_routing:
  default: "00 Inbox/"
```

- [ ] **Step 5: Run negative tests**

```bash
set +e
for f in spec/examples/.invalid/*.yaml; do
  out=$(uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json "$f" 2>&1)
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "ERROR: $f should have failed but passed"
    exit 1
  fi
  echo "ok (rejected): $f"
done
set -e
```

Expected: all three print `ok (rejected)`.

- [ ] **Step 6: Confirm primary glob still excludes invalid dir**

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json spec/examples/*.yaml
```

Expected: PASS (only sees the 3 valid top-level examples; `.invalid/` is hidden).

- [ ] **Step 7: Commit**

```bash
git add spec/examples/.invalid/
git commit -m "spec(examples): add negative-test fixtures under .invalid/"
```

---

## Part 3 - SPEC.md prose

The spec is 16 numbered sections in 4 parts. Each prose task below contains the full substance (pulled from `docs/design.md`) the executor must expand into clean, publishable prose suitable for a public standard. Write in second person where natural ("Your vault..."). Keep paragraphs short. Include the exact YAML/example blocks given.

Style rules:
- No em dashes (user preference - use periods, commas, colons, or restructured phrases).
- Spec is tool-agnostic: never depend on Obsidian in normative text. Obsidian is mentioned only in §16.
- Every example path matches the example configs in `spec/examples/`.

### Task 7: SPEC.md - title, front matter, table of contents

**Files:**
- Modify: `spec/SPEC.md` (overwrite placeholder)

- [ ] **Step 1: Write the header**

Overwrite `spec/SPEC.md` with:

```markdown
# brainkeeper specification

**Version:** 0.1.0
**Status:** Draft (first public release)
**Date:** 2026-04-24
**License:** MIT

## Abstract

brainkeeper is a standard for structured Markdown-based Second Brain vaults. It formalizes a PARA-inspired layer model, extended with a dated journal and a system area, and defines the content conventions (frontmatter, tags, naming, links, templates) and lifecycle rules (classification, transitions, status) that make a vault machine-readable without losing the flexibility that makes personal knowledge systems useful.

The spec is tool-agnostic: any editor that writes Markdown with YAML frontmatter to a local directory can produce a brainkeeper-compliant vault. A companion `brainkeeper.yaml` config file at the vault root specifies per-vault choices (folder names, domain list, capture routes) and is validated against `brainkeeper.schema.json`.

## How to read this spec

- **Normative keywords.** The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY follow RFC 2119.
- **Managed notes.** A note is "managed" if it lives inside one of the eight configured layers and declares the required frontmatter. Unmanaged notes (e.g. scratch files in `00 Inbox` without frontmatter) are tolerated but not guaranteed valid targets for tooling.
- **Config file.** All references to "the config" mean the `brainkeeper.yaml` at the vault root. Semantic keys (`layers.projects`, `layers.archive`) MUST resolve through the config rather than through hardcoded strings.

## Table of contents

### Part I - Structure
1. Layers
2. Numbered prefixes
3. Reserved paths
4. Area substructure
5. Bilingual, language-agnostic folders

### Part II - Content model
6. Frontmatter contract
7. Tag taxonomy
8. Naming conventions
9. Linking convention
10. Template contract

### Part III - Lifecycle
11. Classification rules
12. Transition rules
13. Status semantics

### Part IV - Implementation notes
14. Config file format
15. Extension points
16. Obsidian compatibility notes

---
```

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: SPEC.md header and table of contents"
```

---

### Task 8: SPEC.md - Part I, Sections 1-3 (Layers, Prefixes, Reserved paths)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append Part I intro and sections 1-3**

Append to `spec/SPEC.md`:

```markdown
## Part I - Structure

### 1. Layers

A brainkeeper vault organizes content into exactly eight top-level layers. Each layer has a single purpose:

| Key         | Default path          | Purpose |
|-------------|-----------------------|---------|
| `inbox`     | `00 Inbox`            | Unprocessed capture. Notes live here until triaged. |
| `journal`   | `10 Journal`          | Dated notes: dailies, meeting notes, session logs. |
| `projects`  | `20 Projects`         | Outcomes with a defined end state. |
| `areas`     | `30 Areas`            | Ongoing responsibilities without a finish line. |
| `brain`     | `40 Brain`            | Evergreen knowledge: concepts, references, notes-on-notes. |
| `system`    | `90 System`           | Meta: templates, archive, vault tooling. |
| `archive`   | `90 System/Archive`   | Completed or retired content. Usually a child of `system`. |
| `templates` | `90 System/Templates` | Template files for new notes. Usually a child of `system`. |

The keys are canonical. Paths are user-configurable in `brainkeeper.yaml` (see §5, §14). All eight keys MUST be present in the config; a vault that lacks, for example, a journal layer is out of scope for v1.

### 2. Numbered prefixes

The default paths use a Johnny Decimal-inspired numeric prefix convention: `00 Inbox`, `10 Journal`, `20 Projects`, `30 Areas`, `40 Brain`, `90 System`. Gaps (50, 60, 70, 80) are deliberate and reserved for user expansion; a tool-specific vault might add a `50 Media` or `70 Archive-Cold` layer outside of the standard keys.

Prefixes are a convention, not a requirement. A vault MAY use non-numeric names (see §5 and the `zettelkasten.yaml` example) as long as the eight layer keys map to valid relative paths.

### 3. Reserved paths

A conforming vault MUST contain the eight layer directories at the configured paths. Tooling MAY auto-create any missing layer directory on startup. Two paths are additionally reserved:

- **`<archive>/<YYYY>/`** - if the `archive` layer uses `year_subfolder: true` (default), tooling creates per-year subfolders on demand when archiving.
- **`<templates>/`** - reserved for template files referenced by layer entries or tooling (see §10).

No other paths are reserved by this spec. Users remain free to create any subdirectory structure inside any layer.

```

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part I sections 1-3 (layers, prefixes, reserved paths)"
```

---

### Task 9: SPEC.md - Part I, Sections 4-5 (Area substructure, Bilingual)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append sections 4-5**

Append to `spec/SPEC.md`:

```markdown
### 4. Area substructure

Within the `areas` layer, users MAY create arbitrary subdirectories to organize ongoing responsibilities. Common patterns observed in practice:

```
30 Areas/
├── Finanzas/
├── Pipeline/
├── Portfolio/
└── Research/
```

This is a soft convention. Sub-structure inside `areas` is not validated by the spec. Tools SHOULD treat any direct child of `areas` as a candidate area folder and MAY look for an `<Area> Index.md` file inside it (see §8).

### 5. Bilingual, language-agnostic folders

Folder names in a brainkeeper vault are strings of the user's choosing. The spec reserves no English identifiers for on-disk names. A Spanish-speaking user MAY configure:

```yaml
layers:
  inbox:    "00 Bandeja"
  journal:  "10 Diario"
  projects: "20 Proyectos"
  # ...
```

and the vault remains compliant. Tooling MUST reference layers by their canonical key (`layers.projects`) and never by a literal path string.

This rule applies to all spec-reserved concepts: domains (§7), template file names (§10), status values (§13), and capture routes (§14) are user-configurable strings mapped through the config file.

```

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part I sections 4-5 (area substructure, bilingual)"
```

---

### Task 10: SPEC.md - Part II, Section 6 (Frontmatter contract)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append Part II intro and section 6**

Append to `spec/SPEC.md`:

````markdown
## Part II - Content model

### 6. Frontmatter contract

Every **managed note** MUST begin with a YAML frontmatter block delimited by `---` lines. Minimum required fields:

```yaml
---
type: project
status: active
created: 2026-04-24
tags:
  - topic/mcp
  - project/brainkeeper
---
```

**Required fields:**

| Field     | Type           | Allowed values |
|-----------|----------------|----------------|
| `type`    | string         | `project`, `area`, `idea`, `journal`, `meeting`, `note`, `resource`, `knowledge` |
| `status`  | string         | `active`, `paused`, `completed`, `archived` |
| `created` | `YYYY-MM-DD`   | ISO date, never empty |
| `tags`    | list of string | At least one tag. See §7. |

**Optional fields:**

| Field      | Type         | Notes |
|------------|--------------|-------|
| `deadline` | `YYYY-MM-DD` | Target completion date (projects). |
| `archived` | `YYYY-MM-DD` \| `null` | Set to today when the note is archived; `null` otherwise. |

**Extension rule.** Additional fields beyond the ones above are permitted and ignored by the spec. Tooling SHOULD pass unknown fields through unchanged on write (read-modify-write preserves user fields).

**Type semantics (non-normative).**
- `project` - has a defined end state. Lives in the `projects` layer.
- `area` - ongoing responsibility. Lives in the `areas` layer.
- `idea` - a capture that may promote to a project. Lives in `areas` or `inbox`.
- `journal` - dated daily note. Lives in `journal`.
- `meeting` - dated meeting note. Lives in `journal` (separate file, linked from the day's journal).
- `note` - freeform capture, no stronger semantics.
- `resource` - external reference (article, video, PDF annotation).
- `knowledge` - evergreen note in `brain`.

````

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part II section 6 (frontmatter contract)"
```

---

### Task 11: SPEC.md - Part II, Section 7 (Tag taxonomy)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append section 7**

Append to `spec/SPEC.md`:

````markdown
### 7. Tag taxonomy

brainkeeper uses a hierarchical tag grammar. Dimensions (prefixes) are prescribed; values are open.

**Prescribed dimensions:**

| Prefix     | Cardinality | Required? | Value source |
|------------|-------------|-----------|--------------|
| `domain/`  | exactly 1   | yes       | Enum in `brainkeeper.yaml` (`domains:`). Editable. |
| `topic/`   | 0..n        | recommended | Free (user-defined vocabulary). |
| `project/` | 0..n        | only on notes related to a project | Free; SHOULD match a project folder slug. |
| `person/`  | 0..n        | optional  | Free (meeting and 1-on-1 notes). |

**Syntax rules:**

- Lowercase only.
- Kebab-case (words joined by `-`).
- Singular form (`person/daniel`, not `people/daniels`).
- YAML list form. The `#` prefix is NOT included in the YAML value:

  ```yaml
  tags:
    - topic/mcp
    - project/brainkeeper
  ```

- At least one tag is required on every managed note.

**Guiding principle.** Tag what the folder path does not already encode. A file under `20 Projects/Brainkeeper/` already implies `project/brainkeeper`; adding it is redundant but not wrong. A note in `40 Brain/` about the MCP protocol benefits from `topic/mcp` because `40 Brain/` alone does not convey it.

**Domain tag grammar.** Values for `domain/*` MUST appear in the `domains:` list of `brainkeeper.yaml`. Domain names are lowercase kebab-case (regex: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, length 2–40). Adding a new domain is a one-line config edit (see §15).

````

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part II section 7 (tag taxonomy)"
```

---

### Task 12: SPEC.md - Part II, Section 8 (Naming conventions)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append section 8**

Append to `spec/SPEC.md`:

```markdown
### 8. Naming conventions

**Dates.** Use ISO 8601 `YYYY-MM-DD` for all dates: filenames, frontmatter values, anchor references.

**Daily notes.** `journal/YYYY-MM-DD.md` (e.g. `10 Journal/2026-04-24.md`). The file name pattern is configurable via `layers.journal.format` (default `YYYY-MM-DD.md`).

**Meeting notes.** `journal/YYYY-MM-DD - <Slug>.md` (e.g. `10 Journal/2026-04-24 - Fitizens Standup.md`). Meetings are separate files from the daily note and SHOULD be linked from the day's journal.

**Index files.** `<Name> Index.md`. The `Index.md` suffix is reserved for entry-point notes inside project and area folders (e.g. `20 Projects/Brainkeeper/Brainkeeper Index.md`). Tools MAY treat these specially.

**Project and area folders.** Title Case, no numeric prefixes inside the layer:
- `20 Projects/Brainkeeper/` (good)
- `20 Projects/03-brainkeeper/` (not recommended)

**Note filenames (general).** Title Case with spaces (`Great Article on Caching.md`). Avoid special characters that break wikilinks: `[`, `]`, `|`, `#`, `^`, `:`, `\`, `/`.

```

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part II section 8 (naming conventions)"
```

---

### Task 13: SPEC.md - Part II, Sections 9-10 (Linking, Templates)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append sections 9-10**

Append to `spec/SPEC.md`:

````markdown
### 9. Linking convention

Internal references between notes MUST use wikilink syntax:

- `[[Note Name]]` - link by title (filename without `.md`).
- `[[Path/To/Note|Alias]]` - link by relative path, with a display alias.

Standard Markdown links (`[text](path.md)`) MUST NOT be used for internal references. They are permitted for external URLs only.

**Disambiguation.** When two notes share a filename, use the relative path form to disambiguate. Tools SHOULD prefer the shortest unique path that resolves unambiguously.

**Embedded blocks.** `[[Note#Heading]]` and `[[Note^block-id]]` are permitted for heading and block references. Block IDs follow Obsidian conventions but are optional.

### 10. Template contract

Templates live in the `templates` layer (default `90 System/Templates/`). Required templates:

| File              | Purpose |
|-------------------|---------|
| `Daily.md`        | Template for daily journal notes. |
| `Project.md`      | Template for new project notes. |
| `Area Index.md`   | Template for area entry-point notes. |
| `Idea.md`         | Template for captured ideas. |
| `Meeting.md`      | Template for meeting notes. |

**Substitution.** Templates support simple `{{variable}}` substitution. Defined variables:

| Variable    | Meaning |
|-------------|---------|
| `{{date}}`  | Date the note refers to (`YYYY-MM-DD`). |
| `{{today}}` | Today's date (`YYYY-MM-DD`). |
| `{{title}}` | Title of the note being created. |

Unknown variables MUST be left untouched by substituting tools (no silent deletion). Additional variables MAY be defined by tooling as long as they do not collide with the reserved names above.

````

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part II sections 9-10 (linking, templates)"
```

---

### Task 14: SPEC.md - Part III, Sections 11-13 (Lifecycle)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append Part III intro and sections 11-13**

Append to `spec/SPEC.md`:

```markdown
## Part III - Lifecycle

### 11. Classification rules

A new note with no obvious destination SHOULD be written to the `inbox` layer. Triage moves the note to its final layer. Tools offering a `capture` operation SHOULD:

1. Inspect the `type` field (or infer from content).
2. Look up `capture_routing.<type>` in the config.
3. Fall back to `capture_routing.default` if no route matches.

### 12. Transition rules

Only four layer-to-layer transitions are part of the standard:

| From                    | To                        | Trigger |
|-------------------------|---------------------------|---------|
| `inbox`                 | any layer                 | Triage |
| `areas/Ideas`           | `projects`                | Idea matures into a bounded outcome |
| `projects`              | `archive/YYYY`            | Project completed or abandoned |
| `areas/<Area>`          | `archive/YYYY`            | Area retired |

On any transition, tools MUST:
- Update `status` in frontmatter (see §13).
- Set `archived: YYYY-MM-DD` when moving into the archive.
- Preserve all other frontmatter fields unchanged.

Other moves (e.g. `brain` → `archive`) are permitted but not blessed by the spec. Tools MAY refuse unknown transitions or require explicit user confirmation.

### 13. Status semantics

The `status` frontmatter field takes one of four values:

| Value       | Meaning |
|-------------|---------|
| `active`    | Work in progress. Default for new projects and areas. |
| `paused`    | Deferred without abandoning. Hidden from default query views. |
| `completed` | Outcome reached. Should be archived soon. |
| `archived`  | Moved to the archive layer. `archived` frontmatter field is set to the archive date. |

The `status_field` under `layers.projects` MAY be renamed (default is `status`) and `active_values` MAY include additional synonyms (e.g. `"🟢"`) for users who prefer emoji status markers. Tooling MUST consult the config before filtering by status.

```

- [ ] **Step 2: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part III sections 11-13 (lifecycle)"
```

---

### Task 15: SPEC.md - Part IV, Sections 14-16 (Config, Extensions, Obsidian)

**Files:**
- Modify: `spec/SPEC.md` (append)

- [ ] **Step 1: Append Part IV**

Append to `spec/SPEC.md`:

````markdown
## Part IV - Implementation notes

### 14. Config file format

A brainkeeper-compliant vault MUST contain a `brainkeeper.yaml` at its root. The file is validated against `brainkeeper.schema.json` (JSON Schema Draft 2020-12).

**Full example** (reference vault):

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
  areas: "30 Areas"
  brain: "40 Brain"
  system: "90 System"
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

**Shorthand vs object form for layers.** Each layer entry accepts either a string (shorthand: path only) or an object (when the layer needs additional options: `format`, `template`, `status_field`, `active_values`, `year_subfolder`). The schema defines which options apply to which layers.

**Path rules.** Paths under `layers.*` are vault-relative. Leading `/` is invalid. `..` segments are invalid.

**Capture routes.** A route value ending in `/` denotes a folder (new file per capture). A bare path denotes append-to-file. A `#Anchor` suffix targets a heading inside that file. The token `{today}` is substituted with the current date (`YYYY-MM-DD`).

**Minimum viable config.** See [`examples/minimal.yaml`](./examples/minimal.yaml).

### 15. Extension points

The following additions do NOT require a change to the spec or the schema. They are expressible in config alone:

- Adding a new domain: append to `domains:`.
- Adding a new capture route: add a key under `capture_routing:`.
- Adding a new template: drop the file in the `templates` layer and reference it from a layer entry.
- Renaming any folder: change the corresponding path under `layers:`.

Tooling SHOULD support live config reload: changes to `brainkeeper.yaml` should take effect without a restart. Notes whose domain tag was just added become valid; notes whose domain tag was just removed become orphans (see §7).

### 16. Obsidian compatibility notes

The spec is tool-agnostic. Nothing in Parts I–III depends on Obsidian. This section documents compatibility choices that make a brainkeeper vault cleanly openable in Obsidian:

- **Wikilink syntax.** `[[Note Name]]` is Obsidian's native link style (§9).
- **YAML frontmatter.** The Properties feature in Obsidian reads the same `---` front block (§6).
- **Folder names.** Arbitrary strings; Obsidian imposes no folder naming rules beyond the OS filesystem.
- **Templates.** The `{{date}}` / `{{title}}` variables map onto Obsidian's Templates core plugin. Users who prefer the Templater community plugin MAY use its richer syntax inside template files as long as the reserved variables keep their brainkeeper meaning.

brainkeeper vaults work equally well in Logseq, Silverbullet, and plain-text editors, provided the editor preserves YAML frontmatter and does not rewrite wikilinks into Markdown links.

---

## Appendix A - Schema

The canonical JSON Schema is at [`schema/brainkeeper.schema.json`](./schema/brainkeeper.schema.json). Validate a config with:

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json path/to/brainkeeper.yaml
```

## Appendix B - Versioning

Spec versions follow SemVer with the `spec-` prefix: `spec-v0.1.0`, `spec-v0.2.0`, `spec-v1.0.0`. Breaking changes bump the major component.
````

- [ ] **Step 2: Validate the spec still internally references only real files**

```bash
grep -E '\[.*\]\(\.\/' spec/SPEC.md
```

Expected: every matched relative link corresponds to a real file (`examples/minimal.yaml`, `schema/brainkeeper.schema.json`). If a link does not resolve, fix it before committing.

- [ ] **Step 3: Commit**

```bash
git add spec/SPEC.md
git commit -m "spec: Part IV sections 14-16 (config, extensions, obsidian)"
```

---

## Part 4 - Release

### Task 16: Write `CHANGELOG.md`

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write the changelog**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two artifacts are versioned independently:
- **`spec-vX.Y.Z`** - the brainkeeper specification (`spec/`).
- **`mcp-vX.Y.Z`** - the `brainkeeper-mcp` Python package (forthcoming).

## [spec-v0.1.0] - 2026-04-24

### Added
- Initial public draft of the `brainkeeper` specification (`spec/SPEC.md`).
- JSON Schema for `brainkeeper.yaml` (`spec/schema/brainkeeper.schema.json`).
- Three reference configs: `minimal.yaml`, `daniels-vault.yaml`, `zettelkasten.yaml`.
- Negative-test fixtures under `spec/examples/.invalid/`.

[spec-v0.1.0]: https://github.com/dasirra/brainkeeper/releases/tag/spec-v0.1.0
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG for spec v0.1.0"
```

---

### Task 17: Update main `README.md`

**Files:**
- Modify: `README.md` (section: "Status", section: "Repository layout")

- [ ] **Step 1: Read current README**

```bash
cat README.md
```

- [ ] **Step 2: Update the Status section**

Replace the current "Status" section with:

```markdown
## Status

**Spec v0.1.0** (2026-04-24). Published, first public draft. See [`CHANGELOG.md`](./CHANGELOG.md).

**`brainkeeper-mcp`** - not yet released. Implementation starts after the spec is stable.
```

- [ ] **Step 3: Update the "Repository layout" section**

Replace the layout block with:

````markdown
## Repository layout

```
brainkeeper/
├── spec/                  # the brainkeeper standard
│   ├── SPEC.md            # canonical spec (v0.1.0)
│   ├── schema/            # JSON Schema for brainkeeper.yaml
│   └── examples/          # reference configs (validated against the schema)
├── mcp/                   # brainkeeper-mcp Python package (forthcoming)
└── docs/                  # design docs, plans, articles
```
````

- [ ] **Step 4: Add a new "Validate your config" section just before "Design"**

```markdown
## Validate your config

Drop a `brainkeeper.yaml` at your vault root. Validate it:

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json path/to/brainkeeper.yaml
```

Start from one of the [reference configs](./spec/examples/).
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: update README for spec v0.1.0 release"
```

---

### Task 18: Final cross-check

- [ ] **Step 1: All examples validate**

```bash
uvx check-jsonschema --check-metaschema spec/schema/brainkeeper.schema.json
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json spec/examples/*.yaml
```

Expected: both PASS.

- [ ] **Step 2: All negative fixtures rejected**

```bash
set +e
for f in spec/examples/.invalid/*.yaml; do
  uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json "$f" && {
    echo "FAIL: $f should have been rejected"; exit 1
  }
done
echo "ok: all invalid fixtures rejected"
set -e
```

Expected: prints `ok: all invalid fixtures rejected`.

- [ ] **Step 3: Spec cross-references are live**

```bash
# Every relative link in SPEC.md must resolve to an existing file on disk.
grep -oE '\]\(\./[^)]+\)' spec/SPEC.md | sed -E 's/^\]\(\.\/(.+)\)$/\1/' | while read -r p; do
  [ -e "spec/$p" ] || { echo "MISSING: spec/$p"; exit 1; }
done
echo "ok: all spec links resolve"
```

Expected: prints `ok: all spec links resolve` and no MISSING lines.

- [ ] **Step 4: Confirm no em dashes leaked in**

The repo style rule (user preference) forbids em dashes.

```bash
grep -Rn $'-' spec/ CHANGELOG.md README.md || echo "ok: no em dashes"
```

Expected: prints `ok: no em dashes`.

- [ ] **Step 5: Confirm diff vs main**

```bash
git log --oneline main..HEAD
```

Expected: one commit per task (17+ commits). No stray work-in-progress commits.

---

### Task 19: Tag `spec-v0.1.0`

**Precondition:** All prior tasks complete, `git status` clean, all validation commands pass.

- [ ] **Step 1: Create an annotated tag on `develop`**

```bash
git tag -a spec-v0.1.0 -m "brainkeeper spec v0.1.0 (first public draft)"
```

- [ ] **Step 2: Ask the user before pushing**

Pushing is user-authorized only. Show the user:
- `git log --oneline -1` (tagged commit)
- `git tag --list spec-v0.1.0` (tag exists locally)

Then wait for user confirmation to run:

```bash
git push origin develop
git push origin spec-v0.1.0
```

If the user wants merge-to-main first, follow their instruction instead. Do not push without explicit approval.

---

## Self-review checklist (executor runs this after writing all tasks, before tagging)

- [ ] **Spec coverage.** Every section of `docs/design.md` §3 (Spec contents) has a corresponding task in Part 3 of this plan.
- [ ] **Schema coverage.** Every constraint promised by `SPEC.md` §14 (path rules, domain grammar, required keys) is enforced in `brainkeeper.schema.json`.
- [ ] **Example coverage.** All three examples validate; all three negative fixtures fail validation.
- [ ] **No em dashes** in any spec/changelog/readme file.
- [ ] **Style consistency.** Tables use the same column widths. Heading levels match the TOC.
- [ ] **Dead links.** Every relative link in `SPEC.md` resolves.

---

## Open questions (ask user during execution if unclear)

1. **MIT license** for the spec? README says MIT for the repo; the spec header claims MIT. Confirm before publishing.
2. **PyPI name availability.** Not blocking for this plan (no PyPI upload yet), but flag if `brainkeeper-mcp` is taken on PyPI before the MCP plan starts.
3. **Push target.** Is `origin` the canonical remote, or is there a separate publish step?
