"""vault init subcommand."""

from __future__ import annotations
import importlib.resources
import sys
from pathlib import Path

_LAYER_DIRS = [
    "00 Inbox",
    "10 Journal",
    "20 Projects",
    "30 Areas",
    "40 Brain",
    "90 Archive",
]


def _find_minimal_yaml() -> Path:
    via_package = Path(
        str(importlib.resources.files("brainkeeper.spec") / "examples" / "minimal.yaml")
    )
    if via_package.exists():
        return via_package
    # Dev fallback
    dev_path = (
        Path(__file__).resolve().parents[3] / "spec" / "examples" / "minimal.yaml"
    )
    if dev_path.exists():
        return dev_path
    raise FileNotFoundError("minimal.yaml not found. Run `pip install -e .` first.")


def run(args) -> int:
    vault = args.path.expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)

    for layer in _LAYER_DIRS:
        (vault / layer).mkdir(exist_ok=True)

    config_path = vault / "brainkeeper.yaml"
    if config_path.exists():
        print(
            f"warning: {config_path} already exists - skipping. "
            "Edit it manually to change your vault configuration.",
            file=sys.stderr,
        )
    else:
        minimal = _find_minimal_yaml()
        config_path.write_text(minimal.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"created vault at {vault}")

    return 0
