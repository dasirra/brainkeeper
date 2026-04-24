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
├── Finance/
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

**Domain tag grammar.** Values for `domain/*` MUST appear in the `domains:` list of `brainkeeper.yaml`. Domain names are lowercase kebab-case (regex: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, length 2 to 40). Adding a new domain is a one-line config edit (see §15).


### 8. Naming conventions

**Dates.** Use ISO 8601 `YYYY-MM-DD` for all dates: filenames, frontmatter values, anchor references.

**Daily notes.** `journal/YYYY-MM-DD.md` (e.g. `10 Journal/2026-04-24.md`). The file name pattern is configurable via `layers.journal.format` (default `YYYY-MM-DD.md`).

**Meeting notes.** `journal/YYYY-MM-DD - <Slug>.md` (e.g. `10 Journal/2026-04-24 - Fitizens Standup.md`). Meetings are separate files from the daily note and SHOULD be linked from the day's journal.

**Index files.** `<Name> Index.md`. The `Index.md` suffix is reserved for entry-point notes inside project and area folders (e.g. `20 Projects/Brainkeeper/Brainkeeper Index.md`). Tools MAY treat these specially.

**Project and area folders.** Title Case, no numeric prefixes inside the layer:
- `20 Projects/Brainkeeper/` (good)
- `20 Projects/03-brainkeeper/` (not recommended)

**Note filenames (general).** Title Case with spaces (`Great Article on Caching.md`). Avoid special characters that break wikilinks: `[`, `]`, `|`, `#`, `^`, `:`, `\`, `/`.


### 9. Linking convention

Internal references between notes MUST use wikilink syntax:

- `[[Note Name]]`. Link by title (filename without `.md`).
- `[[Path/To/Note|Alias]]`. Link by relative path, with a display alias.

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

## Part III: Lifecycle

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

Other moves (e.g. `brain` to `archive`) are permitted but not blessed by the spec. Tools MAY refuse unknown transitions or require explicit user confirmation.

### 13. Status semantics

The `status` frontmatter field takes one of four values:

| Value       | Meaning |
|-------------|---------|
| `active`    | Work in progress. Default for new projects and areas. |
| `paused`    | Deferred without abandoning. Hidden from default query views. |
| `completed` | Outcome reached. Should be archived soon. |
| `archived`  | Moved to the archive layer. `archived` frontmatter field is set to the archive date. |

The `status_field` under `layers.projects` MAY be renamed (default is `status`) and `active_values` MAY include additional synonyms (e.g. `"🟢"`) for users who prefer emoji status markers. Tooling MUST consult the config before filtering by status.

## Part IV: Implementation notes

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

The spec is tool-agnostic. Nothing in Parts I to III depends on Obsidian. This section documents compatibility choices that make a brainkeeper vault cleanly openable in Obsidian:

- **Wikilink syntax.** `[[Note Name]]` is Obsidian's native link style (§9).
- **YAML frontmatter.** The Properties feature in Obsidian reads the same `---` front block (§6).
- **Folder names.** Arbitrary strings; Obsidian imposes no folder naming rules beyond the OS filesystem.
- **Templates.** The `{{date}}` / `{{title}}` variables map onto Obsidian's Templates core plugin. Users who prefer the Templater community plugin MAY use its richer syntax inside template files as long as the reserved variables keep their brainkeeper meaning.

brainkeeper vaults work equally well in Logseq, Silverbullet, and plain-text editors, provided the editor preserves YAML frontmatter and does not rewrite wikilinks into Markdown links.

---

## Appendix A: Schema

The canonical JSON Schema is at [`schema/brainkeeper.schema.json`](./schema/brainkeeper.schema.json). Validate a config with:

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json path/to/brainkeeper.yaml
```

## Appendix B: Versioning

Spec versions follow SemVer with the `spec-` prefix: `spec-v0.1.0`, `spec-v0.2.0`, `spec-v1.0.0`. Breaking changes bump the major component.
