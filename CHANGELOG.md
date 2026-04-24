# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two artifacts are versioned independently:
- **`spec-vX.Y.Z`**: the brainkeeper specification (`spec/`).
- **`mcp-vX.Y.Z`**: the `brainkeeper-mcp` Python package (forthcoming).

## [spec-v0.1.0] - 2026-04-24

### Added
- Initial public draft of the `brainkeeper` specification (`spec/SPEC.md`).
- JSON Schema for `brainkeeper.yaml` (`spec/schema/brainkeeper.schema.json`).
- Three reference configs: `minimal.yaml`, `daniels-vault.yaml`, `zettelkasten.yaml`.
- Negative-test fixtures under `spec/examples/.invalid/`.
- Six-layer structural model (`inbox`, `journal`, `projects`, `areas`, `brain`, `archive`) with colocated per-layer templates under `<layer>/.templates/`.
- Archive semantics narrowed to completed projects only; retired Areas are deleted or distilled into Brain, not archived.
- Domain tags: cardinality relaxed to 0..n (optional but recommended); vocabulary derived from folders under `projects/` and `areas/` rather than an enumerated list in the config.

[spec-v0.1.0]: https://github.com/dasirra/brainkeeper/releases/tag/spec-v0.1.0
