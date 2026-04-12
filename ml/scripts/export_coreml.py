#!/usr/bin/env python3
"""Export a trained TinyMultimodal checkpoint to Core ML (.mlpackage).

This is the Phase 4 export pipeline. It:
  1. Loads a trained checkpoint (model.pt + label_vocab.json + architecture.json)
  2. Traces the PyTorch model with torch.jit.trace
  3. Converts to Core ML via coremltools
  4. Runs a post-conversion accuracy gate on val/test splits
  5. Writes all artifacts and a conversion report to the output directory

Usage:
    # From a trainable baseline run:
    python3 ml/scripts/export_coreml.py \\
        --checkpoint-dir results/trainable_baselines/tiny_multimodal_v0_seed0/checkpoint \\
        --image-root /path/to/screenshots_v1

    # With synthetic fixtures:
    python3 ml/scripts/export_coreml.py \\
        --checkpoint-dir results/trainable_fixtures/run_output/checkpoint \\
        --image-root results/trainable_fixtures/images \\
        --manifest-dir results/trainable_fixtures/manifests \\
        --output-dir results/trainable_fixtures/coreml_output
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

import torch  # noqa: E402

from axiom.data.images import IMAGE_SIZE, ImageLoader, resolve_image_root  # noqa: E402
from axiom.eval import compute_exact_match_metrics, normalize_text  # noqa: E402
from axiom.models.tiny_multimodal import (  # noqa: E402
    MAX_CHAR_LEN,
    TinyMultimodalBaseline,
    TinyMultimodalNet,
    encode_question,
)
from axiom.models.specs import ModelSpec  # noqa: E402
from axiom.results import write_json  # noqa: E402

# Accuracy gate threshold: Core ML predictions must not drop more than
# this many percentage points vs PyTorch predictions on any eval split.
ACCURACY_GATE_MAX_DROP = 0.03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint-dir",
        required=True,
        help="Directory containing model.pt, label_vocab.json, architecture.json",
    )
    parser.add_argument(
        "--image-root",
        default=None,
        help="Path to private screenshot directory (or set AXIOM_SCREENSHOT_ROOT)",
    )
    parser.add_argument(
        "--manifest-dir",
        default=None,
        help="Override manifest directory (default: {repo-root}/data/manifests/)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for Core ML artifacts (default: results/coreml_exports/<model_id>_seed0/)",
    )
    parser.add_argument(
        "--model-id",
        default="tiny_multimodal_v0",
        help="Model identifier for spec lookup.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Seed used during training (for output naming).",
    )
    return parser.parse_args()


def _load_splits(manifest_dir: Path | None, repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Load manifest splits from disk."""
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


def _pytorch_predictions(
    model: TinyMultimodalBaseline,
    rows: list[dict[str, Any]],
) -> list[str]:
    """Get predictions from the PyTorch model."""
    return model.predict_many(rows)


def _coreml_predictions(
    mlmodel_path: Path,
    rows: list[dict[str, Any]],
    image_loader: ImageLoader,
    idx_to_label: dict[int, str],
) -> list[str]:
    """Get predictions from the Core ML model."""
    import coremltools as ct
    from PIL import Image

    mlmodel = ct.models.MLModel(str(mlmodel_path))
    predictions: list[str] = []

    for row in rows:
        # Load image as PIL — Core ML ImageType expects PIL.Image
        img_path = image_loader.resolve_path(row["image_filename"])
        pil_img = Image.open(img_path).convert("RGB").resize(
            (IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR
        )

        # Prepare text input
        char_ids = np.array([encode_question(row["question"])], dtype=np.int32)

        # Run prediction
        output = mlmodel.predict({"image": pil_img, "char_ids": char_ids})
        logits = output["logits"]

        # Decode
        pred_idx = int(np.argmax(logits))
        pred_label = idx_to_label.get(pred_idx, "")
        predictions.append(pred_label)

    return predictions


def _evaluate_accuracy_gate(
    pytorch_metrics: dict[str, float],
    coreml_metrics: dict[str, float],
    split_name: str,
) -> dict[str, Any]:
    """Compare PyTorch vs Core ML accuracy, return gate result."""
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

    # Default output dir
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        output_dir = repo_root / "results" / "coreml_exports" / f"{args.model_id}_seed{args.seed}"

    # Resolve image root
    image_root = resolve_image_root(args.image_root)
    print(f"Image root: {image_root}")
    print(f"Checkpoint: {checkpoint_dir}")

    # Load manifest dir
    manifest_dir = Path(args.manifest_dir).resolve() if args.manifest_dir else None
    splits = _load_splits(manifest_dir, repo_root)
    print(f"Splits: pool={len(splits['pool'])}, val={len(splits['val'])}, test={len(splits['test'])}")

    # Load trained PyTorch model from checkpoint
    print("\nLoading PyTorch checkpoint...")
    spec_dict = json.loads(
        (ROOT / "ml" / "configs" / "models" / f"{args.model_id}.json").read_text()
    )
    spec = ModelSpec.from_dict(spec_dict)
    model = TinyMultimodalBaseline.load_checkpoint(
        checkpoint_dir, spec, image_root=image_root
    )
    print("  Checkpoint loaded successfully.")

    # Get PyTorch predictions on eval splits
    print("\nRunning PyTorch inference...")
    pytorch_results: dict[str, dict[str, Any]] = {}
    for split_name in ("val", "test"):
        preds = _pytorch_predictions(model, splits[split_name])
        metrics = compute_exact_match_metrics(splits[split_name], preds)
        pytorch_results[split_name] = metrics
        print(f"  PyTorch {split_name}: EM={metrics['exact_match']:.4f} "
              f"({metrics['num_correct']}/{metrics['num_examples']})")

    # Export to Core ML
    print("\nExporting to Core ML...")
    export_info = model.export_coreml(output_dir)
    mlpackage_path = Path(export_info["mlpackage"])
    print(f"  .mlpackage saved: {mlpackage_path}")
    print(f"  Traced model saved: {export_info['traced_model']}")

    # Get Core ML predictions on eval splits
    print("\nRunning Core ML inference...")
    loader = ImageLoader(image_root)
    idx_to_label = {int(i): a for a, i in model._label_to_idx.items()}

    coreml_results: dict[str, dict[str, Any]] = {}
    gate_results: list[dict[str, Any]] = []

    for split_name in ("val", "test"):
        preds = _coreml_predictions(
            mlpackage_path, splits[split_name], loader, idx_to_label
        )
        metrics = compute_exact_match_metrics(splits[split_name], preds)
        coreml_results[split_name] = metrics
        print(f"  Core ML {split_name}: EM={metrics['exact_match']:.4f} "
              f"({metrics['num_correct']}/{metrics['num_examples']})")

        gate = _evaluate_accuracy_gate(
            pytorch_results[split_name], metrics, split_name
        )
        gate_results.append(gate)
        status = "PASS" if gate["gate_passed"] else "FAIL"
        print(f"  Gate {split_name}: {status} (drop={gate['accuracy_drop']:.4f}, "
              f"max={ACCURACY_GATE_MAX_DROP})")

    # Overall gate decision
    all_passed = all(g["gate_passed"] for g in gate_results)
    overall_status = "passed" if all_passed else "failed"

    # Write conversion report
    report = {
        "run_id": f"coreml_export_{args.model_id}_seed{args.seed}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": args.model_id,
        "checkpoint_dir": str(checkpoint_dir),
        "image_root": str(image_root),
        "export": export_info,
        "pytorch_metrics": {k: v for k, v in pytorch_results.items()},
        "coreml_metrics": {k: v for k, v in coreml_results.items()},
        "accuracy_gate": {
            "max_allowed_drop": ACCURACY_GATE_MAX_DROP,
            "overall_status": overall_status,
            "per_split": gate_results,
        },
        "notes": (
            f"Core ML export of {args.model_id}. "
            f"Accuracy gate {'passed' if all_passed else 'FAILED'} "
            f"with max allowed drop of {ACCURACY_GATE_MAX_DROP:.0%}."
        ),
    }

    report_path = write_json(output_dir / "conversion_report.json", report)
    print(f"\nConversion report: {report_path}")
    print(f"Overall accuracy gate: {overall_status.upper()}")

    # Print artifact summary
    print(f"\nArtifacts in {output_dir}:")
    for key, path in export_info.items():
        print(f"  {key}: {path}")
    print(f"  conversion_report: {report_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
