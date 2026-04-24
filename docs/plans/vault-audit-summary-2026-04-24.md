# Vault audit summary (2026-04-24)

Aggregate findings from running `tools/audit_vault.py` against the vault. No file paths or per-note content from the vault are included here; the full detail report lives locally at `~/vault-audit-2026-04-24.md` (gitignored).

**Spec baseline:** `spec-v0.1.0` (6 canonical layers, colocated `.templates/`, archive-for-projects-only).

## Scale

- 305 markdown files across the vault.
- Five of the six canonical layers are present at top level with exact Johnny-Decimal names (`00 Inbox`, `10 Journal`, `20 Projects`, `30 Areas`, `40 Brain`).
- The sixth canonical layer (`archive`) is not top-level: the current `Archive/` is nested inside a legacy `90 System/` folder along with `Templates/`.
- One loose `.md` file sits at vault root and should move into a layer.

## Compliance scorecard

| Dimension | Compliance | Notes |
|---|---|---|
| Layer structure | 5/6 layers mapped | `archive` needs promotion from `90 System/Archive/` to `90 Archive/`; `90 System/` itself is removed. |
| Frontmatter presence | 13% of notes have any frontmatter | **biggest gap** |
| Frontmatter completeness | 1% of notes carry all 4 required fields | 3 of 305 notes fully compliant |
| Type enum | 9 violations across 8 distinct invalid values | e.g. `research`, `synthesis`, `playbook`, `financial-model`, `reference`, `market-research` |
| Status enum | 24 violations across 8 distinct invalid values | most common: `idea` (8), `draft` (4), `summarized` (4), `final-v3` (2); others are one-offs including one Spanish-cased `exploracion` |
| Date format | 3 violations | small |
| Naming convention | clean | journal filenames + project/area folder names already compliant |
| Link style | 98% wikilink | only 5 markdown-style internal links out of 296 |
| Tag grammar | 2 violations | both uppercase-only values (`VSME`, `ESG`) |
| Archive scope | 0% project-shaped | 4 archived folders exist but none declare `type: project` in frontmatter, so the classifier sees none. Almost certainly a frontmatter-absence artifact rather than a scope problem. |
| Templates location | 0% colocated | 4 legacy template locations exist (under `90 System/Templates/` and peers); all need migration to `<layer>/.templates/`. |
| Cruft | 15 `.DS_Store`, 5 empty folders, 22 possibly-orphan attachments | mostly cosmetic |

## Interpretation

Strengths:
- Folder structure is nearly spec-compliant out of the box. Renaming `90 System/` to promote its children is a small change.
- Wikilink discipline is already excellent (98%).
- Naming conventions are already clean (no prefixed project folders, no misnamed daily notes).
- Tag grammar is almost perfect (2 exceptions, both uppercase acronyms).

Gaps, ranked by effort needed:
1. **Frontmatter (biggest).** 302 of 305 notes lack full frontmatter. Remediation requires type/status inference per note, which is a large pass (possibly LLM-assisted).
2. **Status vocabulary drift.** 24 violations across distinct ad-hoc statuses (`idea`, `draft`, `summarized`, `final-vN`, `exploracion`). Some of these suggest missing type values (e.g. `idea` is properly a `type` not a `status`). Remediation = decide mapping rules, then batch-apply.
3. **Type vocabulary drift.** Custom types in use (`research`, `playbook`, `financial-model`, etc.) that aren't in the spec enum. Two options: extend the spec enum, or remap to the closest existing type. Worth revisiting in a spec-v0.2 conversation.
4. **Archive shape.** Four archived cohort/project folders need `type: project` frontmatter to be recognized. Once frontmatter lands, the archive scope check should pass cleanly.
5. **Templates migration.** All 4 legacy locations need to move to colocated `.templates/` inside the corresponding layer, then `90 System/` can be deleted.
6. **Cruft cleanup.** `.DS_Store` purge, empty folder check, orphan attachment triage. Low effort.

## Suggested next steps

A follow-up remediation plan should address these in roughly this order (cheapest first):
1. Write `brainkeeper.yaml` at the vault root matching current (legacy) paths. Tool can validate against the schema.
2. Promote `90 System/Archive/` to `90 Archive/`; migrate `90 System/Templates/` contents to colocated `.templates/` inside each layer; remove `90 System/`.
3. Cruft pass (`.DS_Store` delete, empty folder remove, orphan attachment triage).
4. Decide spec-level question: extend the `type` enum to include the custom types found (`research`, `playbook`, etc.) or remap them.
5. Batch frontmatter pass (biggest and most labor-intensive).
6. Re-run `tools/audit_vault.py` to confirm compliance.
