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
