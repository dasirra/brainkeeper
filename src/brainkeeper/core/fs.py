"""Atomic file writes with optional mtime check."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class StaleWriteError(Exception):
    """Raised when expected_mtime does not match the file's current mtime."""


class AtomicWriter:
    """tmp-file + os.replace for crash-safe writes."""

    def write_atomic(
        self,
        path: Path,
        content: str,
        expected_mtime: float | None = None,
    ) -> float:
        path = Path(path)
        if expected_mtime is not None and path.exists():
            actual = path.stat().st_mtime
            if abs(actual - expected_mtime) > 1e-6:
                raise StaleWriteError(
                    f"expected mtime {expected_mtime} but found {actual} for {path}"
                )

        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                fp.write(content)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        return path.stat().st_mtime
