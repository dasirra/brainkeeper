# brainkeeper

A formal spec for structured, PARA-inspired Second Brain vaults, plus a Python MCP reference implementation that enforces it.

## Status

Pre-v1.0. Design complete. Implementation starts 2026-04-27.

## What this is

Two linked deliverables in one monorepo:

1. **The brainkeeper spec** — a public standard for structured Second Brain vaults. PARA-inspired, extended with Journal, System, numbered prefixes, hierarchical tags, and an explicit frontmatter contract. Tool-agnostic (works with any Markdown + YAML frontmatter vault).
2. **brainkeeper-mcp** — a Python MCP server that reads a `brainkeeper.yaml` config from a vault and enforces the spec through typed tool calls. Ships on PyPI, runs via `uvx`.

## Why

Second Brain tools like Obsidian, Logseq, and Silverbullet give you a file tree and freedom. That freedom becomes drift: "is this a Project or an Area?", "where do I archive this?", "what tags did I use for X?". CLAUDE.md-style prose rules don't enforce anything; LLMs hallucinate paths, forget conventions, and drift over sessions.

brainkeeper formalizes the shape of a well-organized vault as a schema, then ships an MCP that enforces it. The schema lives in your vault as a config file. Your agents, whether Claude Code, custom LangGraph agents, or anything else speaking MCP, all see the same conventions and can read/write your vault without breaking structure.

## Repository layout

```
brainkeeper/
├── spec/       # the brainkeeper standard (SPEC.md, JSON schema, examples)
├── mcp/        # brainkeeper-mcp Python package
└── docs/       # design docs, articles, reference material
```

`spec/` and `mcp/` will be populated as implementation progresses.

## Design

The full design document lives at [`docs/design.md`](./docs/design.md). It covers:

- The 16-section spec (structure, content model, lifecycle, implementation notes)
- The 27-tool MCP surface across three layers (primitives, convention, semantic)
- Concurrency and safety model (Syncthing-aware, atomic writes, mtime checks)
- Testing strategy, build sequence, risks, and acceptance criteria

## Timeline

- **Week 1** (Apr 27 - May 3): Spec + reference vault
- **Week 2** (May 4 - May 10): MCP core (Layers 0 and 1)
- **Week 3** (May 11 - May 15): Layer 2 + PyPI release

Target v1.0: **2026-05-15**.

## License

MIT — see [LICENSE](./LICENSE).
