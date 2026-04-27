# brainkeeper-mcp smoke test

Manual smoke test against `/Users/dasirra/Vault`.

Run:

```bash
cd mcp
uv run brainkeeper-mcp --vault /Users/dasirra/Vault
```

In another terminal, drive a tool call (requires an MCP client like `mcp-cli`):

```bash
uvx mcp-cli call brainkeeper-mcp list_layers
```

Expected output: 6 layers (`inbox`, `journal`, `projects`, `areas`, `brain`, `archive`).

For programmatic smoke test (no client needed), see `tests/integration/test_primitives.py` and `test_convention.py`.
