#!/usr/bin/env python3
"""Run a selection-strategy sweep over the frozen dataset split.

For each (strategy, budget, seed) combination this script:
  1. Selects a subset of the pool using the strategy.
  2. Trains the specified model on that subset.
  3. Evaluates on val and test splits.
  4. Writes a per-run JSON result.

After all runs it writes ``summary.json`` and ``summary.csv``.

Strategies that are not yet implemented (e.g. kg_guided) are recorded
as skipped rather than crashing the sweep.

Example
-------
    python3 ml/scripts/run_selection_sweep.py \\
        --strategies random uncertainty diversity kg_guided \\
        --budgets 5 10 15 20 25 37 \\
        --seeds 0 1 2 \\
        --model-id question_lookup_v0
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from axiom.data import dataset_fingerprint, load_all_splits  # noqa: E402
from axiom.eval import compute_exact_match_metrics  # noqa: E402
from axiom.models import instantiate_model  # noqa: E402
from axiom.results import (  # noqa: E402
    SelectionRunResult,
    SplitMetrics,
    SweepSummary,
    write_json,
)
from axiom.selection import get_strategy  # noqa: E402

DEFAULT_STRATEGIES = ["random", "uncertainty", "diversity", "kg_guided"]
DEFAULT_BUDGETS = [5, 10, 15, 20, 25, 37]
DEFAULT_SEEDS = [0, 1, 2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--strategies",
        nargs="+",
        default=DEFAULT_STRATEGIES,
        help=f"Selection strategies to run (default: {DEFAULT_STRATEGIES})",
    )
    p.add_argument(
        "--budgets",
        nargs="+",
        type=int,
        default=DEFAULT_BUDGETS,
        help=f"Training budget sizes (default: {DEFAULT_BUDGETS})",
    )
    p.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=DEFAULT_SEEDS,
        help=f"Random seeds (default: {DEFAULT_SEEDS})",
    )
    p.add_argument(
        "--model-id",
        default="question_lookup_v0",
        help="Executable model identifier (default: question_lookup_v0)",
    )
    p.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="Repository root containing data/manifests/",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: results/selection_sweeps/<timestamp>)",
    )
    return p.parse_args()


def _validate_budgets(budgets: list[int], pool_size: int) -> list[int]:
    valid: list[int] = []
    dropped: list[int] = []
    for b in budgets:
        if b < 1 or b > pool_size:
            dropped.append(b)
        else:
            valid.append(b)
    if dropped:
        print(f"WARNING: dropped budgets outside [1, {pool_size}]: {dropped}")
    if not valid:
        raise ValueError(f"No valid budgets for pool size {pool_size}")
    return valid


def _run_one(
    strategy_name: str,
    budget: int,
    seed: int,
    model_id: str,
    pool: list[dict[str, Any]],
    splits: dict[str, list[dict[str, Any]]],
    ds_fingerprint: dict[str, Any],
    pool_size: int,
) -> SelectionRunResult:
    """Execute one (strategy, budget, seed) combination."""
    strategy = get_strategy(strategy_name)
    selected_indices = strategy.select(pool, budget, seed)

    selected_rows = [pool[i] for i in selected_indices]
    selected_ids = [pool[i]["id"] for i in selected_indices]

    model = instantiate_model(model_id)
    training_summary = model.train(selected_rows, val_rows=splits["val"], seed=seed)

    metrics_by_split: dict[str, dict[str, Any]] = {}

    # Evaluate on the selected training subset.
    train_preds = model.predict_many(selected_rows)
    train_metrics = compute_exact_match_metrics(selected_rows, train_preds)
    metrics_by_split["train_subset"] = SplitMetrics(
        split_name="train_subset", **train_metrics
    ).to_dict()

    # Evaluate on val and test.
    for split_name in ("val", "test"):
        preds = model.predict_many(splits[split_name])
        payload = compute_exact_match_metrics(splits[split_name], preds)
        metrics_by_split[split_name] = SplitMetrics(
            split_name=split_name, **payload
        ).to_dict()

    run_id = f"{strategy_name}_{model_id}_b{budget}_s{seed}"
    return SelectionRunResult(
        run_id=run_id,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        strategy=strategy_name,
        budget=budget,
        seed=seed,
        model_id=model_id,
        dataset={
            "fingerprint": ds_fingerprint,
            "pool_size": pool_size,
            "val_size": len(splits["val"]),
            "test_size": len(splits["test"]),
        },
        selected_ids=selected_ids,
        training={
            "num_selected": len(selected_ids),
            "seed": seed,
            "summary": training_summary,
        },
        metrics=metrics_by_split,
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "strategy",
        "budget",
        "seed",
        "model_id",
        "val_em",
        "test_em",
        "train_subset_em",
        "num_selected",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    # Load dataset.
    splits = load_all_splits(repo_root=repo_root, validate=True)
    pool = splits["pool"]
    pool_size = len(pool)
    ds_fingerprint = dataset_fingerprint(repo_root=repo_root)

    print(f"Pool size: {pool_size}  Val: {len(splits['val'])}  Test: {len(splits['test'])}")

    # Validate budgets.
    budgets = _validate_budgets(args.budgets, pool_size)

    # Output directory.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else repo_root / "results" / "selection_sweeps" / timestamp
    )
    runs_dir = output_dir / "runs"

    all_run_dicts: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    strategies_executed: list[str] = []
    strategies_skipped: list[dict[str, str]] = []
    seen_strategies: set[str] = set()

    for strategy_name in args.strategies:
        # Attempt to instantiate; catch blocked strategies early.
        try:
            strategy = get_strategy(strategy_name)
            # Quick probe: will it raise NotImplementedError?
            strategy.select(pool, min(budgets), args.seeds[0])
        except NotImplementedError as exc:
            reason = str(exc)
            print(f"SKIP  {strategy_name}: {reason}")
            if strategy_name not in seen_strategies:
                strategies_skipped.append(
                    {"strategy": strategy_name, "reason": reason}
                )
                seen_strategies.add(strategy_name)

            for budget in budgets:
                for seed in args.seeds:
                    csv_rows.append(
                        {
                            "strategy": strategy_name,
                            "budget": budget,
                            "seed": seed,
                            "model_id": args.model_id,
                            "val_em": "",
                            "test_em": "",
                            "train_subset_em": "",
                            "num_selected": "",
                            "status": "skipped",
                        }
                    )
            continue
        except KeyError as exc:
            print(f"ERROR unknown strategy '{strategy_name}': {exc}")
            continue

        if strategy_name not in seen_strategies:
            strategies_executed.append(strategy_name)
            seen_strategies.add(strategy_name)

        for budget in budgets:
            for seed in args.seeds:
                result = _run_one(
                    strategy_name=strategy_name,
                    budget=budget,
                    seed=seed,
                    model_id=args.model_id,
                    pool=pool,
                    splits=splits,
                    ds_fingerprint=ds_fingerprint,
                    pool_size=pool_size,
                )

                # Write per-run JSON.
                run_path = runs_dir / f"{result.run_id}.json"
                write_json(run_path, result.to_dict())

                val_em = result.metrics["val"]["exact_match"]
                test_em = result.metrics["test"]["exact_match"]
                train_em = result.metrics["train_subset"]["exact_match"]

                print(
                    f"  {result.run_id}  "
                    f"val_EM={val_em:.3f}  test_EM={test_em:.3f}  "
                    f"train_EM={train_em:.3f}"
                )

                all_run_dicts.append(result.to_dict())
                csv_rows.append(
                    {
                        "strategy": strategy_name,
                        "budget": budget,
                        "seed": seed,
                        "model_id": args.model_id,
                        "val_em": f"{val_em:.4f}",
                        "test_em": f"{test_em:.4f}",
                        "train_subset_em": f"{train_em:.4f}",
                        "num_selected": budget,
                        "status": "completed",
                    }
                )

    # Write aggregate summary.
    summary = SweepSummary(
        sweep_id=timestamp,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        config={
            "strategies_requested": args.strategies,
            "budgets": budgets,
            "seeds": args.seeds,
            "model_id": args.model_id,
        },
        dataset={
            "fingerprint": ds_fingerprint,
            "pool_size": pool_size,
            "val_size": len(splits["val"]),
            "test_size": len(splits["test"]),
        },
        strategies_executed=strategies_executed,
        strategies_skipped=strategies_skipped,
        runs=[
            {
                "run_id": r["run_id"],
                "strategy": r["strategy"],
                "budget": r["budget"],
                "seed": r["seed"],
                "val_em": r["metrics"]["val"]["exact_match"],
                "test_em": r["metrics"]["test"]["exact_match"],
                "train_subset_em": r["metrics"]["train_subset"]["exact_match"],
            }
            for r in all_run_dicts
        ],
    )

    summary_path = write_json(output_dir / "summary.json", summary.to_dict())
    csv_path = _write_csv(output_dir / "summary.csv", csv_rows)

    print(f"\nSweep complete.")
    print(f"  Executed: {strategies_executed}")
    print(f"  Skipped:  {[s['strategy'] for s in strategies_skipped]}")
    print(f"  Runs:     {len(all_run_dicts)}")
    print(f"  Summary:  {summary_path}")
    print(f"  CSV:      {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
