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
