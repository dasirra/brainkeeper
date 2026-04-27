from pathlib import Path

from brainkeeper_mcp.index import Index, NoteMeta


def test_build_walks_vault(minimal_vault: Path):
    j = minimal_vault / "10 Journal" / "2026-04-27.md"
    j.write_text("---\ntype: journal\nstatus: active\ncreated: 2026-04-27\ntags: [topic/journal]\n---\nx")
    idx = Index(minimal_vault)
    idx.build()
    assert any(p.name == "2026-04-27.md" for p in idx.paths())


def test_get_returns_meta(minimal_vault: Path):
    j = minimal_vault / "10 Journal" / "2026-04-27.md"
    j.write_text("---\ntype: journal\nstatus: active\ncreated: 2026-04-27\ntags: [topic/journal]\n---\nx")
    idx = Index(minimal_vault)
    idx.build()
    meta = idx.get(j)
    assert isinstance(meta, NoteMeta)
    assert meta.frontmatter["type"] == "journal"


def test_query_by_tag(minimal_vault: Path):
    a = minimal_vault / "40 Brain" / "a.md"
    a.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n")
    b = minimal_vault / "40 Brain" / "b.md"
    b.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/y]\n---\n")
    idx = Index(minimal_vault)
    idx.build()
    hits = idx.by_tag("topic/x")
    assert len(hits) == 1
    assert hits[0].path == a


def test_query_by_status(minimal_vault: Path):
    a = minimal_vault / "20 Projects" / "a.md"
    a.write_text("---\ntype: project\nstatus: active\ncreated: 2026-04-27\ntags: [project/a]\n---\n")
    b = minimal_vault / "20 Projects" / "b.md"
    b.write_text("---\ntype: project\nstatus: completed\ncreated: 2026-04-27\ntags: [project/b]\n---\n")
    idx = Index(minimal_vault)
    idx.build()
    assert len(idx.by_status("active")) == 1
    assert len(idx.by_status("completed")) == 1


def test_orphans_are_notes_with_validation_errors(minimal_vault: Path):
    bad = minimal_vault / "00 Inbox" / "bad.md"
    bad.write_text("just text, no frontmatter")
    idx = Index(minimal_vault)
    idx.build()
    orphans = idx.orphans()
    assert any(o.path == bad for o in orphans)


def test_update_replaces_entry(minimal_vault: Path):
    n = minimal_vault / "40 Brain" / "n.md"
    n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n")
    idx = Index(minimal_vault)
    idx.build()
    n.write_text("---\ntype: knowledge\nstatus: archived\ncreated: 2026-04-27\ntags: [topic/x]\n---\n")
    idx.update(n)
    assert idx.get(n).frontmatter["status"] == "archived"


def test_remove_deletes_entry(minimal_vault: Path):
    n = minimal_vault / "40 Brain" / "n.md"
    n.write_text("---\ntype: knowledge\nstatus: active\ncreated: 2026-04-27\ntags: [topic/x]\n---\n")
    idx = Index(minimal_vault)
    idx.build()
    assert idx.get(n) is not None
    n.unlink()
    idx.remove(n)
    assert idx.get(n) is None
