"""CLI entry point: `brainkeeper-mcp --vault <path>`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .server import BrainkeeperServer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brainkeeper-mcp")
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Path to the vault root containing brainkeeper.yaml",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging",
    )
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    sys.exit(main())
