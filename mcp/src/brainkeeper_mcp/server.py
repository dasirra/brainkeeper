"""FastMCP server wiring + tool registration."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from .config import Config, ConfigLoader
from .fs import AtomicWriter
from .index import Index
from .rescanner import PeriodicRescanner
from .watcher import FileWatcher


class BrainkeeperServer:
    """Holds infrastructure + the FastMCP instance with tools registered."""

    def __init__(self, vault: Path) -> None:
        self.vault = Path(vault)
        self.config: Config = ConfigLoader(self.vault).load()
        self.index = Index(self.vault)
        self.writer = AtomicWriter()
        self.watcher = FileWatcher(self.vault, self.index)
        self.rescanner = PeriodicRescanner(self.vault, self.index)
        self.mcp = FastMCP("brainkeeper")
        from .tools.primitives import register_primitives
        register_primitives(self.mcp, self)
        # Convention tools registered in Task 11+

    def start_infrastructure(self) -> None:
        self.index.build()
        self.watcher.start()
        self.rescanner.start()

    def stop_infrastructure(self) -> None:
        self.rescanner.stop()
        self.watcher.stop()

    def run_stdio(self) -> None:
        self.start_infrastructure()
        try:
            self.mcp.run()
        finally:
            self.stop_infrastructure()
