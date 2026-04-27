"""In-memory index of vault notes with frontmatter metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from .frontmatter import FrontmatterParser


@dataclass
class NoteMeta:
    path: Path
    frontmatter: dict[str, Any]
    mtime: float
    validation_errors: list[str]


class Index:
    """Thread-safe dict[Path, NoteMeta] with simple queries."""

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = Path(vault_root)
        self._lock = RLock()
        self._notes: dict[Path, NoteMeta] = {}
        self._parser = FrontmatterParser()

    def build(self) -> None:
        with self._lock:
            self._notes.clear()
            for f in self.vault_root.rglob("*.md"):
                if any(p.startswith(".") for p in f.relative_to(self.vault_root).parts):
                    continue
                self._index_file(f)

    def update(self, path: Path) -> None:
        path = Path(path)
        with self._lock:
            if not path.exists():
                self._notes.pop(path, None)
                return
            self._index_file(path)

    def remove(self, path: Path) -> None:
        with self._lock:
            self._notes.pop(Path(path), None)

    def get(self, path: Path) -> NoteMeta | None:
        with self._lock:
            return self._notes.get(Path(path))

    def paths(self) -> list[Path]:
        with self._lock:
            return list(self._notes.keys())

    def by_tag(self, tag: str) -> list[NoteMeta]:
        with self._lock:
            return [
                m for m in self._notes.values()
                if isinstance(m.frontmatter.get("tags"), list)
                and tag in m.frontmatter["tags"]
            ]

    def by_status(self, status: str) -> list[NoteMeta]:
        with self._lock:
            return [
                m for m in self._notes.values()
                if str(m.frontmatter.get("status")) == status
            ]

    def by_type(self, type_value: str) -> list[NoteMeta]:
        with self._lock:
            return [
                m for m in self._notes.values()
                if str(m.frontmatter.get("type")) == type_value
            ]

    def orphans(self) -> list[NoteMeta]:
        """Notes with any validation error against the spec."""
        with self._lock:
            return [m for m in self._notes.values() if m.validation_errors]

    def _index_file(self, path: Path) -> None:
        try:
            meta, _ = self._parser.parse(path)
        except Exception:
            meta = {}
        errors = self._parser.validate(meta)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return
        self._notes[path] = NoteMeta(
            path=path, frontmatter=meta, mtime=mtime, validation_errors=errors,
        )
