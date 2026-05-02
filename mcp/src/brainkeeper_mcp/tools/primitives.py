"""Layer 0 primitives: filesystem access for the MCP."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import frontmatter as fm_lib
import yaml

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
        post = fm_lib.load(p)
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
            if any(seg.startswith(".") or seg == "_templates" for seg in rel_parts):
                continue
            entry: dict[str, Any] = {
                "path": _rel(srv, p),
                "mtime": p.stat().st_mtime,
            }
            if with_frontmatter:
                try:
                    post = fm_lib.load(p)
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
        """Atomic write of a note.

        When `frontmatter` is provided, `created` and `updated` are auto-managed
        per spec v0.1.3 §6:
        - On first write of a path, `created` defaults to today if not provided.
        - On overwrite of an existing path, on-disk `created` is preserved if
          not provided.
        - `updated` is always refreshed to today.

        `expected_mtime` guards against concurrent writes.
        """
        p = _resolve(srv, path)
        is_new = not p.exists()
        today = date.today().isoformat()

        if frontmatter is not None:
            fm = dict(frontmatter)
            if not is_new and "created" not in fm:
                try:
                    existing = fm_lib.load(p).metadata or {}
                    if "created" in existing:
                        v = existing["created"]
                        fm["created"] = v.isoformat()[:10] if hasattr(v, "isoformat") else str(v)
                except Exception:
                    pass
            fm.setdefault("created", today)
            fm["updated"] = today
            fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip()
            full = f"---\n{fm_text}\n---\n{content}"
        else:
            full = content

        mtime = srv.writer.write_atomic(p, full, expected_mtime=expected_mtime)
        srv.index.update(p)
        return {"path": _rel(srv, p), "mtime": mtime, "created": is_new}

    @mcp.tool()
    def move_note(src: str, dst: str) -> dict[str, Any]:
        """Move a note. v1 does NOT rewrite wikilinks."""
        s = _resolve(srv, src)
        d = _resolve(srv, dst)
        if not s.is_file():
            raise FileNotFoundError(src)
        d.parent.mkdir(parents=True, exist_ok=True)
        s.replace(d)
        srv.index.remove(s)
        srv.index.update(d)
        return {
            "from": _rel(srv, s),
            "to": _rel(srv, d),
            "wikilinks_broken": [],
        }

    @mcp.tool()
    def delete_note(path: str, soft: bool = True) -> dict[str, Any]:
        """Delete a note. soft=True moves to <archive>/<YYYY>/."""
        p = _resolve(srv, path)
        if not p.is_file():
            raise FileNotFoundError(path)
        if soft:
            archive_dir = srv.config.layer_path("archive")
            opts = srv.config.layers.archive
            if opts.year_subfolder:
                archive_dir = archive_dir / str(date.today().year)
            archive_dir.mkdir(parents=True, exist_ok=True)
            target = archive_dir / p.name
            p.replace(target)
            srv.index.remove(p)
            srv.index.update(target)
            return {"path": _rel(srv, p), "destination": _rel(srv, target)}
        else:
            p.unlink()
            srv.index.remove(p)
            return {"path": _rel(srv, p), "destination": None}
