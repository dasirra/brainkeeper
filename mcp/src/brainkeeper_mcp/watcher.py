"""Filesystem watcher pushing updates into Index, debounced."""

from __future__ import annotations

import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .index import Index


class _Handler(FileSystemEventHandler):
    def __init__(self, vault_root: Path, index: Index, debounce_ms: int) -> None:
        self.vault_root = vault_root
        self.index = index
        self.debounce = debounce_ms / 1000.0
        self._timers: dict[Path, threading.Timer] = {}
        self._lock = threading.Lock()

    def _schedule(self, path: Path, deleted: bool) -> None:
        if path.suffix != ".md":
            return
        try:
            rel = path.relative_to(self.vault_root)
        except ValueError:
            return
        if any(p.startswith(".") for p in rel.parts):
            return

        def _fire():
            with self._lock:
                self._timers.pop(path, None)
            if deleted:
                self.index.remove(path)
            else:
                self.index.update(path)

        with self._lock:
            t = self._timers.get(path)
            if t:
                t.cancel()
            timer = threading.Timer(self.debounce, _fire)
            timer.daemon = True
            self._timers[path] = timer
            timer.start()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.src_path), deleted=False)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.src_path), deleted=False)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.src_path), deleted=True)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.src_path), deleted=True)
        self._schedule(Path(event.dest_path), deleted=False)


class FileWatcher:
    def __init__(self, vault_root: Path, index: Index, debounce_ms: int = 200) -> None:
        self.vault_root = Path(vault_root)
        self.index = index
        self.debounce_ms = debounce_ms
        self._observer = Observer()
        self._handler = _Handler(self.vault_root, index, debounce_ms)

    def start(self) -> None:
        self._observer.schedule(self._handler, str(self.vault_root), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=5)
