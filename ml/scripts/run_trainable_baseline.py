#!/usr/bin/env python3
"""Train and evaluate a real multimodal baseline over the frozen dataset split.

This script is the first real trainable model path in the repo, designed
to produce actual model artifacts (checkpoint, label vocab, architecture
metadata) that can later be converted to Core ML in Phase 4.

Usage:
    python3 ml/scripts/run_trainable_baseline.py --image-root /path/to/screenshots_v1

    # Or with env var:
    AXIOM_SCREENSHOT_ROOT=/path/to/screenshots_v1 python3 ml/scripts/run_trainable_baseline.py

    # With synthetic fixtures for testing:
    python3 ml/scripts/run_trainable_baseline.py \\
        --image-root results/trainable_fixtures/images \\
        --manifest-dir results/trainable_fixtures/manifests \\
        --output-dir results/trainable_fixtures/run_output
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from axiom.data import dataset_fingerprint, load_all_splits  # noqa: E402
from axiom.data.images import ImageLoader, resolve_image_root  # noqa: E402
from axiom.eval import compute_exact_match_metrics, normalize_text  # noqa: E402
from axiom.models import instantiate_model, resolve_model_spec  # noqa: E402
from axiom.results import (  # noqa: E402
    BaselineRunResult,
    SplitMetrics,
    write_json,
    write_jsonl,
    write_run_result,
)


def _default_output_dir(repo_root: Path, model_id: str, seed: int) -> Path:
    return repo_root / "results" / "trainable_baselines" / f"{model_id}_seed{seed}"


def _prediction_rows(
    rows: list[dict[str, Any]], predictions: list[str]
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row, predicted in zip(rows, predictions):
        payload.append(
            {
                "id": row["id"],
                "image_filename": row["image_filename"],
                "question": row["question"],
                "gold_answer": row["answer"],
                "predicted_answer": predicted,
                "is_correct": normalize_text(str(row["answer"]))
                == normalize_text(str(predicted)),
            }
        )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-id",
        default="tiny_multimodal_v0",
        help="Model identifier from ml/configs/models/*.json",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    parser.add_argument(
        "--image-root",
        default=None,
        help="Path to private screenshot directory (or set AXIOM_SCREENSHOT_ROOT)",
    )
    parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="Repository root containing data/manifests/",
    )
    parser.add_argument(
        "--manifest-dir",
        default=None,
        help="Override manifest directory (default: {repo-root}/data/manifests/)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for result artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir is not None
        else _default_output_dir(repo_root, args.model_id, args.seed)
    )

    # Resolve image root
    image_root = resolve_image_root(args.image_root)
    print(f"Image root: {image_root}")

    # Load manifests
    if args.manifest_dir:
        # Override: load from custom manifest directory
        manifest_root = Path(args.manifest_dir).resolve()
        print(f"Manifest dir: {manifest_root}")
        # Build a temporary repo_root-like structure for the loader
        # by using the manifest_dir's parent's parent as repo_root
        # Actually, just load directly
        import json

        splits: dict[str, list[dict[str, Any]]] = {}
        for split_name in ("pool", "val", "test"):
            path = manifest_root / f"{split_name}.jsonl"
            if not path.exists():
                raise FileNotFoundError(f"Missing manifest: {path}")
            rows = []
            for line in path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    rows.append(json.loads(line))
            splits[split_name] = rows
        fingerprint = {"note": "custom manifest directory", "path": str(manifest_root)}
    else:
        splits = load_all_splits(repo_root=repo_root, validate=True)
        fingerprint = dataset_fingerprint(repo_root=repo_root)

    print(f"Splits: pool={len(splits['pool'])}, val={len(splits['val'])}, test={len(splits['test'])}")

    # Validate image availability
    loader = ImageLoader(image_root)
    all_filenames = set()
    for split_rows in splits.values():
        for row in split_rows:
            all_filenames.add(row["image_filename"])

    found, missing = loader.validate_manifest(
        [{"image_filename": f} for f in sorted(all_filenames)]
    )
    print(f"Images: {len(found)} found, {len(missing)} missing")
    if missing:
        print(f"Missing images: {missing[:10]}{'...' if len(missing) > 10 else ''}")
        print("ERROR: Cannot train without all images. Aborting.")
        return 1

    # Instantiate and train
    spec = resolve_model_spec(args.model_id)
    model = instantiate_model(args.model_id, image_root=image_root)

    print(f"\nTraining {args.model_id}...")
    training_summary = model.train(
        splits["pool"],
        val_rows=splits["val"],
        seed=args.seed,
    )
    print(f"Training complete. Loss={training_summary['final_loss']:.4f}, "
          f"Train acc={training_summary['train_accuracy']:.4f}, "
          f"Params={training_summary['parameter_count']:,}")

    # Save checkpoint
    checkpoint_dir = output_dir / "checkpoint"
    checkpoint_paths = model.save_checkpoint(checkpoint_dir)
    print(f"Checkpoint saved to: {checkpoint_dir}")

    # Evaluate on all splits
    metrics_by_split: dict[str, dict[str, Any]] = {}
    artifact_paths: dict[str, str] = {}

    for split_name, rows in splits.items():
        predictions = model.predict_many(rows)
        metric_payload = compute_exact_match_metrics(rows, predictions)
        split_metrics = SplitMetrics(split_name=split_name, **metric_payload)
        metrics_by_split[split_name] = split_metrics.to_dict()

        prediction_path = write_jsonl(
            output_dir / f"predictions_{split_name}.jsonl",
            _prediction_rows(rows, predictions),
        )
        artifact_paths[f"predictions_{split_name}"] = str(prediction_path)

    # Record checkpoint paths
    for key, path in checkpoint_paths.items():
        artifact_paths[f"checkpoint_{key}"] = path

    # Write training summary
    model_state_path = write_json(output_dir / "training_state.json", training_summary)
    artifact_paths["training_state"] = str(model_state_path)

    # Build and write run result
    result = BaselineRunResult(
        run_id=f"{args.model_id}_seed{args.seed}",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        model=spec.to_dict(),
        dataset={
            "fingerprint": fingerprint,
            "split_counts": {name: len(rows) for name, rows in splits.items()},
        },
        training={
            "train_split": "pool",
            "validation_split": "val",
            "test_split": "test",
            "seed": args.seed,
            "num_train_examples": len(splits["pool"]),
            "image_root": str(image_root),
            "summary": training_summary,
        },
        metrics=metrics_by_split,
        artifacts=artifact_paths,
        notes=(
            f"{args.model_id} is a real trainable multimodal baseline designed to "
            f"unblock Phase 4 Core ML conversion. It uses both image and text inputs "
            f"and produces a PyTorch checkpoint suitable for later export."
        ),
    )

    run_result_path = write_run_result(output_dir / "run_result.json", result)

    # Print results
    print(f"\nResults written to: {output_dir}")
    print(f"Run result: {run_result_path}")
    for split_name in ("pool", "val", "test"):
        sm = metrics_by_split[split_name]
        print(
            f"  {split_name}: EM={sm['exact_match']:.3f} "
            f"({sm['num_correct']}/{sm['num_examples']})"
        )

    print(f"\nCheckpoint artifacts:")
    for key, path in checkpoint_paths.items():
        print(f"  {key}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
