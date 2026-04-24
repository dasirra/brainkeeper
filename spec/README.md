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
