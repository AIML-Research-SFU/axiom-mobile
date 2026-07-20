#!/usr/bin/env python3
"""Export a trained AxiomLora checkpoint to Core ML (.mlpackage).

Same pipeline as ml/scripts/export_coreml.py (Phase 4), pointed at the
axiom_lora architecture instead of tiny_multimodal:
  1. Loads a trained checkpoint (model.pt + label_vocab.json + architecture.json)
  2. Traces the PyTorch model with torch.jit.trace
  3. Converts to Core ML via coremltools
  4. Runs a post-conversion accuracy gate on val/test splits
  5. Writes all artifacts and a conversion report to the output directory

A separate script rather than generalizing export_coreml.py, matching this
repo's existing convention of one specific script per model family (see
run_baseline.py vs run_trainable_baseline.py) rather than a shared dispatch
layer.

Usage:
    python3 ml/scripts/export_coreml_lora.py \\
        --checkpoint-dir results/trainable_baselines/axiom_lora_v1_seed0_local/checkpoint \\
        --image-root ~/Datasets/axiom-mobile/local_phase8_images \\
        --manifest-dir ~/Datasets/axiom-mobile/local_phase8_manifests
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from axiom.data.images import IMAGE_SIZE, ImageLoader, resolve_image_root  # noqa: E402
from axiom.eval import compute_exact_match_metrics  # noqa: E402
from axiom.models.axiom_lora import AxiomLoraBaseline  # noqa: E402
from axiom.models.tiny_multimodal import MAX_CHAR_LEN, encode_question  # noqa: E402
from axiom.models.specs import ModelSpec  # noqa: E402
from axiom.results import write_json  # noqa: E402

ACCURACY_GATE_MAX_DROP = 0.03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-dir", required=True)
    parser.add_argument("--image-root", default=None)
    parser.add_argument("--manifest-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--model-id", default="axiom_lora_v1")
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def _load_splits(manifest_dir: Path | None, repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    if manifest_dir is not None:
        splits: dict[str, list[dict[str, Any]]] = {}
        for split_name in ("pool", "val", "test"):
            path = manifest_dir / f"{split_name}.jsonl"
            if not path.exists():
                raise FileNotFoundError(f"Missing manifest: {path}")
            rows = []
            for line in path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    rows.append(json.loads(line))
            splits[split_name] = rows
        return splits

    from axiom.data import load_all_splits  # noqa: E402
    return load_all_splits(repo_root=repo_root, validate=True)


def _coreml_predictions(
    mlmodel_path: Path,
    rows: list[dict[str, Any]],
    image_loader: ImageLoader,
    idx_to_label: dict[int, str],
) -> list[str]:
    import coremltools as ct
    from PIL import Image

    mlmodel = ct.models.MLModel(str(mlmodel_path))
    predictions: list[str] = []

    for row in rows:
        img_path = image_loader.resolve_path(row["image_filename"])
        pil_img = Image.open(img_path).convert("RGB").resize(
            (IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR
        )
        char_ids = np.array([encode_question(row["question"])], dtype=np.int32)
        output = mlmodel.predict({"image": pil_img, "char_ids": char_ids})
        logits = output["logits"]
        pred_idx = int(np.argmax(logits))
        predictions.append(idx_to_label.get(pred_idx, ""))

    return predictions


def _evaluate_accuracy_gate(
    pytorch_metrics: dict[str, float], coreml_metrics: dict[str, float], split_name: str
) -> dict[str, Any]:
    pt_em = pytorch_metrics["exact_match"]
    cm_em = coreml_metrics["exact_match"]
    drop = pt_em - cm_em
    passed = drop <= ACCURACY_GATE_MAX_DROP
    return {
        "split": split_name,
        "pytorch_exact_match": round(pt_em, 4),
        "coreml_exact_match": round(cm_em, 4),
        "accuracy_drop": round(drop, 4),
        "max_allowed_drop": ACCURACY_GATE_MAX_DROP,
        "gate_passed": passed,
    }


def main() -> int:
    args = parse_args()
    checkpoint_dir = Path(args.checkpoint_dir).resolve()
    repo_root = ROOT.resolve()

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else repo_root / "results" / "coreml_exports" / f"{args.model_id}_seed{args.seed}"
    )

    image_root = resolve_image_root(args.image_root)
    print(f"Image root: {image_root}")
    print(f"Checkpoint: {checkpoint_dir}")

    manifest_dir = Path(args.manifest_dir).resolve() if args.manifest_dir else None
    splits = _load_splits(manifest_dir, repo_root)
    print(f"Splits: pool={len(splits['pool'])}, val={len(splits['val'])}, test={len(splits['test'])}")

    print("\nLoading PyTorch checkpoint...")
    spec_dict = json.loads(
        (ROOT / "ml" / "configs" / "models" / f"{args.model_id}.json").read_text()
    )
    spec = ModelSpec.from_dict(spec_dict)
    model = AxiomLoraBaseline.load_checkpoint(checkpoint_dir, spec, image_root=image_root)
    print("  Checkpoint loaded successfully.")

    print("\nRunning PyTorch inference...")
    pytorch_results: dict[str, dict[str, Any]] = {}
    for split_name in ("val", "test"):
        preds = model.predict_many(splits[split_name])
        metrics = compute_exact_match_metrics(splits[split_name], preds)
        pytorch_results[split_name] = metrics
        print(f"  PyTorch {split_name}: EM={metrics['exact_match']:.4f} "
              f"({metrics['num_correct']}/{metrics['num_examples']})")

    print("\nExporting to Core ML...")
    export_info = model.export_coreml(output_dir)
    mlpackage_path = Path(export_info["mlpackage"])
    print(f"  .mlpackage saved: {mlpackage_path}")

    print("\nRunning Core ML inference...")
    loader = ImageLoader(image_root)
    idx_to_label = {int(i): a for a, i in model._label_to_idx.items()}

    coreml_results: dict[str, dict[str, Any]] = {}
    gate_results: list[dict[str, Any]] = []

    for split_name in ("val", "test"):
        preds = _coreml_predictions(mlpackage_path, splits[split_name], loader, idx_to_label)
        metrics = compute_exact_match_metrics(splits[split_name], preds)
        coreml_results[split_name] = metrics
        print(f"  Core ML {split_name}: EM={metrics['exact_match']:.4f} "
              f"({metrics['num_correct']}/{metrics['num_examples']})")

        gate = _evaluate_accuracy_gate(pytorch_results[split_name], metrics, split_name)
        gate_results.append(gate)
        status = "PASS" if gate["gate_passed"] else "FAIL"
        print(f"  Gate {split_name}: {status} (drop={gate['accuracy_drop']:.4f}, "
              f"max={ACCURACY_GATE_MAX_DROP})")

    all_passed = all(g["gate_passed"] for g in gate_results)
    overall_status = "passed" if all_passed else "failed"

    import os

    def _dir_size_mb(path: Path) -> float:
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                total += os.path.getsize(os.path.join(dirpath, f))
        return total / 1024 / 1024

    report = {
        "run_id": f"coreml_export_{args.model_id}_seed{args.seed}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": args.model_id,
        "checkpoint_dir": str(checkpoint_dir),
        "image_root": str(image_root),
        "export": export_info,
        "mlpackage_size_mb": round(_dir_size_mb(mlpackage_path), 2),
        "pytorch_metrics": pytorch_results,
        "coreml_metrics": coreml_results,
        "accuracy_gate": {
            "max_allowed_drop": ACCURACY_GATE_MAX_DROP,
            "overall_status": overall_status,
            "per_split": gate_results,
        },
        "notes": (
            f"Core ML export of {args.model_id} (pretrained MobileNetV3-Small "
            f"backbone + LoRA adapter + char-level text encoder). "
            f"Accuracy gate {'passed' if all_passed else 'FAILED'} "
            f"with max allowed drop of {ACCURACY_GATE_MAX_DROP:.0%}."
        ),
    }

    report_path = write_json(output_dir / "conversion_report.json", report)
    print(f"\nConversion report: {report_path}")
    print(f"Overall accuracy gate: {overall_status.upper()}")
    print(f"Package size: {report['mlpackage_size_mb']} MB")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
