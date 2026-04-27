"""Layer 0 primitives: filesystem access for the MCP."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import frontmatter

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import BrainkeeperServer


def _resolve(srv: "BrainkeeperServer", relpath: str) -> Path:
    p = (srv.vault / relpath).resolve()
    vault_resolved = srv.vault.resolve()
    if not p.is_relative_to(vault_resolved):
        raise PermissionError(f"path escapes vault: {relpath}")
    return p


def _rel(srv: "BrainkeeperServer", path: Path) -> str:
    return str(path.resolve().relative_to(srv.vault.resolve()))


def register_primitives(mcp: "FastMCP", srv: "BrainkeeperServer") -> None:

    @mcp.tool()
    def read_note(path: str) -> dict[str, Any]:
        """Read a note: returns path, frontmatter dict, content, mtime."""
        p = _resolve(srv, path)
        if not p.is_file():
            raise FileNotFoundError(path)
        post = frontmatter.load(p)
        return {
            "path": _rel(srv, p),
            "frontmatter": dict(post.metadata or {}),
            "content": post.content,
            "mtime": p.stat().st_mtime,
        }

    @mcp.tool()
    def list_notes(
        glob: str = "**/*.md",
        with_frontmatter: bool = False,
    ) -> list[dict[str, Any]]:
        """List notes matching a glob pattern relative to vault root."""
        out: list[dict[str, Any]] = []
        for p in srv.vault.glob(glob):
            if not p.is_file():
                continue
            rel_parts = p.relative_to(srv.vault).parts
            if any(seg.startswith(".") for seg in rel_parts):
                continue
            entry: dict[str, Any] = {
                "path": _rel(srv, p),
                "mtime": p.stat().st_mtime,
            }
            if with_frontmatter:
                try:
                    post = frontmatter.load(p)
                    entry["frontmatter"] = dict(post.metadata or {})
                except Exception:
                    entry["frontmatter"] = {}
            out.append(entry)
        return out

    @mcp.tool()
    def write_note_atomic(
        path: str,
        content: str,
        frontmatter: dict[str, Any] | None = None,
        expected_mtime: float | None = None,
    ) -> dict[str, Any]:
        """Atomic write of a note. expected_mtime guards against concurrent writes."""
        p = _resolve(srv, path)
        created = not p.exists()
        if frontmatter:
            import yaml
            fm_text = yaml.safe_dump(frontmatter, sort_keys=False).rstrip()
            full = f"---\n{fm_text}\n---\n{content}"
        else:
            full = content
        mtime = srv.writer.write_atomic(p, full, expected_mtime=expected_mtime)
        srv.index.update(p)
        return {"path": _rel(srv, p), "mtime": mtime, "created": created}
