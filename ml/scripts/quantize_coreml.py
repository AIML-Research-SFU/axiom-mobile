#!/usr/bin/env python3
"""Post-training quantization for an already-exported Core ML model (Phase 11).

Deferred in Phase 4 for tiny_multimodal_v0/v1 because those models were
already tiny (96KB) -- not worth quantizing. axiom_lora_v1 is bigger
(2.04MB, dominated by the frozen pretrained MobileNetV3-Small backbone),
so this is where quantization actually has something to compress.

Applies int8 linear weight quantization via coremltools.optimize, then
re-runs the same accuracy-drop gate used at export time (this time:
original fp32/fp16 .mlpackage vs quantized .mlpackage, not PyTorch vs
CoreML) so compression is never accepted silently -- same discipline as
export_coreml.py / export_coreml_lora.py.

Usage:
    python3 ml/scripts/quantize_coreml.py \\
        --mlpackage results/coreml_exports/axiom_lora_v1_seed0_local/AxiomLora.mlpackage \\
        --label-vocab results/coreml_exports/axiom_lora_v1_seed0_local/label_vocab.json \\
        --image-root ~/Datasets/axiom-mobile/local_phase8_images \\
        --manifest-dir ~/Datasets/axiom-mobile/local_phase8_manifests
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from axiom.data.images import IMAGE_SIZE, ImageLoader, resolve_image_root  # noqa: E402
from axiom.eval import compute_exact_match_metrics  # noqa: E402
from axiom.models.tiny_multimodal import MAX_CHAR_LEN, encode_question  # noqa: E402
from axiom.results import write_json  # noqa: E402

ACCURACY_GATE_MAX_DROP = 0.03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlpackage", required=True, help="Path to the source .mlpackage")
    parser.add_argument("--label-vocab", required=True, help="Path to label_vocab.json")
    parser.add_argument("--image-root", default=None)
    parser.add_argument("--manifest-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--dtype", default="int8", choices=["int8", "uint8", "int4", "uint4"],
        help="Quantized weight dtype (default: int8)",
    )
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


def _predict(mlmodel_path: Path, rows: list[dict[str, Any]], loader: ImageLoader, idx_to_label: dict[int, str]) -> list[str]:
    import coremltools as ct
    from PIL import Image

    mlmodel = ct.models.MLModel(str(mlmodel_path))
    predictions: list[str] = []
    for row in rows:
        img_path = loader.resolve_path(row["image_filename"])
        pil_img = Image.open(img_path).convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)
        char_ids = np.array([encode_question(row["question"])], dtype=np.int32)
        output = mlmodel.predict({"image": pil_img, "char_ids": char_ids})
        pred_idx = int(np.argmax(output["logits"]))
        predictions.append(idx_to_label.get(pred_idx, ""))
    return predictions


def _dir_size_mb(path: Path) -> float:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    return total / 1024 / 1024


def main() -> int:
    args = parse_args()
    import coremltools as ct
    import coremltools.optimize as cto

    mlpackage_path = Path(args.mlpackage).resolve()
    label_vocab = json.loads(Path(args.label_vocab).read_text())
    idx_to_label = {int(i): a for a, i in label_vocab.items()}

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else mlpackage_path.parent / f"quantized_{args.dtype}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    image_root = resolve_image_root(args.image_root)
    manifest_dir = Path(args.manifest_dir).resolve() if args.manifest_dir else None
    splits = _load_splits(manifest_dir, ROOT)
    loader = ImageLoader(image_root)

    original_size_mb = _dir_size_mb(mlpackage_path)
    print(f"Original package: {mlpackage_path} ({original_size_mb:.2f} MB)")

    print(f"\nLoading and quantizing to {args.dtype}...")
    mlmodel = ct.models.MLModel(str(mlpackage_path))
    op_config = cto.coreml.OpLinearQuantizerConfig(mode="linear_symmetric", dtype=args.dtype)
    config = cto.coreml.OptimizationConfig(global_config=op_config)
    quantized = cto.coreml.linear_quantize_weights(mlmodel, config)

    quantized_path = output_dir / mlpackage_path.name
    quantized.save(str(quantized_path))
    quantized_size_mb = _dir_size_mb(quantized_path)
    compression_ratio = original_size_mb / quantized_size_mb if quantized_size_mb > 0 else float("nan")
    print(f"Quantized package: {quantized_path} ({quantized_size_mb:.2f} MB)")
    print(f"Compression ratio: {compression_ratio:.2f}x")

    print("\nRunning original-model inference...")
    original_results: dict[str, dict[str, Any]] = {}
    for split_name in ("val", "test"):
        preds = _predict(mlpackage_path, splits[split_name], loader, idx_to_label)
        original_results[split_name] = compute_exact_match_metrics(splits[split_name], preds)
        print(f"  original {split_name}: EM={original_results[split_name]['exact_match']:.4f}")

    print("\nRunning quantized-model inference...")
    quantized_results: dict[str, dict[str, Any]] = {}
    gate_results: list[dict[str, Any]] = []
    for split_name in ("val", "test"):
        preds = _predict(quantized_path, splits[split_name], loader, idx_to_label)
        quantized_results[split_name] = compute_exact_match_metrics(splits[split_name], preds)
        drop = original_results[split_name]["exact_match"] - quantized_results[split_name]["exact_match"]
        passed = drop <= ACCURACY_GATE_MAX_DROP
        gate_results.append({
            "split": split_name,
            "original_exact_match": round(original_results[split_name]["exact_match"], 4),
            "quantized_exact_match": round(quantized_results[split_name]["exact_match"], 4),
            "accuracy_drop": round(drop, 4),
            "max_allowed_drop": ACCURACY_GATE_MAX_DROP,
            "gate_passed": passed,
        })
        status = "PASS" if passed else "FAIL"
        print(f"  quantized {split_name}: EM={quantized_results[split_name]['exact_match']:.4f} "
              f"(drop={drop:.4f}) [{status}]")

    all_passed = all(g["gate_passed"] for g in gate_results)

    report = {
        "run_id": f"quantize_{args.dtype}_{mlpackage_path.stem}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_mlpackage": str(mlpackage_path),
        "quantized_mlpackage": str(quantized_path),
        "dtype": args.dtype,
        "original_size_mb": round(original_size_mb, 3),
        "quantized_size_mb": round(quantized_size_mb, 3),
        "compression_ratio": round(compression_ratio, 3),
        "original_metrics": original_results,
        "quantized_metrics": quantized_results,
        "accuracy_gate": {
            "max_allowed_drop": ACCURACY_GATE_MAX_DROP,
            "overall_status": "passed" if all_passed else "failed",
            "per_split": gate_results,
        },
    }
    report_path = write_json(output_dir / "quantization_report.json", report)
    print(f"\nReport: {report_path}")
    print(f"Overall accuracy gate: {'PASSED' if all_passed else 'FAILED'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
