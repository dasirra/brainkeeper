from pathlib import Path


from brainkeeper.core.frontmatter import (
    FrontmatterParser,
    REQUIRED_FIELDS,
    DATE_FIELDS,
)


def _write(p: Path, body: str) -> Path:
    p.write_text(body)
    return p


def test_parse_minimal(tmp_path: Path):
    f = _write(
        tmp_path / "n.md",
        "---\ncreated: 2026-04-27\nupdated: 2026-04-27\ntags: [topic/x]\n---\nbody",
    )
    meta, content = FrontmatterParser().parse(f)
    assert meta["created"] == "2026-04-27"
    assert meta["updated"] == "2026-04-27"
    assert meta["tags"] == ["topic/x"]
    assert content.strip() == "body"


def test_parse_no_frontmatter(tmp_path: Path):
    f = _write(tmp_path / "n.md", "just body, no fm")
    meta, content = FrontmatterParser().parse(f)
    assert meta == {}
    assert content == "just body, no fm"


def test_parse_extension_field_passes_through(tmp_path: Path):
    """User-defined fields are kept verbatim per the extension rule (§6)."""
    f = _write(
        tmp_path / "n.md",
        "---\ncreated: 2026-04-27\nupdated: 2026-04-27\ntags: [topic/x]\n"
        "lesson: L01\nmodule: 1\n---\nbody",
    )
    meta, _ = FrontmatterParser().parse(f)
    assert meta["lesson"] == "L01"
    assert meta["module"] == 1


def test_validate_required_fields_missing(tmp_path: Path):
    f = _write(tmp_path / "n.md", "---\ntags: [topic/x]\n---\nbody")
    parser = FrontmatterParser()
    meta, _ = parser.parse(f)
    errors = parser.validate(meta)
    assert any("created" in e for e in errors)
    assert any("updated" in e for e in errors)
    # `tags` was provided, so it should not be flagged
    assert not any("`tags` is missing" in e for e in errors)


def test_validate_no_type_required():
    """Spec v0.1.3 dropped `type` — its absence MUST NOT raise an error."""
    parser = FrontmatterParser()
    errors = parser.validate(
        {
            "created": "2026-04-27",
            "updated": "2026-04-27",
            "tags": ["t/x"],
        }
    )
    assert errors == []


def test_validate_no_status_required():
    """Spec v0.1.3 dropped `status` — its absence MUST NOT raise an error."""
    parser = FrontmatterParser()
    errors = parser.validate(
        {
            "created": "2026-04-27",
            "updated": "2026-04-27",
            "tags": ["t/x"],
        }
    )
    assert errors == []


def test_validate_extension_field_ignored():
    """A user field like `status: complete` (non-spec value) MUST NOT raise."""
    parser = FrontmatterParser()
    errors = parser.validate(
        {
            "created": "2026-04-27",
            "updated": "2026-04-27",
            "tags": ["t/x"],
            "status": "complete",  # extension field, value not in any spec enum
            "type": "lesson",  # extension field, value not in any spec enum
        }
    )
    assert errors == []


def test_validate_bad_date_format():
    parser = FrontmatterParser()
    errors = parser.validate(
        {
            "created": "April 27 2026",
            "updated": "2026-04-27",
            "tags": ["t/x"],
        }
    )
    assert any("created" in e for e in errors)


def test_validate_updated_before_created():
    """`updated` MUST be ≥ `created` per §6."""
    parser = FrontmatterParser()
    errors = parser.validate(
        {
            "created": "2026-04-27",
            "updated": "2026-04-26",
            "tags": ["t/x"],
        }
    )
    assert any("updated" in e and "earlier" in e for e in errors)


def test_validate_updated_equal_to_created_ok():
    """`updated == created` is allowed (newly written, never edited)."""
    parser = FrontmatterParser()
    errors = parser.validate(
        {
            "created": "2026-04-27",
            "updated": "2026-04-27",
            "tags": ["t/x"],
        }
    )
    assert errors == []


def test_validate_tag_grammar():
    parser = FrontmatterParser()
    errors = parser.validate(
        {
            "created": "2026-04-27",
            "updated": "2026-04-27",
            "tags": ["topic/MCP", "good-tag", "bad_tag"],
        }
    )
    # 2 violations: uppercase MCP, snake_case bad_tag
    assert sum(1 for e in errors if "tag" in e) == 2


def test_required_fields_constant_matches_spec():
    """Sanity-check the public REQUIRED_FIELDS export."""
    assert REQUIRED_FIELDS == ("created", "updated", "tags")
    assert "created" in DATE_FIELDS
    assert "updated" in DATE_FIELDS
