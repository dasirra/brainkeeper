from pathlib import Path

import pytest

from brainkeeper_mcp.frontmatter import (
    FrontmatterParser, ValidationError, ALLOWED_TYPES, ALLOWED_STATUSES,
)


def _write(p: Path, body: str) -> Path:
    p.write_text(body)
    return p


def test_parse_minimal(tmp_path: Path):
    f = _write(tmp_path / "n.md", "---\ntype: note\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\nbody")
    meta, content = FrontmatterParser().parse(f)
    assert meta["type"] == "note"
    assert meta["status"] == "active"
    assert meta["created"] == "2026-04-27"
    assert meta["tags"] == ["topic/x"]
    assert content.strip() == "body"


def test_parse_no_frontmatter(tmp_path: Path):
    f = _write(tmp_path / "n.md", "just body, no fm")
    meta, content = FrontmatterParser().parse(f)
    assert meta == {}
    assert content == "just body, no fm"


def test_validate_required_fields_missing(tmp_path: Path):
    f = _write(tmp_path / "n.md", "---\ntype: note\n---\nbody")
    parser = FrontmatterParser()
    meta, _ = parser.parse(f)
    errors = parser.validate(meta)
    assert any("status" in e for e in errors)
    assert any("created" in e for e in errors)
    assert any("tags" in e for e in errors)


def test_validate_unknown_type(tmp_path: Path):
    parser = FrontmatterParser()
    errors = parser.validate({
        "type": "playbook", "status": "active", "created": "2026-04-27", "tags": ["t/x"],
    })
    assert any("type" in e and "playbook" in e for e in errors)


def test_validate_unknown_status(tmp_path: Path):
    parser = FrontmatterParser()
    errors = parser.validate({
        "type": "note", "status": "draft", "created": "2026-04-27", "tags": ["t/x"],
    })
    assert any("status" in e for e in errors)


def test_validate_bad_date_format(tmp_path: Path):
    parser = FrontmatterParser()
    errors = parser.validate({
        "type": "note", "status": "active", "created": "April 27 2026", "tags": ["t/x"],
    })
    assert any("created" in e for e in errors)


def test_validate_tag_grammar(tmp_path: Path):
    parser = FrontmatterParser()
    errors = parser.validate({
        "type": "note", "status": "active", "created": "2026-04-27",
        "tags": ["topic/MCP", "good-tag", "bad_tag"],
    })
    # 2 violations: uppercase MCP, snake_case bad_tag
    assert sum(1 for e in errors if "tag" in e) == 2


def test_allowed_constants_match_spec():
    assert "project" in ALLOWED_TYPES
    assert "knowledge" in ALLOWED_TYPES
    assert "active" in ALLOWED_STATUSES
    assert "archived" in ALLOWED_STATUSES
