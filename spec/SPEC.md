# brainkeeper specification

**Version:** 0.2.0
**Status:** Draft
**Date:** 2026-05-05
**License:** MIT

## Abstract

brainkeeper is a standard for structured Markdown-based Second Brain vaults. It formalizes a PARA-inspired layer model, extended with a dated journal and a narrow archive for completed projects, and defines the content conventions (frontmatter, tags, naming, links, templates) and lifecycle rules (classification, transitions) that make a vault machine-readable without losing the flexibility that makes personal knowledge systems useful.

The spec is tool-agnostic: any editor that writes Markdown with YAML frontmatter to a local directory can produce a brainkeeper-compliant vault. A companion `brainkeeper.yaml` config file at the vault root specifies per-vault choices (folder names, layer options) and is validated against `brainkeeper.schema.json`.

## How to read this spec

- **Normative keywords.** The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY follow RFC 2119.
- **Managed notes.** A note is "managed" if it lives inside one of the six configured layers and declares the required frontmatter. Unmanaged notes (e.g. scratch files in `00 Inbox` without frontmatter) are tolerated but not guaranteed valid targets for tooling.
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

### Part IV: Implementation notes
14. Config file format
15. Extension points
16. Obsidian compatibility notes

---
## Part I: Structure

### 1. Layers

A brainkeeper vault organizes content into exactly six top-level layers. Each layer has a single purpose:

| Key         | Default path    | Purpose |
|-------------|-----------------|---------|
| `inbox`     | `00 Inbox`      | Unprocessed capture. Notes live here until triaged. |
| `journal`   | `10 Journal`    | Dated notes: dailies, meeting notes, session logs. |
| `projects`  | `20 Projects`   | Outcomes with a defined end state. |
| `areas`     | `30 Areas`      | Ongoing responsibilities without a finish line. |
| `brain`     | `40 Brain`      | Evergreen knowledge: concepts, references, notes-on-notes. |
| `archive`   | `90 Archive`    | Completed projects, preserved for history. See §12. |

The keys are canonical. Paths are user-configurable in `brainkeeper.yaml` (see §5, §14). All six keys MUST be present in the config; a vault that lacks, for example, a journal layer is out of scope for v1.

Templates and other vault meta-files are not their own layers. Templates colocate inside the layer they serve (see §10).

### 2. Numbered prefixes

The default paths use a Johnny Decimal-inspired numeric prefix convention: `00 Inbox`, `10 Journal`, `20 Projects`, `30 Areas`, `40 Brain`, `90 Archive`. Gaps (50, 60, 70, 80) are deliberate and reserved for user expansion; a tool-specific vault might add a `50 Media` or `70 Reference` layer outside of the six canonical keys.

Prefixes are a convention, not a requirement. A vault MAY use non-numeric names (see §5 and the `zettelkasten.yaml` example) as long as the six layer keys map to valid relative paths.

### 3. Reserved paths

A conforming vault MUST contain the six layer directories at the configured paths. Tooling MAY auto-create any missing layer directory on startup. Two path conventions are additionally reserved:

- **`<archive>/<YYYY>/`**. If the `archive` layer uses `year_subfolder: true` (default), tooling creates per-year subfolders on demand when archiving.
- **`<layer>/_templates/`**. Each layer that uses templates places them under a `_templates/` subfolder (see §10). The underscore prefix marks the folder as meta (not a content folder) while keeping it visible in Obsidian's sidebar so users can edit templates from the same UI they use for notes.

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

This rule applies to all spec-reserved concepts: template file names (§10) are user-configurable strings mapped through the config file.


## Part II: Content model

### 6. Frontmatter contract

Every **managed note** MUST begin with a YAML frontmatter block delimited by `---` lines. Minimum required fields:

```yaml
---
created: 2026-04-24
updated: 2026-05-01
tags:
  - topic/mcp
  - project/brainkeeper
---
```

**Required fields:**

| Field     | Type           | Allowed values |
|-----------|----------------|----------------|
| `created` | `YYYY-MM-DD`   | ISO date, never empty. Set once when the note is first written. |
| `updated` | `YYYY-MM-DD`   | ISO date, never empty. Set to `created` on first write; refreshed to today on every subsequent edit. MUST be ≥ `created`. |
| `tags`    | list of string | At least one tag. See §7. |

**Extension rule.** Any additional fields are permitted and ignored by the spec. Tooling SHOULD pass unknown fields through unchanged on write (read-modify-write preserves user fields). The spec is intentionally minimal — vault- or tool-specific concerns (lifecycle status, deadlines, course metadata, etc.) live as user-defined fields under the extension rule.

**Note classification.** The spec does not define a `type` field. A note's role is conveyed by the combination of its layer (folder), tags, and filename pattern. For example, a file at `20 Projects/Brainkeeper/Brainkeeper Index.md` with `tags: [project/brainkeeper]` is unambiguously a project entry-point note without needing an explicit `type` field.


### 7. Tag taxonomy

Every managed note carries at least one tag (see §6). Tags are the primary classification axis: they cross-cut the folder hierarchy, letting queries span all six layers.

**Grammar.** Tags are lowercase kebab-case strings. Tooling MUST validate the pattern `^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$`. The optional `prefix/value` form is allowed for users who want soft hierarchy (`topic/mcp`, `area/finance`); use it if it helps you find notes later, skip it if it doesn't. Singular form is recommended (`person/daniel`, not `people/daniels`).

**No prescribed dimensions.** brainkeeper does not require any particular tag prefix or vocabulary. Pick names that make sense for your vault. The `#` prefix is NOT included in the YAML value:

```yaml
tags:
  - mcp
  - pkm
  - obsidian
  - topic/spec   # prefix form, optional
```

**Guiding principle.** Tag what the folder path does not already encode. A file under `20 Projects/Brainkeeper/` is already known to belong to the Brainkeeper project; tagging it `brainkeeper` again is redundant but not wrong. A note in `40 Brain/` benefits from tags because the folder alone says nothing about what the note is about.


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

Templates colocate with the layer they serve. Each layer that uses templates places them inside a `_templates/` subfolder:

| Path                               | Purpose |
|------------------------------------|---------|
| `<journal>/_templates/Daily.md`    | Template for daily journal notes. |
| `<journal>/_templates/Meeting.md`  | Template for meeting notes. |
| `<projects>/_templates/Project.md` | Template for new project notes. |
| `<areas>/_templates/Area Index.md` | Template for area entry-point notes. |
| `<areas>/_templates/Idea.md`       | Template for captured ideas. |

The `_templates/` underscore-prefix marks the folder as meta (not a content folder). Unlike a hidden dot-folder, it remains visible in Obsidian's sidebar so users can browse and edit templates from the same UI they use for notes. It moves automatically with the layer when the user renames a folder in `brainkeeper.yaml`, so bilingual and alternate-convention vaults need no additional config. Tooling MUST treat `_templates/` as meta (skip from indexing and content queries) and MAY auto-create it on demand.

**Substitution.** Templates support simple `{{variable}}` substitution. Defined variables:

| Variable    | Meaning |
|-------------|---------|
| `{{date}}`  | Date the note refers to (`YYYY-MM-DD`). |
| `{{today}}` | Today's date (`YYYY-MM-DD`). |
| `{{title}}` | Title of the note being created. |

Unknown variables MUST be left untouched by substituting tools (no silent deletion). Additional variables MAY be defined by tooling as long as they do not collide with the reserved names above.

## Part III: Lifecycle

### 11. Classification rules

A new note with no obvious destination SHOULD be written to the `inbox` layer. Triage moves the note to its final layer. The spec does not prescribe a routing mechanism: callers are responsible for choosing a target path inside the vault, using the layer map (§1), the tag taxonomy (§7), and the naming conventions (§8) as guidance.

### 12. Transition rules

Only three layer-to-layer transitions are part of the standard:

| From                    | To                        | Trigger |
|-------------------------|---------------------------|---------|
| `inbox`                 | any layer                 | Triage |
| `areas/Ideas`           | `projects`                | Idea matures into a bounded outcome |
| `projects`              | `archive/YYYY`            | Project completed or abandoned |

On an archive transition, tools MUST:
- Move the file to `<archive>/<YYYY>/`.
- Set `updated: YYYY-MM-DD` to today (per §6, every write refreshes `updated`).
- Preserve all other frontmatter fields unchanged.

Tooling MAY add user-defined fields (e.g. `archived_on`, lifecycle markers) under the extension rule, but the spec itself imposes no archive-specific frontmatter mutations beyond `updated`.

**On retiring an area.** brainkeeper does not archive areas. An Area that becomes irrelevant SHOULD be either deleted outright or have its essential knowledge distilled into `brain/` before deletion. This keeps the archive layer narrow and semantically crisp: archive is a record of completed projects, not a catch-all for retired vault sections.

Other moves (e.g. `brain` to `archive`) are not blessed by the spec. Tools MAY refuse unknown transitions or require explicit user confirmation.

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
  projects: "20 Projects"
  areas: "30 Areas"
  brain: "40 Brain"
  archive:
    path: "90 Archive"
    year_subfolder: true
```

**Shorthand vs object form for layers.** Each layer entry accepts either a string (shorthand: path only) or an object (when the layer needs additional options: `format`, `year_subfolder`). The schema defines which options apply to which layers.

**Path rules.** Paths under `layers.*` are vault-relative. Leading `/` is invalid. `..` segments are invalid.

**Minimum viable config.** See [`examples/minimal.yaml`](./examples/minimal.yaml).

### 15. Extension points

The following additions do NOT require a change to the spec or the schema. They are expressible in config alone:

- Adding a new template: drop a `.md` file into `<layer>/_templates/` inside the relevant layer.
- Renaming any folder: change the corresponding path under `layers:`.

Tooling SHOULD support live config reload: changes to `brainkeeper.yaml` should take effect without a restart.

### 16. Obsidian compatibility notes

The spec is tool-agnostic. Nothing in Parts I to III depends on Obsidian. This section documents compatibility choices that make a brainkeeper vault cleanly openable in Obsidian:

- **Wikilink syntax.** `[[Note Name]]` is Obsidian's native link style (§9).
- **YAML frontmatter.** The Properties feature in Obsidian reads the same `---` front block (§6).
- **Folder names.** Arbitrary strings; Obsidian imposes no folder naming rules beyond the OS filesystem.
- **Templates.** The `{{date}}` / `{{title}}` variables map onto Obsidian's Templates core plugin. The `_templates/` underscore-folder convention keeps templates visible in the sidebar (so they can be edited like any other note) while marking them as meta so brainkeeper tooling excludes them from indexing. Users who prefer the Templater community plugin MAY use its richer syntax inside template files as long as the reserved variables keep their brainkeeper meaning.

brainkeeper vaults work equally well in Logseq, Silverbullet, and plain-text editors, provided the editor preserves YAML frontmatter and does not rewrite wikilinks into Markdown links.

---

## Appendix A: Schema

The canonical JSON Schema is at [`schema/brainkeeper.schema.json`](./schema/brainkeeper.schema.json). Validate a config with:

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json path/to/brainkeeper.yaml
```

## Appendix B: Versioning

Spec versions follow SemVer with the `spec-` prefix: `spec-v0.1.0`, `spec-v0.2.0`, `spec-v1.0.0`. Breaking changes bump the major component.
