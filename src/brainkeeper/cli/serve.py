"""MCP serve subcommand."""

from __future__ import annotations
import logging
import sys

from ..mcp.server import BrainkeeperServer


def run(args) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    vault = args.vault
    if not vault.is_dir():
        print(
            f"error: no vault at {vault}. Run `brainkeeper init` to create it.",
            file=sys.stderr,
        )
        return 1
    srv = BrainkeeperServer(vault)
    srv.run_stdio()
    return 0
