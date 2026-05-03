"""brainkeeper CLI dispatcher."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from . import serve as _serve
from . import init as _init


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brainkeeper",
        description="brainkeeper vault tooling",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sp_serve = sub.add_parser("serve", help="Start the MCP server")
    sp_serve.add_argument(
        "--vault",
        type=Path,
        required=True,
        help="Path to vault root containing brainkeeper.yaml",
    )
    sp_serve.add_argument("-v", "--verbose", action="store_true")

    sp_init = sub.add_parser("init", help="Bootstrap a new vault")
    sp_init.add_argument(
        "path", type=Path, help="Path for the new vault root (created if absent)"
    )

    args = parser.parse_args(argv)

    if args.command == "serve":
        return _serve.run(args)
    if args.command == "init":
        return _init.run(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
