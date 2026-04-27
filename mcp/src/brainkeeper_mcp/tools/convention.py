"""Layer 1: convention-aware tools that read brainkeeper.yaml."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import BrainkeeperServer


CANONICAL_KEYS = ("inbox", "journal", "projects", "areas", "brain", "archive")


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
                k: v for k, v in opts.model_dump().items()
                if k != "path" and v is not None
            }
            out.append({"key": key, "path": opts.path, "options": options})
        return out
