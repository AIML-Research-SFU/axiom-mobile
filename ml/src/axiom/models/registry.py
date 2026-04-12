"""Config loading and model instantiation registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .question_lookup import QuestionLookupBaseline
from .specs import ModelSpec


def _default_config_dir() -> Path:
    # registry.py -> models -> axiom -> src -> ml -> repo_root
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "ml" / "configs" / "models"


def load_model_specs(config_dir: str | Path | None = None) -> dict[str, ModelSpec]:
    config_root = Path(config_dir).resolve() if config_dir is not None else _default_config_dir()
    specs: dict[str, ModelSpec] = {}

    for path in sorted(config_root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        spec = ModelSpec.from_dict(payload)
        specs[spec.model_id] = spec

    if not specs:
        raise FileNotFoundError(f"No model config files found in {config_root}")
    return specs


def resolve_model_spec(
    model_id: str,
    config_dir: str | Path | None = None,
) -> ModelSpec:
    specs = load_model_specs(config_dir=config_dir)
    if model_id not in specs:
        raise KeyError(f"Unknown model_id '{model_id}'. Available: {sorted(specs)}")
    return specs[model_id]


def instantiate_model(
    model_id: str,
    config_dir: str | Path | None = None,
    **kwargs: Any,
):
    spec = resolve_model_spec(model_id, config_dir=config_dir)

    if spec.backend == "heuristic" and spec.model_id == "question_lookup_v0":
        return QuestionLookupBaseline(spec)

    if spec.backend == "pytorch" and spec.model_id == "tiny_multimodal_v0":
        from .tiny_multimodal import TinyMultimodalBaseline
        return TinyMultimodalBaseline(spec, **kwargs)

    raise NotImplementedError(
        f"Model '{model_id}' is configured but not executable yet "
        f"(backend={spec.backend}, stage={spec.stage})."
    )
