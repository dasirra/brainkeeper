# Vault remediation plan (2026-04-24)

## Context

The audit (`docs/plans/vault-audit-summary-2026-04-24.md`) measured 305 notes against `spec-v0.1.0`. Layer structure is nearly compliant, naming and links are clean, but frontmatter coverage is 1% and templates / archive need restructuring. This plan remediates the vault without extending the spec: custom `type` and `status` values will be remapped to the canonical enums.

The vault at `/Users/dasirra/Vault` is not a git repository. Before any destructive phase, we take a tarball snapshot to `~/vault-backups/` as recovery insurance.

Each phase below ends with a user-facing checkpoint. Nothing proceeds to the next phase without your explicit OK.

## Phase ordering (safest first)

1. **Pre-flight snapshot + `brainkeeper.yaml`** (non-destructive)
2. **Cruft cleanup** (mechanical, reversible via snapshot)
3. **Tag grammar fixes** (2 notes)
4. **Link conversions** (5 notes)
5. **Structural rename** (move `90 System/Archive/` → `90 Archive/`; colocate templates; remove `90 System/`)
6. **Enum remap decisions** (you choose mappings)
7. **Frontmatter pass** (302 notes; LLM-assisted, dry-run first)
8. **Re-audit** (confirm compliance)

## Phase details

### Phase 1: Snapshot + `brainkeeper.yaml`

1.1. Create `~/vault-backups/vault-backup-<timestamp>.tar.gz` via `tar -czf`. Record SHA256.
1.2. Write `/Users/dasirra/Vault/brainkeeper.yaml` matching current folder paths (object form for `journal`, `projects`, `archive`; string for the rest). Validate against the schema.
1.3. Verify audit tool still runs and report a 1-check-changed delta (archive layer now found at top-level... wait, not yet, `brainkeeper.yaml` is a config file and the audit doesn't read it. So no audit delta expected from this phase alone.).

Checkpoint: show the generated config, get approval. No vault content changed.

### Phase 2: Cruft cleanup

2.1. Delete 15 `.DS_Store` files. Safe: macOS regenerates on demand.
2.2. Remove 5 empty folders (list them for user confirmation first).
2.3. Orphan attachments (22 files): show each group to user. We do not auto-delete. User marks keep/delete per item.

Checkpoint: confirm each batch. Re-run audit's cruft check to confirm zero after.

### Phase 3: Tag grammar fixes

Two tags violate grammar: `VSME` and `ESG`. Options per tag:
- Lowercase: `vsme`, `esg` (bare tag, no prefix — weak)
- Canonicalize with prefix: `topic/vsme`, `topic/esg` (recommended)

Apply in-place edits to the 1 affected file per tag.

Checkpoint: show before/after, approve.

### Phase 4: Link conversions

5 internal markdown links like `[text](./path.md)` convert to `[[path|text]]` or `[[path]]`. Apply per-file Edit operations.

Checkpoint: show each conversion before applying.

### Phase 5: Structural rename

5.1. For each file under `90 System/Templates/`, classify which layer it should move to (by name: `Daily.md` → `10 Journal/.templates/Daily.md`; `Project.md` → `20 Projects/.templates/Project.md`; etc.). Show mapping, get approval.
5.2. Move `90 System/Templates/*` to the colocated `.templates/` in each layer.
5.3. Move `90 System/Archive/*` to `90 Archive/*` (create `90 Archive/` at top level first if needed).
5.4. Delete `90 System/` (should now be empty).
5.5. Update `brainkeeper.yaml` with the new `archive` path.
5.6. Update `20 Projects/.templates/` if it already exists (audit showed it at 0; this phase creates it).

Checkpoint: run audit, confirm structure check now shows all 6 layers + templates colocated.

### Phase 6: Enum remap decisions

Present the violation breakdown:
- Type violations (9 files across 8 distinct values): `research`, `synthesis`, `playbook`, `financial-model`, `linkedin-post`, `reference`, `product-idea`, `market-research`.
- Status violations (24 files across 8 distinct values): `idea`, `draft`, `summarized`, `final-v3`, `published`, `draft-v4`, `passed`, `exploracion`.

User provides a mapping table (custom → canonical). I propose defaults; user edits if desired. Example:

| Custom type | → | Canonical type |
|---|---|---|
| `research` | → | `knowledge` |
| `reference` | → | `resource` |
| `linkedin-post` | → | `note` |
| `product-idea` | → | `idea` |
| ... | | ... |

| Custom status | → | Canonical status |
|---|---|---|
| `idea` | → | (move to `type: idea`, status becomes `active`) |
| `draft`, `draft-v4` | → | `active` |
| `summarized`, `published`, `final-v3`, `passed` | → | `completed` |
| `exploracion` | → | `active` |

Apply the mapping via `Edit` per-file.

Checkpoint: show mapping, approve, then apply.

### Phase 7: Frontmatter pass

302 of 305 notes lack full frontmatter. Inference rules:
- `type`: from path (`10 Journal/*.md` = journal or meeting; `20 Projects/<P>/...` = project/note; `40 Brain/...` = knowledge default; `30 Areas/...` = note or area; `00 Inbox/...` = note; `90 Archive/*` = project inside archived project folders, else whatever's most plausible).
- `status`: default `active`; `archived` for anything under `90 Archive/`.
- `created`: first 10-character `YYYY-MM-DD` string found in content or filename; else file mtime from filesystem.
- `tags`: at least 1; default inferred as `domain/<kebab-case top-level area/project folder name>` when possible.

**Dry-run first.** The tool emits a `frontmatter-patches.json` of proposed changes per file (no writes). User skims a sample of say 20 patches (we pick a mix: one per layer, plus edge cases). If acceptable, bulk apply. If not, tune inference rules and re-dry-run.

Because this is destructive across 302 files, we batch by layer:
- 7.1: journal notes (well-constrained: dates from filenames).
- 7.2: project notes (fine-grained; nested folders imply `project/` tag).
- 7.3: area notes.
- 7.4: brain notes.
- 7.5: inbox notes.
- 7.6: archive notes.

Checkpoint after each sub-phase: spot-check a dozen files.

### Phase 8: Re-audit

Run `tools/audit_vault.py` again. Confirm:
- Structure: 6/6 canonical (archive top-level, no System).
- Frontmatter coverage: target 100% (allow dropouts if user intentionally left some notes unmanaged).
- Enums: 0 violations.
- Templates: 100% colocated.
- Links + tags: still clean.
- Archive scope: now project-shaped.

Write a delta summary to `docs/plans/vault-audit-summary-2026-04-24.md` (append a "post-remediation" section) so the before/after is captured.

## Tooling we will write or reuse

- Existing: `tools/audit_vault.py`. Used for baseline + re-audit.
- New: `tools/snapshot_vault.sh` — tarball + SHA256.
- New: `tools/remediate_frontmatter.py` — dry-run/apply tool with inference rules. Takes a vault path and optional `--dry-run`.
- New: `tools/remediate_enum_remap.py` — consumes a mapping YAML, applies type/status rewrites. 

Each of these, like the audit tool, lives under `tools/` and is committed.

## Verification

- Snapshot exists and SHA256 matches `tar tzf` spot-check.
- After each phase, `tools/audit_vault.py` shows the expected improvement.
- After Phase 8, no enum violations, no tag grammar violations, no cruft, all 6 layers canonical.

## Open questions before Phase 1

1. Backup location OK at `~/vault-backups/`, or prefer elsewhere?
2. If Syncthing is running during remediation, should we pause it first? (Syncthing mid-move can cause conflict files.)
3. Any notes you want me to skip / leave in legacy shape? (e.g. drafts you know are work-in-progress.)
