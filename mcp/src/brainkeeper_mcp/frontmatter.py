"""YAML frontmatter parsing + validation against brainkeeper spec v0.1."""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any

import frontmatter

ALLOWED_TYPES: frozenset[str] = frozenset((
    "project", "area", "idea", "journal",
    "meeting", "note", "resource", "knowledge",
))
ALLOWED_STATUSES: frozenset[str] = frozenset((
    "active", "paused", "completed", "archived",
))
REQUIRED_FIELDS: tuple[str, ...] = ("type", "status", "created", "tags")
DATE_FIELDS: tuple[str, ...] = ("created", "deadline", "archived")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$")


class ValidationError(Exception):
    """Raised when frontmatter fails spec validation."""


class FrontmatterParser:
    """Thin wrapper over python-frontmatter with spec validation."""

    def parse(self, path: Path) -> tuple[dict[str, Any], str]:
        post = frontmatter.load(path)
        meta = dict(post.metadata or {})
        # PyYAML auto-coerces ISO dates into date/datetime objects.
        # Normalize known date fields back to YYYY-MM-DD strings so downstream
        # consumers and the spec-aligned validator see consistent string types.
        for field in DATE_FIELDS:
            v = meta.get(field)
            if isinstance(v, (_dt.date, _dt.datetime)):
                meta[field] = v.isoformat()[:10]
        return meta, post.content

    def validate(self, meta: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        for field in REQUIRED_FIELDS:
            value = meta.get(field)
            if value in (None, "", []):
                errors.append(f"required field `{field}` is missing or empty")

        t = meta.get("type")
        if t and str(t) not in ALLOWED_TYPES:
            errors.append(f"`type` value '{t}' not in allowed enum")

        s = meta.get("status")
        if s and str(s) not in ALLOWED_STATUSES:
            errors.append(f"`status` value '{s}' not in allowed enum")

        for field in DATE_FIELDS:
            v = meta.get(field)
            if v in (None, "", False):
                continue
            if not _DATE_RE.match(str(v)):
                errors.append(f"`{field}` value '{v}' is not YYYY-MM-DD")

        tags = meta.get("tags")
        if isinstance(tags, list):
            for t in tags:
                if not isinstance(t, str) or not _TAG_RE.match(t.lstrip("#")):
                    errors.append(f"tag '{t}' fails grammar")

        return errors
