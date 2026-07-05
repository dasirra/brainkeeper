"""brainkeeper CLI dispatcher."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from . import serve as _serve
from . import init as _init


def vault_path() -> Path:
    """Fixed vault location: the single source of truth."""
    return Path.home() / ".brainkeeper" / "vault"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brainkeeper",
        description="brainkeeper vault tooling",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sp_serve = sub.add_parser("serve", help="Start the MCP server")
    sp_serve.add_argument("-v", "--verbose", action="store_true")

    sub.add_parser("init", help="Bootstrap the vault at ~/.brainkeeper/vault")

    args = parser.parse_args(argv)
    args.vault = vault_path()

    if args.command == "serve":
        return _serve.run(args)
    if args.command == "init":
        return _init.run(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
