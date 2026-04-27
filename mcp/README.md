# brainkeeper-mcp

Reference MCP server implementing the [brainkeeper spec](../spec/SPEC.md).

Loads a `brainkeeper.yaml` from a vault root, indexes notes in memory, and exposes typed tool calls over stdio.

## Quickstart

```bash
uvx brainkeeper-mcp --vault /path/to/your/vault
```

The vault must contain a valid `brainkeeper.yaml`. See [`spec/examples/`](../spec/examples/).

## Status

v0.1-alpha. Layer 0 (5 primitives) + Layer 1 (5 convention tools). Layer 2 semantic ops are forthcoming.
