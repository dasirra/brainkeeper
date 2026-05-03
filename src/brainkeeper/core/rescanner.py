"""Periodic safety-net rescanner that walks the vault and reconciles Index."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from .index import Index

log = logging.getLogger(__name__)


class PeriodicRescanner:
    def __init__(self, vault_root: Path, index: Index, interval_seconds: int = 300) -> None:
        self.vault_root = Path(vault_root)
        self.index = index
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def rescan_once(self) -> None:
        on_disk: set[Path] = set()
        for f in self.vault_root.rglob("*.md"):
            parts = f.relative_to(self.vault_root).parts
            if any(p.startswith(".") or p == "_templates" for p in parts):
                continue
            on_disk.add(f)
            self.index.update(f)
        in_index = set(self.index.paths())
        for missing in in_index - on_disk:
            log.info("rescan: removing missing file from index: %s", missing)
            self.index.remove(missing)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.rescan_once()
            except Exception:
                log.exception("rescan iteration failed")
