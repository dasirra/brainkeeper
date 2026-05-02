from pathlib import Path

import pytest

from brainkeeper_mcp.server import BrainkeeperServer


@pytest.fixture
def srv(minimal_vault: Path) -> BrainkeeperServer:
    s = BrainkeeperServer(minimal_vault)
    s.index.build()
    return s


def _call(srv: BrainkeeperServer, tool_name: str, **kwargs):
    components = srv.mcp._local_provider._components
    tool = next(t for k, t in components.items() if k.startswith("tool:") and t.name == tool_name)
    return tool.fn(**kwargs)


def _make(vault: Path, rel: str, tags: list[str], extra: str = "") -> Path:
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    fm = "\n".join(f"  - {t}" for t in tags)
    body = (
        "---\n"
        "created: 2026-04-27\n"
        "updated: 2026-04-27\n"
        "tags:\n"
        f"{fm}\n"
        f"{extra}"
        "---\n"
        "body"
    )
    p.write_text(body, encoding="utf-8")
    return p


# ---------- find_by_tag ----------


def test_find_by_tag_exact_match(srv, minimal_vault):
    a = _make(minimal_vault, "40 Brain/a.md", ["topic/mcp", "domain/fitizens"])
    b = _make(minimal_vault, "40 Brain/b.md", ["topic/rag"])
    srv.index.update(a); srv.index.update(b)
    out = _call(srv, "find_by_tag", tag="topic/mcp", prefix_match=False)
    paths = {item["path"] for item in out}
    assert paths == {"40 Brain/a.md"}


def test_find_by_tag_prefix_dimension_query(srv, minimal_vault):
    """`topic/` should match every topic-prefixed tag."""
    a = _make(minimal_vault, "40 Brain/a.md", ["topic/mcp"])
    b = _make(minimal_vault, "40 Brain/b.md", ["topic/rag"])
    c = _make(minimal_vault, "40 Brain/c.md", ["domain/x"])
    srv.index.update(a); srv.index.update(b); srv.index.update(c)
    out = _call(srv, "find_by_tag", tag="topic/")
    paths = {item["path"] for item in out}
    assert paths == {"40 Brain/a.md", "40 Brain/b.md"}


def test_find_by_tag_strips_hash_prefix(srv, minimal_vault):
    a = _make(minimal_vault, "40 Brain/a.md", ["topic/mcp"])
    srv.index.update(a)
    out = _call(srv, "find_by_tag", tag="#topic/mcp", prefix_match=False)
    assert len(out) == 1


def test_find_by_tag_returns_frontmatter(srv, minimal_vault):
    a = _make(minimal_vault, "40 Brain/a.md", ["topic/mcp"])
    srv.index.update(a)
    out = _call(srv, "find_by_tag", tag="topic/mcp", prefix_match=False)
    assert out[0]["frontmatter"]["tags"] == ["topic/mcp"]
    assert "mtime" in out[0]


def test_find_by_tag_empty_when_no_match(srv, minimal_vault):
    a = _make(minimal_vault, "40 Brain/a.md", ["topic/mcp"])
    srv.index.update(a)
    out = _call(srv, "find_by_tag", tag="domain/none")
    assert out == []


# ---------- find_orphans ----------


def test_find_orphans_returns_validation_errors(srv, minimal_vault):
    """A note missing `updated` is an orphan under spec v0.1.3."""
    p = minimal_vault / "40 Brain" / "broken.md"
    p.write_text("---\ncreated: 2026-04-27\ntags: [t/x]\n---\nbody")
    srv.index.update(p)
    out = _call(srv, "find_orphans")
    matched = [o for o in out if o["path"] == "40 Brain/broken.md"]
    assert matched, "broken note should appear as orphan"
    assert any("updated" in e for e in matched[0]["errors"])


def test_find_orphans_skips_compliant_notes(srv, minimal_vault):
    """Fully compliant notes do NOT appear in orphans."""
    a = _make(minimal_vault, "40 Brain/ok.md", ["topic/x"])
    srv.index.update(a)
    out = _call(srv, "find_orphans")
    paths = {o["path"] for o in out}
    assert "40 Brain/ok.md" not in paths


def test_find_orphans_returns_empty_for_empty_vault(srv):
    """No managed notes — no orphans."""
    out = _call(srv, "find_orphans")
    assert out == []


# ---------- validate_frontmatter ----------


def test_validate_frontmatter_passes_for_compliant(srv, minimal_vault):
    a = _make(minimal_vault, "40 Brain/ok.md", ["topic/x"])
    srv.index.update(a)
    out = _call(srv, "validate_frontmatter", path="40 Brain/ok.md")
    assert out["valid"] is True
    assert out["errors"] == []


def test_validate_frontmatter_flags_missing_updated(srv, minimal_vault):
    p = minimal_vault / "40 Brain" / "broken.md"
    p.write_text("---\ncreated: 2026-04-27\ntags: [t/x]\n---\nbody")
    srv.index.update(p)
    out = _call(srv, "validate_frontmatter", path="40 Brain/broken.md")
    assert out["valid"] is False
    assert any("updated" in e for e in out["errors"])


def test_validate_frontmatter_flags_updated_before_created(srv, minimal_vault):
    p = minimal_vault / "40 Brain" / "back.md"
    p.write_text("---\ncreated: 2026-05-01\nupdated: 2026-04-01\ntags: [t/x]\n---\nbody")
    srv.index.update(p)
    out = _call(srv, "validate_frontmatter", path="40 Brain/back.md")
    assert out["valid"] is False
    assert any("earlier" in e for e in out["errors"])


def test_validate_frontmatter_missing_file_raises(srv):
    with pytest.raises(FileNotFoundError):
        _call(srv, "validate_frontmatter", path="40 Brain/nope.md")


def test_validate_frontmatter_works_on_unindexed_file(srv, minimal_vault):
    """Tool re-reads from disk, so it should validate even files the index hasn't seen."""
    a = _make(minimal_vault, "40 Brain/fresh.md", ["topic/x"])
    # Deliberately do NOT call srv.index.update(a)
    out = _call(srv, "validate_frontmatter", path="40 Brain/fresh.md")
    assert out["valid"] is True
