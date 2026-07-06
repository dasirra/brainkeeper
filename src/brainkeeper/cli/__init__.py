"""brainkeeper CLI dispatcher."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from . import serve as _serve
from . import init as _init
from . import stats as _stats


def vault_path() -> Path:
    """Fixed vault location: the single source of truth."""
    # resolve() keeps the watcher/index path keys canonical under symlinked homes
    return (Path.home() / ".brainkeeper" / "vault").resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brainkeeper",
        description="brainkeeper vault tooling",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sp_serve = sub.add_parser("serve", help="Start the MCP server")
    sp_serve.add_argument("-v", "--verbose", action="store_true")

    sub.add_parser("init", help="Bootstrap the vault at ~/.brainkeeper/vault")

    sp_stats = sub.add_parser(
        "stats",
        help="Show vault progress, health, and structure summary",
        description=(
            "Show vault progress, health, and structure summary. "
            "Day-based metrics (7/30-day windows, journal streak, inbox age) "
            "use local calendar days."
        ),
    )
    sp_stats.add_argument(
        "--json", action="store_true", help="Emit full stats as JSON instead of text"
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    args.vault = vault_path()
    if args.command == "serve":
        return _serve.run(args)
    if args.command == "stats":
        return _stats.run(args)
    return _init.run(args)


if __name__ == "__main__":
    sys.exit(main())
