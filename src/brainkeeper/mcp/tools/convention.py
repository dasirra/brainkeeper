"""Layer 1: convention-aware tools that read brainkeeper.yaml."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import BrainkeeperServer


CANONICAL_KEYS = ("inbox", "journal", "projects", "areas", "brain", "archive")

_VAR_RE = re.compile(r"\{\{[^}]+\}\}")


def _find_template(srv: "BrainkeeperServer", name: str, layer: str | None) -> Path:
    candidates = [name, f"{name}.md"]
    layers = [layer] if layer else list(CANONICAL_KEYS)
    for lk in layers:
        layer_dir = srv.config.layer_path(lk)
        templates_dir = layer_dir / "_templates"
        if not templates_dir.is_dir():
            continue
        for cand in candidates:
            target = templates_dir / cand
            if target.is_file():
                return target
    raise FileNotFoundError(f"template '{name}' not found under any layer")


def register_convention(mcp: "FastMCP", srv: "BrainkeeperServer") -> None:

    @mcp.tool()
    def read_convention() -> dict[str, Any]:
        """Return the parsed brainkeeper.yaml as a dict."""
        path = srv.vault / "brainkeeper.yaml"
        return yaml.safe_load(path.read_text()) or {}

    @mcp.tool()
    def list_layers() -> list[dict[str, Any]]:
        """List the 6 canonical layers with their paths and options."""
        out = []
        for key in CANONICAL_KEYS:
            opts = getattr(srv.config.layers, key)
            options = {
                k: v
                for k, v in opts.model_dump().items()
                if k != "path" and v is not None
            }
            out.append({"key": key, "path": opts.path, "options": options})
        return out

    @mcp.tool()
    def get_template(name: str, layer: str | None = None) -> dict[str, Any]:
        """Locate a template. Searches `<layer>/_templates/` for the canonical layers."""
        path = _find_template(srv, name, layer)
        content = path.read_text(encoding="utf-8")
        variables = sorted(set(_VAR_RE.findall(content)))
        return {
            "name": path.name,
            "path": str(path.relative_to(srv.vault)),
            "content": content,
            "variables": variables,
        }

    @mcp.tool()
    def resolve_path(
        intent: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Resolve a capture intent to a target path + mode + optional anchor."""
        params = params or {}
        routing = srv.config.capture_routing
        target = routing.get(intent, routing["default"])
        target = target.replace("{today}", date.today().isoformat())
        anchor = None
        if "#" in target:
            target, anchor = target.split("#", 1)
        mode = "create" if target.endswith("/") else "append"
        return {"path": target, "mode": mode, "anchor": anchor}
