"""Load and validate brainkeeper.yaml against the JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field

# Locate the canonical schema by walking up from this file:
# mcp/src/brainkeeper_mcp/config.py -> repo root -> spec/schema/brainkeeper.schema.json
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "spec" / "schema" / "brainkeeper.schema.json"
)


class LayerOptions(BaseModel):
    path: str
    format: str | None = None
    status_field: str | None = None
    active_values: list[str] | None = None
    year_subfolder: bool | None = None


def _coerce_layer(value: Any) -> LayerOptions:
    if isinstance(value, str):
        return LayerOptions(path=value)
    if isinstance(value, dict):
        return LayerOptions(**value)
    raise ValueError(f"layer entry must be str or dict: {value!r}")


class Layers(BaseModel):
    inbox: LayerOptions
    journal: LayerOptions
    projects: LayerOptions
    areas: LayerOptions
    brain: LayerOptions
    archive: LayerOptions

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "Layers":
        return cls(**{k: _coerce_layer(v) for k, v in raw.items()})


class Config(BaseModel):
    layers: Layers
    capture_routing: dict[str, str]
    vault_root: Path = Field(exclude=True)

    def layer_path(self, key: str) -> Path:
        opts: LayerOptions = getattr(self.layers, key)
        return self.vault_root / opts.path


class ConfigLoader:
    """Loads brainkeeper.yaml from a vault root and validates against schema."""

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = Path(vault_root)
        self._validator = Draft202012Validator(
            json.loads(_SCHEMA_PATH.read_text())
        )

    def load(self) -> Config:
        path = self.vault_root / "brainkeeper.yaml"
        if not path.exists():
            raise FileNotFoundError(f"no brainkeeper.yaml at {self.vault_root}")
        raw = yaml.safe_load(path.read_text()) or {}
        errors = sorted(self._validator.iter_errors(raw), key=lambda e: e.path)
        if errors:
            msg = "; ".join(e.message for e in errors)
            raise ValueError(f"brainkeeper.yaml fails schema: {msg}")
        return Config(
            layers=Layers.from_raw(raw["layers"]),
            capture_routing=raw["capture_routing"],
            vault_root=self.vault_root,
        )
