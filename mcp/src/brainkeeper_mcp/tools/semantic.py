"""Layer 2 semantic tools: query, hygiene, and lifecycle over the index."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import frontmatter as fm_lib
import yaml

from ..frontmatter import FrontmatterParser

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import BrainkeeperServer


def _resolve(srv: "BrainkeeperServer", relpath: str) -> Path:
    p = (srv.vault / relpath).resolve()
    if not p.is_relative_to(srv.vault.resolve()):
        raise PermissionError(f"path escapes vault: {relpath}")
    return p


def _rel(srv: "BrainkeeperServer", path: Path) -> str:
    return str(path.resolve().relative_to(srv.vault.resolve()))


def _summary(srv: "BrainkeeperServer", meta) -> dict[str, Any]:
    return {
        "path": _rel(srv, meta.path),
        "frontmatter": meta.frontmatter,
        "mtime": meta.mtime,
    }


def register_semantic(mcp: "FastMCP", srv: "BrainkeeperServer") -> None:

    @mcp.tool()
    def find_by_tag(tag: str, prefix_match: bool = True) -> list[dict[str, Any]]:
        """Find managed notes whose tags include the given value.

        With `prefix_match=True` (default), matches any tag that starts with
        the query. Use this for dimension queries like `topic/` (all topic
        tags) or `domain/fitizens` (all notes in that domain — also matches
        any deeper hierarchy under it).

        With `prefix_match=False`, only exact matches are returned.

        A leading '#' is stripped from both the query and stored tags so
        `#topic/mcp` and `topic/mcp` behave the same.
        """
        needle = tag.lstrip("#")
        out: list[dict[str, Any]] = []
        for p in srv.index.paths():
            meta = srv.index.get(p)
            if not meta:
                continue
            tags = meta.frontmatter.get("tags") or []
            if not isinstance(tags, list):
                continue
            normalized = [t.lstrip("#") for t in tags if isinstance(t, str)]
            if prefix_match:
                hit = any(t.startswith(needle) for t in normalized)
            else:
                hit = needle in normalized
            if hit:
                out.append(_summary(srv, meta))
        return out

    @mcp.tool()
    def find_orphans() -> list[dict[str, Any]]:
        """Return all notes that fail spec validation.

        Each entry includes the path, the validation errors detected during
        the last index scan, and the parsed frontmatter for context.
        """
        return [
            {
                "path": _rel(srv, m.path),
                "errors": m.validation_errors,
                "frontmatter": m.frontmatter,
                "mtime": m.mtime,
            }
            for m in srv.index.orphans()
        ]

    @mcp.tool()
    def validate_frontmatter(path: str) -> dict[str, Any]:
        """Validate a single note's frontmatter against the spec.

        Re-reads the file from disk (does not rely on the index), so callers
        can validate notes that aren't yet indexed. Returns `{path, valid,
        errors, frontmatter}`.
        """
        p = _resolve(srv, path)
        if not p.is_file():
            raise FileNotFoundError(path)
        parser = FrontmatterParser()
        meta, _ = parser.parse(p)
        errors = parser.validate(meta)
        return {
            "path": _rel(srv, p),
            "valid": not errors,
            "errors": errors,
            "frontmatter": meta,
        }

    @mcp.tool()
    def update_frontmatter(path: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Apply a partial frontmatter update to a note.

        Each key in `patch` overrides the corresponding key in the existing
        frontmatter; keys not in `patch` are preserved unchanged. To delete
        a key, pass its value as `None`.

        `updated` is always refreshed to today regardless of what `patch`
        contains — the tool owns this field per spec §6. `created` is
        preserved from disk if missing from `patch`; on a previously-
        unmanaged file (no frontmatter), it defaults to today.

        Returns `{path, mtime, frontmatter}` reflecting the post-write state.
        """
        p = _resolve(srv, path)
        if not p.is_file():
            raise FileNotFoundError(path)

        post = fm_lib.load(p)
        meta = dict(post.metadata or {})

        for k in ("created", "updated"):
            v = meta.get(k)
            if hasattr(v, "isoformat"):
                meta[k] = v.isoformat()[:10]

        for k, v in patch.items():
            if v is None:
                meta.pop(k, None)
            else:
                meta[k] = v

        meta["updated"] = date.today().isoformat()
        meta.setdefault("created", date.today().isoformat())

        fm_text = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).rstrip()
        new_content = f"---\n{fm_text}\n---\n{post.content}"
        mtime = srv.writer.write_atomic(p, new_content)
        srv.index.update(p)
        return {
            "path": _rel(srv, p),
            "mtime": mtime,
            "frontmatter": meta,
        }
