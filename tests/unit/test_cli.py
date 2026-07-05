from pathlib import Path

from brainkeeper.cli import main

_LAYER_DIRS = [
    "00 Inbox",
    "10 Journal",
    "20 Projects",
    "30 Areas",
    "40 Brain",
    "90 Archive",
]


def test_init_creates_layers_and_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert main(["init"]) == 0
    vault = tmp_path / ".brainkeeper" / "vault"
    for layer in _LAYER_DIRS:
        assert (vault / layer).is_dir()
    assert (vault / "brainkeeper.yaml").exists()


def test_reinit_warns_and_preserves_config(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["init"])
    config_path = tmp_path / ".brainkeeper" / "vault" / "brainkeeper.yaml"
    config_path.write_text("# user edit\n")

    assert main(["init"]) == 0
    assert "already exists" in capsys.readouterr().err
    assert config_path.read_text() == "# user edit\n"


def test_serve_missing_vault_exits_1(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert main(["serve"]) == 1
    assert "brainkeeper init" in capsys.readouterr().err


def test_init_blocked_by_file_exits_1(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".brainkeeper").write_text("not a directory\n")
    assert main(["init"]) == 1
    assert "error" in capsys.readouterr().err
