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
    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"error: vault path is not a directory: {vault}", file=sys.stderr)
        return 1
    srv = BrainkeeperServer(vault)
    srv.run_stdio()
    return 0
