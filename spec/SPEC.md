# brainkeeper specification

**Version:** 0.1.0
**Status:** Draft (first public release)
**Date:** 2026-04-24
**License:** MIT

## Abstract

brainkeeper is a standard for structured Markdown-based Second Brain vaults. It formalizes a PARA-inspired layer model, extended with a dated journal and a narrow archive for completed projects, and defines the content conventions (frontmatter, tags, naming, links, templates) and lifecycle rules (classification, transitions, status) that make a vault machine-readable without losing the flexibility that makes personal knowledge systems useful.

The spec is tool-agnostic: any editor that writes Markdown with YAML frontmatter to a local directory can produce a brainkeeper-compliant vault. A companion `brainkeeper.yaml` config file at the vault root specifies per-vault choices (folder names, domain list, capture routes) and is validated against `brainkeeper.schema.json`.

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
13. Status semantics

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
- **`<layer>/.templates/`**. Each layer that uses templates places them under a hidden `.templates/` subfolder (see §10). The dot-prefix hides the folder from Obsidian's sidebar and from shell globs.

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

This rule applies to all spec-reserved concepts: template file names (§10), status values (§13), and capture routes (§14) are user-configurable strings mapped through the config file. Domain tag values (§7) derive from folder names under `projects/` and `areas/`, so renaming a folder renames the domain.


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

| Prefix     | Cardinality | Required?   | Value source |
|------------|-------------|-------------|--------------|
| `domain/`  | 0..n        | recommended | Derived from folder names under `projects/` and `areas/` (see "Domain vocabulary" below). |
| `topic/`   | 0..n        | recommended | Free (user-defined vocabulary). |
| `project/` | 0..n        | required on notes related to an active project | Free; SHOULD match a project folder slug. |
| `person/`  | 0..n        | optional    | Free (meeting and 1-on-1 notes). |

**Syntax rules:**

- Lowercase only.
- Kebab-case (words joined by `-`).
- Singular form (`person/daniel`, not `people/daniels`).
- YAML list form. The `#` prefix is NOT included in the YAML value:

  ```yaml
  tags:
    - domain/fitizens
    - topic/mcp
    - project/brainkeeper
  ```

- At least one tag of any dimension is required on every managed note (see §6).

**Guiding principle.** Tag what the folder path does not already encode. A file under `20 Projects/Brainkeeper/` already implies `project/brainkeeper`; adding it is redundant but not wrong. A note in `40 Brain/` about the MCP protocol benefits from `topic/mcp` because `40 Brain/` alone does not convey it.

**Why domain tags.** Domains are the cross-cutting axis the folder tree cannot represent. Folders classify notes by *kind* (project, journal, knowledge); domains classify by *life area* (fitizens, teaching, family). A Brain note and a Journal entry can both carry `domain/fitizens`, supporting queries that span all six layers. Concrete uses:

- **Per-domain filtering.** "All active notes in `domain/teaching`" crosses Projects, Journal, Areas, Brain.
- **Context-aware capture.** Tooling or an agent can inject the active domain during note creation.
- **Analytics.** Aggregate queries ("hours logged per domain this month") become natural.
- **Agent routing.** Domain tags are the single most useful filter when an agent acts on a subset of the vault.

**Domain vocabulary.** brainkeeper does NOT require a fixed domain list in `brainkeeper.yaml`. The vocabulary is derived from folder structure:

- A direct subfolder of `projects/` at path `projects/<Name>/` yields a valid domain value `kebab-case(<Name>)`.
- A direct subfolder of `areas/` at path `areas/<Name>/` yields a valid domain value `kebab-case(<Name>)`.

Kebab-case conversion lowercases the name, replaces whitespace runs with a single `-`, and strips characters outside `[a-z0-9-]`. `Fitizens` becomes `fitizens`; `Home Lab` becomes `home-lab`; `AI Research` becomes `ai-research`.

Tooling and LLM-driven capture SHOULD infer the domain tag from the destination folder path or from content context, preferring existing domains (folders that already exist) over inventing new values. Creating a new domain is equivalent to creating a new top-level subfolder under `projects/` or `areas/`. Renaming a folder renames the domain from that point forward; historical tags continue to refer to the old value.

**Domain tag grammar.** Domain values MUST be lowercase kebab-case (regex: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, length 2 to 40). Tooling SHOULD reject tags that fail this pattern. Tooling SHOULD NOT reject a tag solely for not appearing in a prior enum, since the vocabulary is implicit and evolves with the folder tree.


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

Templates colocate with the layer they serve. Each layer that uses templates places them inside a hidden `.templates/` subfolder:

| Path                               | Purpose |
|------------------------------------|---------|
| `<journal>/.templates/Daily.md`    | Template for daily journal notes. |
| `<journal>/.templates/Meeting.md`  | Template for meeting notes. |
| `<projects>/.templates/Project.md` | Template for new project notes. |
| `<areas>/.templates/Area Index.md` | Template for area entry-point notes. |
| `<areas>/.templates/Idea.md`       | Template for captured ideas. |

The `.templates/` dot-folder is hidden from Obsidian's sidebar and from default shell globs. It moves automatically with the layer when the user renames a folder in `brainkeeper.yaml`, so bilingual and alternate-convention vaults need no additional config. Tooling MAY auto-create `.templates/` on demand.

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

Only three layer-to-layer transitions are part of the standard:

| From                    | To                        | Trigger |
|-------------------------|---------------------------|---------|
| `inbox`                 | any layer                 | Triage |
| `areas/Ideas`           | `projects`                | Idea matures into a bounded outcome |
| `projects`              | `archive/YYYY`            | Project completed or abandoned |

On an archive transition, tools MUST:
- Set `status` to `archived` in frontmatter (see §13).
- Set `archived: YYYY-MM-DD` to today.
- Preserve all other frontmatter fields unchanged.

**On retiring an area.** brainkeeper does not archive areas. An Area that becomes irrelevant SHOULD be either deleted outright or have its essential knowledge distilled into `brain/` before deletion. This keeps the archive layer narrow and semantically crisp: archive is a record of completed projects, not a catch-all for retired vault sections.

Other moves (e.g. `brain` to `archive`) are not blessed by the spec. Tools MAY refuse unknown transitions or require explicit user confirmation.

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
  projects:
    path: "20 Projects"
    status_field: status
    active_values: ["active", "🟢"]
  areas: "30 Areas"
  brain: "40 Brain"
  archive:
    path: "90 Archive"
    year_subfolder: true

capture_routing:
  idea:    "30 Areas/Ideas/Inbox.md"
  todo:    "00 Inbox/Todos.md"
  meeting: "10 Journal/{today}.md#Meetings"
  default: "00 Inbox/"
```

**Shorthand vs object form for layers.** Each layer entry accepts either a string (shorthand: path only) or an object (when the layer needs additional options: `format`, `status_field`, `active_values`, `year_subfolder`). The schema defines which options apply to which layers.

**Path rules.** Paths under `layers.*` are vault-relative. Leading `/` is invalid. `..` segments are invalid.

**Capture routes.** A route value ending in `/` denotes a folder (new file per capture). A bare path denotes append-to-file. A `#Anchor` suffix targets a heading inside that file. The token `{today}` is substituted with the current date (`YYYY-MM-DD`).

**Minimum viable config.** See [`examples/minimal.yaml`](./examples/minimal.yaml).

### 15. Extension points

The following additions do NOT require a change to the spec or the schema. They are expressible in config alone:

- Adding a new domain: create a folder under `projects/` or `areas/` with the domain name in Title Case. Tooling derives the `domain/<kebab-case>` tag value from the folder name.
- Adding a new capture route: add a key under `capture_routing:`.
- Adding a new template: drop a `.md` file into `<layer>/.templates/` inside the relevant layer.
- Renaming any folder: change the corresponding path under `layers:`.

Tooling SHOULD support live config reload: changes to `brainkeeper.yaml` should take effect without a restart. Domain tag values reflect current folder structure; deleting a domain folder does not invalidate historical tags but new captures SHOULD NOT reuse the removed value.

### 16. Obsidian compatibility notes

The spec is tool-agnostic. Nothing in Parts I to III depends on Obsidian. This section documents compatibility choices that make a brainkeeper vault cleanly openable in Obsidian:

- **Wikilink syntax.** `[[Note Name]]` is Obsidian's native link style (§9).
- **YAML frontmatter.** The Properties feature in Obsidian reads the same `---` front block (§6).
- **Folder names.** Arbitrary strings; Obsidian imposes no folder naming rules beyond the OS filesystem.
- **Templates.** The `{{date}}` / `{{title}}` variables map onto Obsidian's Templates core plugin. The `.templates/` dot-folder convention keeps templates out of the sidebar and search results. Users who prefer the Templater community plugin MAY use its richer syntax inside template files as long as the reserved variables keep their brainkeeper meaning.

brainkeeper vaults work equally well in Logseq, Silverbullet, and plain-text editors, provided the editor preserves YAML frontmatter and does not rewrite wikilinks into Markdown links.

---

## Appendix A: Schema

The canonical JSON Schema is at [`schema/brainkeeper.schema.json`](./schema/brainkeeper.schema.json). Validate a config with:

```bash
uvx check-jsonschema --schemafile spec/schema/brainkeeper.schema.json path/to/brainkeeper.yaml
```

## Appendix B: Versioning

Spec versions follow SemVer with the `spec-` prefix: `spec-v0.1.0`, `spec-v0.2.0`, `spec-v1.0.0`. Breaking changes bump the major component.
