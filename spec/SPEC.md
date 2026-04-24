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

### Part I: Structure
1. Layers
2. Numbered prefixes
3. Reserved paths
4. Area substructure
5. Bilingual, language-agnostic folders

### Part II: Content model
6. Frontmatter contract
7. Tag taxonomy
8. Naming conventions
9. Linking convention
10. Template contract

### Part III: Lifecycle
11. Classification rules
12. Transition rules
13. Status semantics

### Part IV: Implementation notes
14. Config file format
15. Extension points
16. Obsidian compatibility notes

---
## Part I: Structure

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

- **`<archive>/<YYYY>/`**. If the `archive` layer uses `year_subfolder: true` (default), tooling creates per-year subfolders on demand when archiving.
- **`<templates>/`**. Reserved for template files referenced by layer entries or tooling (see §10).

No other paths are reserved by this spec. Users remain free to create any subdirectory structure inside any layer.

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


## Part II: Content model

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
| `archived` | `YYYY-MM-DD` or `null` | Set to today when the note is archived; `null` otherwise. |

**Extension rule.** Additional fields beyond the ones above are permitted and ignored by the spec. Tooling SHOULD pass unknown fields through unchanged on write (read-modify-write preserves user fields).

**Type semantics (non-normative).**
- `project`. Has a defined end state. Lives in the `projects` layer.
- `area`. Ongoing responsibility. Lives in the `areas` layer.
- `idea`. A capture that may promote to a project. Lives in `areas` or `inbox`.
- `journal`. Dated daily note. Lives in `journal`.
- `meeting`. Dated meeting note. Lives in `journal` (separate file, linked from the day's journal).
- `note`. Freeform capture, no stronger semantics.
- `resource`. External reference (article, video, PDF annotation).
- `knowledge`. Evergreen note in `brain`.

