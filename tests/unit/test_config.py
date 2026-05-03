from pathlib import Path

import pytest

from brainkeeper.core.config import Config, ConfigLoader


def test_load_minimal(tmp_path: Path):
    yaml = tmp_path / "brainkeeper.yaml"
    yaml.write_text("""
layers:
  inbox: "00 Inbox"
  journal:
    path: "10 Journal"
    format: "YYYY-MM-DD.md"
  projects: "20 Projects"
  areas: "30 Areas"
  brain: "40 Brain"
  archive: "90 Archive"
capture_routing:
  default: "00 Inbox/"
""")
    cfg = ConfigLoader(tmp_path).load()
    assert isinstance(cfg, Config)
    assert cfg.layers.inbox.path == "00 Inbox"
    assert cfg.layers.journal.path == "10 Journal"
    assert cfg.layers.journal.format == "YYYY-MM-DD.md"
    assert cfg.capture_routing["default"] == "00 Inbox/"


def test_missing_layers_rejected(tmp_path: Path):
    (tmp_path / "brainkeeper.yaml").write_text("""
layers:
  inbox: "00 Inbox"
capture_routing:
  default: "00 Inbox/"
""")
    with pytest.raises(ValueError):
        ConfigLoader(tmp_path).load()


def test_missing_capture_routing_default_rejected(tmp_path: Path):
    (tmp_path / "brainkeeper.yaml").write_text("""
layers:
  inbox: "00 Inbox"
  journal: "10 Journal"
  projects: "20 Projects"
  areas: "30 Areas"
  brain: "40 Brain"
  archive: "90 Archive"
capture_routing:
  idea: "x"
""")
    with pytest.raises(ValueError):
        ConfigLoader(tmp_path).load()


def test_no_config_file_rejected(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        ConfigLoader(tmp_path).load()


def test_layer_path_resolves(tmp_path: Path, minimal_vault: Path):
    cfg = ConfigLoader(minimal_vault).load()
    assert cfg.layer_path("inbox").name == "00 Inbox"
    assert cfg.layer_path("journal").name == "10 Journal"
    assert cfg.layer_path("archive").name == "90 Archive"
