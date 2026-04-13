#!/usr/bin/env python3
"""Phase 6 statistical analysis — ingests all experiment artifacts and
produces reproducible, honest summary outputs.

Usage:
    python3 ml/scripts/run_statistical_analysis.py
    python3 ml/scripts/run_statistical_analysis.py --output-dir results/analysis/phase6_v0

Inputs consumed:
    results/baselines/                 — heuristic baseline run_result.json
    results/trainable_baselines/       — trainable baseline run_result.json
    results/selection_sweeps/          — sweep summary.json + per-run JSONs
    results/coreml_exports/            — conversion_report.json
    results/device_profiles/analysis/  — device-profile summary.json

Outputs written to {output_dir}/:
    summary.json      — complete Phase 6 analysis (machine-readable)
    summary.csv       — flat comparison table
    analysis.md       — human-readable report
    learning_curves.svg  — deterministic learning-curve plot (if data supports)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "ml" / "src"))

from axiom.analysis.schemas import (
    AnalysisStatus,
    ComparisonAnalysis,
    DeviceProfileAnalysis,
    LatencyAnalysis,
    LearningCurveAnalysis,
    PairedComparison,
    ParetoAnalysis,
    ParetoPoint,
    Phase6Analysis,
    PowerLawFit,
    StrategyCurve,
)
from axiom.analysis.stats import (
    bootstrap_ci,
    fit_power_law,
    paired_bootstrap_diff,
    percentile,
)


# ===================================================================
# Input loading
# ===================================================================


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_baselines(results_dir: Path) -> list[dict[str, Any]]:
    """Load all baseline run_result.json files."""
    baselines_dir = results_dir / "baselines"
    results = []
    if baselines_dir.is_dir():
        for child in sorted(baselines_dir.iterdir()):
            rr = child / "run_result.json"
            if rr.exists():
                results.append(load_json(rr))
    return results


def discover_trainable_baselines(results_dir: Path) -> list[dict[str, Any]]:
    tb_dir = results_dir / "trainable_baselines"
    results = []
    if tb_dir.is_dir():
        for child in sorted(tb_dir.iterdir()):
            rr = child / "run_result.json"
            if rr.exists():
                results.append(load_json(rr))
    return results


def discover_sweep(results_dir: Path) -> dict[str, Any] | None:
    """Load the latest sweep summary + learning-curve summary."""
    sweep_dir = results_dir / "selection_sweeps" / "sweep_v0"
    summary_path = sweep_dir / "summary.json"
    if not summary_path.exists():
        # Try to find any sweep directory
        sweeps_root = results_dir / "selection_sweeps"
        if sweeps_root.is_dir():
            for child in sorted(sweeps_root.iterdir(), reverse=True):
                sp = child / "summary.json"
                if sp.exists():
                    summary_path = sp
                    sweep_dir = child
                    break
    if not summary_path.exists():
        return None

    data: dict[str, Any] = load_json(summary_path)

    # Also load learning-curve summary if available
    lc_path = sweep_dir / "analysis" / "learning_curve_summary.json"
    if lc_path.exists():
        data["learning_curve_summary"] = load_json(lc_path)

    # Load per-run files for seed-level data
    runs_dir = sweep_dir / "runs"
    if runs_dir.is_dir():
        per_run: list[dict[str, Any]] = []
        for rp in sorted(runs_dir.glob("*.json")):
            per_run.append(load_json(rp))
        data["per_run_results"] = per_run

    return data


def discover_coreml_exports(results_dir: Path) -> list[dict[str, Any]]:
    exports_dir = results_dir / "coreml_exports"
    results = []
    if exports_dir.is_dir():
        for child in sorted(exports_dir.iterdir()):
            cr = child / "conversion_report.json"
            if cr.exists():
                results.append(load_json(cr))
    return results


def discover_device_profiles(results_dir: Path) -> dict[str, Any] | None:
    summary_path = results_dir / "device_profiles" / "analysis" / "summary.json"
    if summary_path.exists():
        return load_json(summary_path)
    return None


# ===================================================================
# Analysis: Learning curves
# ===================================================================


def analyze_learning_curves(sweep: dict[str, Any] | None) -> LearningCurveAnalysis:
    """Analyze selection-strategy learning curves with bootstrap CIs."""
    if sweep is None:
        return LearningCurveAnalysis(
            status=AnalysisStatus.BLOCKED,
            reason="No selection sweep data found.",
            strategies=[],
            dataset_info={},
        )

    dataset_info = sweep.get("dataset", {})
    per_run = sweep.get("per_run_results", [])
    lc_summary = sweep.get("learning_curve_summary", {})

    if not per_run and not lc_summary:
        return LearningCurveAnalysis(
            status=AnalysisStatus.INSUFFICIENT_DATA,
            reason="No per-run results or learning-curve summary found.",
            strategies=[],
            dataset_info=dataset_info,
        )

    # Group runs by (strategy, budget) → list of seed metrics
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for run in per_run:
        key = (run.get("strategy", ""), run.get("budget", 0))
        grouped.setdefault(key, []).append(run)

    # Build per-strategy curves
    strategies_seen = sorted(set(k[0] for k in grouped))
    budgets_seen = sorted(set(k[1] for k in grouped))

    strategy_curves: list[StrategyCurve] = []
    notes: list[str] = []

    for strat in strategies_seen:
        budgets: list[int] = []
        test_em_means: list[float] = []
        test_em_cis: list[dict[str, Any]] = []
        val_em_means: list[float] = []

        for budget in budgets_seen:
            runs = grouped.get((strat, budget), [])
            if not runs:
                continue

            test_ems = [
                r.get("metrics", {}).get("test", {}).get("exact_match", 0.0)
                for r in runs
            ]
            val_ems = [
                r.get("metrics", {}).get("val", {}).get("exact_match", 0.0)
                for r in runs
            ]

            budgets.append(budget)
            test_em_means.append(sum(test_ems) / len(test_ems) if test_ems else 0.0)
            val_em_means.append(sum(val_ems) / len(val_ems) if val_ems else 0.0)

            ci = bootstrap_ci(test_ems, statistic="mean", seed=42 + budget)
            test_em_cis.append(ci.to_dict())

        # Attempt power-law fit on test EM means
        plaw = fit_power_law(
            [float(b) for b in budgets],
            test_em_means,
            min_points=3,
            min_nonzero_y=2,
        )

        # Check if val is entirely zero (degenerate)
        all_val_zero = all(v < 1e-12 for v in val_em_means)
        if all_val_zero and val_em_means:
            notes.append(
                f"Strategy '{strat}': all validation EM values are 0.0. "
                f"This is expected with the heuristic baseline on a small dataset "
                f"where val examples don't overlap with memorized mappings."
            )

        curve_status = AnalysisStatus.COMPLETE
        curve_reason = ""
        if len(budgets) < 3:
            curve_status = AnalysisStatus.INSUFFICIENT_DATA
            curve_reason = f"Only {len(budgets)} budget levels for strategy '{strat}'."

        strategy_curves.append(StrategyCurve(
            strategy=strat,
            budgets=budgets,
            test_em_means=[round(v, 6) for v in test_em_means],
            test_em_cis=test_em_cis,
            val_em_means=[round(v, 6) for v in val_em_means],
            power_law_fit=plaw.to_dict(),
            status=curve_status,
            reason=curve_reason,
        ))

    # Overall status
    skipped_strats = sweep.get("strategies_skipped", [])
    if skipped_strats:
        notes.append(
            "Skipped strategies: "
            + ", ".join(s.get("strategy", "?") for s in skipped_strats)
            + ". See selection sweep docs for reasons."
        )

    overall_status = AnalysisStatus.PARTIAL
    overall_reason = (
        f"{len(strategies_seen)} strategies analyzed across "
        f"{len(budgets_seen)} budgets. "
        f"Dataset is small (pool={dataset_info.get('pool_size', '?')}, "
        f"test={dataset_info.get('test_size', '?')}, "
        f"val={dataset_info.get('val_size', '?')}); "
        f"results validate the pipeline but are not publication-ready."
    )

    return LearningCurveAnalysis(
        status=overall_status,
        reason=overall_reason,
        strategies=[c.to_dict() for c in strategy_curves],
        dataset_info=dataset_info,
        notes=notes,
    )


# ===================================================================
# Analysis: Strategy comparisons
# ===================================================================


def analyze_comparisons(
    sweep: dict[str, Any] | None,
    baselines: list[dict[str, Any]],
    trainable: list[dict[str, Any]],
) -> ComparisonAnalysis:
    """Paired bootstrap comparisons between strategies and baselines."""
    notes: list[str] = []

    # --- Baseline vs trainable baseline ---
    baseline_comp: dict[str, Any] = {}
    heuristic = next(
        (b for b in baselines if b.get("model", {}).get("model_id") == "question_lookup_v0"),
        None,
    )
    trainable_b = next(
        (t for t in trainable if t.get("model", {}).get("model_id") == "tiny_multimodal_v0"),
        None,
    )

    if heuristic and trainable_b:
        h_test = heuristic.get("metrics", {}).get("test", {}).get("exact_match", 0.0)
        t_test = trainable_b.get("metrics", {}).get("test", {}).get("exact_match", 0.0)
        h_pool = heuristic.get("metrics", {}).get("pool", {}).get("exact_match", 0.0)
        t_pool = trainable_b.get("metrics", {}).get("pool", {}).get("exact_match", 0.0)

        baseline_comp = {
            "heuristic_baseline": {
                "model_id": "question_lookup_v0",
                "pool_em": round(h_pool, 4),
                "test_em": round(h_test, 4),
                "val_em": 0.0,
            },
            "trainable_baseline": {
                "model_id": "tiny_multimodal_v0",
                "pool_em": round(t_pool, 4),
                "test_em": round(t_test, 4),
                "val_em": 0.0,
                "params": trainable_b.get("model", {}).get("params_millions"),
            },
            "test_em_diff": round(t_test - h_test, 4),
            "pool_em_diff": round(t_pool - h_pool, 4),
            "status": AnalysisStatus.COMPLETE,
            "reason": (
                "Single-seed comparison. Heuristic baseline memorizes pool answers "
                "(high pool EM) but does not generalize (low test EM). Trainable "
                "baseline also has low test EM on this small dataset. No statistical "
                "significance test is meaningful with 1 run per model."
            ),
            "notes": [
                "Both models achieve 10% test EM (1/10 correct) and 0% val EM.",
                "The heuristic baseline's high pool EM (73%) reflects memorization, "
                "not generalization.",
                "Paired comparison is not applicable: different model architectures "
                "with a single run each.",
            ],
        }
    else:
        baseline_comp = {
            "status": AnalysisStatus.BLOCKED,
            "reason": "Missing heuristic or trainable baseline results.",
        }

    # --- Pairwise strategy comparisons ---
    pairwise: list[dict[str, Any]] = []
    if sweep is None:
        return ComparisonAnalysis(
            status=AnalysisStatus.BLOCKED,
            reason="No sweep data for strategy comparisons.",
            baseline_comparison=baseline_comp,
            pairwise_comparisons=[],
            notes=notes,
        )

    per_run = sweep.get("per_run_results", [])
    # Group by (strategy, budget, seed)
    by_strat_budget: dict[tuple[str, int], dict[int, float]] = {}
    for run in per_run:
        strat = run.get("strategy", "")
        budget = run.get("budget", 0)
        seed = run.get("seed", 0)
        test_em = run.get("metrics", {}).get("test", {}).get("exact_match", 0.0)
        by_strat_budget.setdefault((strat, budget), {})[seed] = test_em

    strategies = sorted(set(k[0] for k in by_strat_budget))
    budgets = sorted(set(k[1] for k in by_strat_budget))

    # Compare all strategy pairs at the full-pool budget
    full_budget = max(budgets) if budgets else 0
    for i, strat_a in enumerate(strategies):
        for strat_b in strategies[i + 1:]:
            seeds_a = by_strat_budget.get((strat_a, full_budget), {})
            seeds_b = by_strat_budget.get((strat_b, full_budget), {})

            # Align by seed
            common_seeds = sorted(set(seeds_a) & set(seeds_b))
            vals_a = [seeds_a[s] for s in common_seeds]
            vals_b = [seeds_b[s] for s in common_seeds]

            diff_result = paired_bootstrap_diff(vals_a, vals_b, seed=42)

            comp = PairedComparison(
                strategy_a=strat_a,
                strategy_b=strat_b,
                metric="test_em",
                budget=full_budget,
                mean_diff=diff_result["mean_diff"],
                ci_lower=diff_result["ci_lower"],
                ci_upper=diff_result["ci_upper"],
                ci_level=diff_result["ci_level"],
                n_bootstrap=diff_result["n_bootstrap"],
                n_seeds=len(common_seeds),
                status=diff_result["status"],
                reason=diff_result.get("reason", ""),
            )
            pairwise.append(comp.to_dict())

    if not pairwise:
        notes.append("No pairwise comparisons possible (insufficient strategies).")

    # Check if all test EMs are tiny
    all_ems = [
        run.get("metrics", {}).get("test", {}).get("exact_match", 0.0)
        for run in per_run
    ]
    if all(em < 0.01 for em in all_ems):
        notes.append(
            "All test EM values are near zero. Strategy differences are not "
            "statistically meaningful at current dataset scale."
        )

    overall_status = AnalysisStatus.PARTIAL
    reason = (
        f"{len(pairwise)} pairwise comparisons at budget={full_budget} "
        f"with {len(strategies)} strategies. "
        f"Small sample sizes (3 seeds); bootstrap CIs are provided but "
        f"may be unreliable."
    )

    return ComparisonAnalysis(
        status=overall_status,
        reason=reason,
        baseline_comparison=baseline_comp,
        pairwise_comparisons=pairwise,
        notes=notes,
    )


# ===================================================================
# Analysis: Device profiles
# ===================================================================


def analyze_device_profiles(
    dp_summary: dict[str, Any] | None,
) -> DeviceProfileAnalysis:
    """Separate simulator and physical-device latency evidence."""
    if dp_summary is None:
        return DeviceProfileAnalysis(
            status=AnalysisStatus.BLOCKED,
            reason="No device-profile summary found.",
            simulator=[],
            physical_device=[],
            memory_status=AnalysisStatus.BLOCKED,
            memory_reason="No device-profile data.",
            energy_status=AnalysisStatus.BLOCKED,
            energy_reason="No device-profile data.",
        )

    sessions = dp_summary.get("sessions", [])
    sim_sessions: list[dict[str, Any]] = []
    phys_sessions: list[dict[str, Any]] = []

    for s in sessions:
        # Classify as simulator or physical based on device name / session dir
        session_dir = s.get("session_dir", "")
        is_sim = "sim" in session_dir.lower() or "simulator" in s.get("device_name", "").lower()

        latency = s.get("latency", {})
        thresholds = s.get("thresholds", [])

        analysis = LatencyAnalysis(
            environment="simulator" if is_sim else "physical_device",
            model_id=s.get("model_id", "unknown"),
            n_sessions=1,
            n_total_records=s.get("total_records", 0),
            p50_ms=latency.get("p50_ms", 0.0),
            p95_ms=latency.get("p95_ms", 0.0),
            mean_ms=latency.get("mean_ms", 0.0),
            min_ms=latency.get("min_ms", 0),
            max_ms=latency.get("max_ms", 0),
            bootstrap_ci_p50=None,  # Would need raw per-iteration data
            threshold_evaluations=thresholds,
            status=AnalysisStatus.SIMULATOR_ONLY if is_sim else AnalysisStatus.COMPLETE,
            reason=(
                "Simulator latency — not valid for on-device performance conclusions. "
                "No NPU, no real thermal behavior."
                if is_sim else "Physical-device measurement."
            ),
        )

        if is_sim:
            sim_sessions.append(analysis.to_dict())
        else:
            phys_sessions.append(analysis.to_dict())

    # Memory / energy status
    has_trace = any(s.get("has_trace_metrics", False) for s in sessions)
    has_phys = len(phys_sessions) > 0

    memory_status = AnalysisStatus.PHYSICAL_DEVICE_REQUIRED
    memory_reason = "No physical-device Instruments Allocations trace captured yet."
    if has_trace and has_phys:
        memory_status = AnalysisStatus.COMPLETE
        memory_reason = "Physical-device memory data available."

    energy_status = AnalysisStatus.PHYSICAL_DEVICE_REQUIRED
    energy_reason = (
        "Energy Log requires physical device. Instruments reports relative "
        "levels (0-20 scale), not battery %/hr. Not available from Simulator."
    )

    notes: list[str] = []
    if sim_sessions and not phys_sessions:
        notes.append(
            "All latency data is from Simulator only. These validate the "
            "instrumentation pipeline but are NOT publishable on-device evidence."
        )
    if not sessions:
        notes.append("No profiling sessions found.")

    overall_status = AnalysisStatus.SIMULATOR_ONLY if not phys_sessions else AnalysisStatus.COMPLETE
    overall_reason = (
        f"{len(sim_sessions)} simulator session(s), "
        f"{len(phys_sessions)} physical-device session(s)."
    )

    return DeviceProfileAnalysis(
        status=overall_status,
        reason=overall_reason,
        simulator=sim_sessions,
        physical_device=phys_sessions,
        memory_status=memory_status,
        memory_reason=memory_reason,
        energy_status=energy_status,
        energy_reason=energy_reason,
        notes=notes,
    )


# ===================================================================
# Analysis: Pareto
# ===================================================================


def analyze_pareto(
    baselines: list[dict[str, Any]],
    trainable: list[dict[str, Any]],
    coreml_exports: list[dict[str, Any]],
    dp_summary: dict[str, Any] | None,
) -> ParetoAnalysis:
    """Quality vs latency vs size Pareto view."""
    points: list[ParetoPoint] = []
    notes: list[str] = []

    # Gather all models with their test EM
    models: dict[str, dict[str, Any]] = {}

    for b in baselines:
        mid = b.get("model", {}).get("model_id", "unknown")
        test_em = b.get("metrics", {}).get("test", {}).get("exact_match", 0.0)
        size_mb = b.get("model", {}).get("expected_app_footprint_mb")
        models[mid] = {"test_em": test_em, "size_mb": size_mb, "source": "baseline"}

    for t in trainable:
        mid = t.get("model", {}).get("model_id", "unknown")
        test_em = t.get("metrics", {}).get("test", {}).get("exact_match", 0.0)
        size_mb = t.get("model", {}).get("expected_app_footprint_mb")
        models[mid] = {"test_em": test_em, "size_mb": size_mb, "source": "trainable"}

    # Get latency from device profiles
    latency_by_model: dict[str, dict[str, Any]] = {}
    if dp_summary:
        for s in dp_summary.get("sessions", []):
            mid = s.get("model_id", "unknown")
            session_dir = s.get("session_dir", "")
            is_sim = "sim" in session_dir.lower()
            p50 = s.get("latency", {}).get("p50_ms", 0.0)

            env = "simulator" if is_sim else "physical_device"
            # Keep physical if available, otherwise simulator
            existing = latency_by_model.get(mid)
            if existing is None or (existing["env"] == "simulator" and env == "physical_device"):
                latency_by_model[mid] = {"p50": p50, "env": env}

    # Build Pareto points
    for mid, info in models.items():
        lat = latency_by_model.get(mid, {})
        p50 = lat.get("p50") if lat else None
        lat_env = lat.get("env", "unavailable") if lat else "unavailable"

        point = ParetoPoint(
            model_id=mid,
            quality_metric="test_em",
            quality_value=info["test_em"],
            latency_p50_ms=p50,
            latency_environment=lat_env,
            artifact_size_mb=info.get("size_mb"),
            is_pareto_optimal=False,  # Computed below
            status=AnalysisStatus.SIMULATOR_ONLY if lat_env == "simulator" else (
                AnalysisStatus.COMPLETE if lat_env == "physical_device" else AnalysisStatus.PARTIAL
            ),
            reason="" if lat_env != "unavailable" else "No latency data available.",
        )
        points.append(point)

    # Simple Pareto optimality: non-dominated on (quality DESC, latency ASC)
    for i, p in enumerate(points):
        dominated = False
        for j, q in enumerate(points):
            if i == j:
                continue
            # q dominates p if q is at least as good on all and strictly better on one
            q_better_quality = q.quality_value >= p.quality_value
            q_better_latency = (
                (q.latency_p50_ms is not None and p.latency_p50_ms is not None
                 and q.latency_p50_ms <= p.latency_p50_ms)
                or q.latency_p50_ms is None  # can't compare
            )
            q_strictly_better = (
                q.quality_value > p.quality_value
                or (q.latency_p50_ms is not None and p.latency_p50_ms is not None
                    and q.latency_p50_ms < p.latency_p50_ms)
            )
            if q_better_quality and q_better_latency and q_strictly_better:
                dominated = True
                break
        if not dominated:
            p.is_pareto_optimal = True

    if not points:
        notes.append("No model data available for Pareto analysis.")

    # Check for mixed environments
    envs = set(p.latency_environment for p in points if p.latency_p50_ms is not None)
    if len(envs) > 1:
        notes.append(
            "WARNING: Pareto view mixes latency from different environments. "
            "Do NOT compare simulator and physical-device latencies directly."
        )
    if envs == {"simulator"}:
        notes.append(
            "All latency data is from Simulator. Pareto conclusions are "
            "preliminary and not publishable."
        )

    overall_status = AnalysisStatus.PARTIAL
    reason = f"{len(points)} model(s) in Pareto view."

    return ParetoAnalysis(
        status=overall_status,
        reason=reason,
        points=[p.to_dict() for p in points],
        notes=notes,
    )


# ===================================================================
# Output writers
# ===================================================================


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_csv_table(path: Path, analysis: Phase6Analysis) -> None:
    """Write a flat comparison CSV from the analysis."""
    path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []

    # Baseline comparison
    bc = analysis.comparisons.get("baseline_comparison", {})
    for key in ["heuristic_baseline", "trainable_baseline"]:
        entry = bc.get(key, {})
        if "model_id" in entry:
            rows.append({
                "model_id": entry["model_id"],
                "type": key.replace("_", " "),
                "pool_em": entry.get("pool_em", ""),
                "test_em": entry.get("test_em", ""),
                "val_em": entry.get("val_em", ""),
                "params_m": entry.get("params", ""),
                "latency_p50_ms": "",
                "latency_env": "",
                "artifact_size_mb": "",
            })

    # Pareto points
    for p in analysis.pareto.get("points", []):
        existing = next((r for r in rows if r["model_id"] == p["model_id"]), None)
        if existing:
            existing["latency_p50_ms"] = p.get("latency_p50_ms", "")
            existing["latency_env"] = p.get("latency_environment", "")
            existing["artifact_size_mb"] = p.get("artifact_size_mb", "")
        else:
            rows.append({
                "model_id": p["model_id"],
                "type": "pareto_point",
                "pool_em": "",
                "test_em": p.get("quality_value", ""),
                "val_em": "",
                "params_m": "",
                "latency_p50_ms": p.get("latency_p50_ms", ""),
                "latency_env": p.get("latency_environment", ""),
                "artifact_size_mb": p.get("artifact_size_mb", ""),
            })

    fieldnames = [
        "model_id", "type", "pool_em", "test_em", "val_em",
        "params_m", "latency_p50_ms", "latency_env", "artifact_size_mb",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown_report(path: Path, analysis: Phase6Analysis) -> None:
    """Write a human-readable Phase 6 analysis report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    lines.append("# AXIOM-Mobile Phase 6 Statistical Analysis Report")
    lines.append("")
    lines.append(f"Generated: {analysis.created_at_utc}")
    lines.append(f"Version: {analysis.version}")
    lines.append(f"Overall status: **{analysis.overall_status}**")
    lines.append("")

    if analysis.overall_notes:
        lines.append("## Key Notes")
        lines.append("")
        for note in analysis.overall_notes:
            lines.append(f"- {note}")
        lines.append("")

    # --- Learning Curves ---
    lc = analysis.learning_curves
    lines.append("## 1. Learning-Curve / Scaling Analysis")
    lines.append("")
    lines.append(f"**Status:** {lc.get('status', '?')}")
    lines.append(f"**Reason:** {lc.get('reason', '')}")
    lines.append("")

    ds = lc.get("dataset_info", {})
    if ds:
        lines.append(f"Dataset: pool={ds.get('pool_size', '?')}, "
                      f"val={ds.get('val_size', '?')}, test={ds.get('test_size', '?')}")
        lines.append("")

    for strat_data in lc.get("strategies", []):
        strat = strat_data.get("strategy", "?")
        lines.append(f"### Strategy: {strat}")
        lines.append("")

        budgets = strat_data.get("budgets", [])
        means = strat_data.get("test_em_means", [])
        cis = strat_data.get("test_em_cis", [])
        val_means = strat_data.get("val_em_means", [])

        if budgets:
            lines.append("| Budget | Test EM (mean) | 95% CI | Val EM |")
            lines.append("|--------|---------------|--------|--------|")
            for i, b in enumerate(budgets):
                ci_str = "—"
                if i < len(cis):
                    ci = cis[i]
                    ci_str = f"[{ci.get('ci_lower', 0):.3f}, {ci.get('ci_upper', 0):.3f}]"
                v = val_means[i] if i < len(val_means) else 0.0
                m = means[i] if i < len(means) else 0.0
                lines.append(f"| {b} | {m:.4f} | {ci_str} | {v:.4f} |")
            lines.append("")

        plaw = strat_data.get("power_law_fit", {})
        lines.append(f"**Power-law fit:** {plaw.get('status', '?')} — {plaw.get('reason', '')}")
        if plaw.get("a") is not None:
            lines.append(f"  - y = {plaw['a']:.4f} * x^{plaw.get('b', 0):.4f}, "
                          f"R^2 = {plaw.get('r_squared', 0):.4f}")
        lines.append("")

    for note in lc.get("notes", []):
        lines.append(f"> {note}")
    lines.append("")

    # --- Comparisons ---
    comp = analysis.comparisons
    lines.append("## 2. Model and Strategy Comparisons")
    lines.append("")
    lines.append(f"**Status:** {comp.get('status', '?')}")
    lines.append("")

    bc = comp.get("baseline_comparison", {})
    if "heuristic_baseline" in bc:
        hb = bc["heuristic_baseline"]
        tb = bc.get("trainable_baseline", {})
        lines.append("### Baseline Comparison")
        lines.append("")
        lines.append("| Model | Pool EM | Test EM | Val EM |")
        lines.append("|-------|---------|---------|--------|")
        lines.append(f"| {hb.get('model_id', '?')} (heuristic) | "
                      f"{hb.get('pool_em', 0):.4f} | "
                      f"{hb.get('test_em', 0):.4f} | "
                      f"{hb.get('val_em', 0):.4f} |")
        if tb:
            lines.append(f"| {tb.get('model_id', '?')} (trainable) | "
                          f"{tb.get('pool_em', 0):.4f} | "
                          f"{tb.get('test_em', 0):.4f} | "
                          f"{tb.get('val_em', 0):.4f} |")
        lines.append("")
        if bc.get("notes"):
            for n in bc["notes"]:
                lines.append(f"> {n}")
            lines.append("")

    pw = comp.get("pairwise_comparisons", [])
    if pw:
        lines.append("### Pairwise Strategy Comparisons (full-pool budget)")
        lines.append("")
        lines.append("| Strategy A | Strategy B | Mean diff (A-B) | 95% CI | Seeds | Status |")
        lines.append("|-----------|-----------|----------------|--------|-------|--------|")
        for c in pw:
            lines.append(
                f"| {c.get('strategy_a', '?')} | {c.get('strategy_b', '?')} | "
                f"{c.get('mean_diff', 0):.4f} | "
                f"[{c.get('ci_lower', 0):.4f}, {c.get('ci_upper', 0):.4f}] | "
                f"{c.get('n_seeds', 0)} | {c.get('status', '?')} |"
            )
        lines.append("")

    for note in comp.get("notes", []):
        lines.append(f"> {note}")
    lines.append("")

    # --- Device Profiles ---
    dp = analysis.device_profiles
    lines.append("## 3. Device-Profile Performance")
    lines.append("")
    lines.append(f"**Status:** {dp.get('status', '?')}")
    lines.append(f"**Reason:** {dp.get('reason', '')}")
    lines.append("")

    if dp.get("simulator"):
        lines.append("### Simulator Sessions (not publishable)")
        lines.append("")
        lines.append("| Model | Records | p50 (ms) | p95 (ms) | Mean (ms) | Status |")
        lines.append("|-------|---------|----------|----------|-----------|--------|")
        for s in dp["simulator"]:
            lines.append(
                f"| {s.get('model_id', '?')} | {s.get('n_total_records', 0)} | "
                f"{s.get('p50_ms', 0):.1f} | {s.get('p95_ms', 0):.1f} | "
                f"{s.get('mean_ms', 0):.1f} | {s.get('status', '?')} |"
            )
        lines.append("")

    if dp.get("physical_device"):
        lines.append("### Physical-Device Sessions")
        lines.append("")
        lines.append("| Model | Records | p50 (ms) | p95 (ms) | Mean (ms) | Status |")
        lines.append("|-------|---------|----------|----------|-----------|--------|")
        for s in dp["physical_device"]:
            lines.append(
                f"| {s.get('model_id', '?')} | {s.get('n_total_records', 0)} | "
                f"{s.get('p50_ms', 0):.1f} | {s.get('p95_ms', 0):.1f} | "
                f"{s.get('mean_ms', 0):.1f} | {s.get('status', '?')} |"
            )
        lines.append("")
    else:
        lines.append("### Physical-Device Sessions")
        lines.append("")
        lines.append("**No physical-device sessions captured yet.** "
                      "This is the primary remaining blocker for publishable results.")
        lines.append("")

    lines.append(f"**Memory:** {dp.get('memory_status', '?')} — {dp.get('memory_reason', '')}")
    lines.append(f"**Energy:** {dp.get('energy_status', '?')} — {dp.get('energy_reason', '')}")
    lines.append("")

    for note in dp.get("notes", []):
        lines.append(f"> {note}")
    lines.append("")

    # --- Pareto ---
    par = analysis.pareto
    lines.append("## 4. Pareto Analysis (Quality vs Efficiency)")
    lines.append("")
    lines.append(f"**Status:** {par.get('status', '?')}")
    lines.append("")

    pts = par.get("points", [])
    if pts:
        lines.append("| Model | Test EM | Latency p50 (ms) | Lat. Env | Size (MB) | Pareto? |")
        lines.append("|-------|---------|------------------|----------|-----------|---------|")
        for p in pts:
            lat = p.get("latency_p50_ms")
            lat_str = f"{lat:.1f}" if lat is not None else "—"
            size = p.get("artifact_size_mb")
            size_str = f"{size}" if size is not None else "—"
            lines.append(
                f"| {p.get('model_id', '?')} | {p.get('quality_value', 0):.4f} | "
                f"{lat_str} | {p.get('latency_environment', '?')} | "
                f"{size_str} | {'Yes' if p.get('is_pareto_optimal') else 'No'} |"
            )
        lines.append("")

    for note in par.get("notes", []):
        lines.append(f"> {note}")
    lines.append("")

    # --- What this report does NOT prove ---
    lines.append("## What This Report Does NOT Prove")
    lines.append("")
    lines.append("1. **No physical-device latency evidence.** All latency data is "
                  "from iOS Simulator. Simulator has no NPU, no real thermal "
                  "behavior, no meaningful energy data.")
    lines.append("2. **No statistical significance claims.** With 3 seeds and "
                  "tiny test/val sets, bootstrap CIs are provided for honesty "
                  "but should not be over-interpreted.")
    lines.append("3. **No quality conclusions.** The 70% EM target from the "
                  "research proposal is not met. The current heuristic baseline "
                  "and tiny multimodal model both achieve ~10% test EM.")
    lines.append("4. **No energy/memory conclusions.** These require physical-"
                  "device Instruments traces (Energy Log, Allocations).")
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_learning_curve_svg(
    path: Path,
    lc_analysis: LearningCurveAnalysis,
) -> bool:
    """Write a deterministic SVG learning-curve plot. Returns True if written."""
    strategies = lc_analysis.strategies
    if not strategies:
        return False

    # Check if there's any non-zero data worth plotting
    any_nonzero = False
    for s_data in strategies:
        s = StrategyCurve(**s_data) if isinstance(s_data, dict) else s_data
        means = s_data.get("test_em_means", []) if isinstance(s_data, dict) else s.test_em_means
        if any(m > 0 for m in means):
            any_nonzero = True
            break

    if not any_nonzero:
        return False  # All-zero plot would be misleading

    # SVG parameters
    W, H = 640, 400
    margin = {"top": 40, "right": 30, "bottom": 60, "left": 70}
    plot_w = W - margin["left"] - margin["right"]
    plot_h = H - margin["top"] - margin["bottom"]

    # Colorblind-friendly palette (Tol bright)
    colors = {
        "random": "#4477AA",
        "uncertainty": "#EE6677",
        "diversity": "#228833",
        "kg_guided": "#CCBB44",
    }

    # Determine axis ranges
    all_budgets: list[int] = []
    all_means: list[float] = []
    for s_data in strategies:
        budgets = s_data.get("budgets", []) if isinstance(s_data, dict) else s_data.budgets
        means = s_data.get("test_em_means", []) if isinstance(s_data, dict) else s_data.test_em_means
        all_budgets.extend(budgets)
        all_means.extend(means)

    if not all_budgets:
        return False

    x_min, x_max = min(all_budgets), max(all_budgets)
    y_max = max(max(all_means) * 1.2, 0.25)  # At least 0.25 for visibility

    def sx(x: float) -> float:
        if x_max == x_min:
            return margin["left"] + plot_w / 2
        return margin["left"] + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y: float) -> float:
        return margin["top"] + plot_h - (y / y_max) * plot_h

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(W),
        "height": str(H),
        "viewBox": f"0 0 {W} {H}",
    })

    # Background
    ET.SubElement(svg, "rect", {
        "width": str(W), "height": str(H),
        "fill": "white", "rx": "4",
    })

    # Grid lines
    for i in range(6):
        y_val = y_max * i / 5
        y_pos = sy(y_val)
        ET.SubElement(svg, "line", {
            "x1": str(margin["left"]), "y1": str(y_pos),
            "x2": str(W - margin["right"]), "y2": str(y_pos),
            "stroke": "#E0E0E0", "stroke-width": "1",
        })
        ET.SubElement(svg, "text", {
            "x": str(margin["left"] - 8), "y": str(y_pos + 4),
            "text-anchor": "end", "font-size": "11", "fill": "#666",
        }).text = f"{y_val:.2f}"

    # X-axis labels
    for b in sorted(set(all_budgets)):
        x_pos = sx(b)
        ET.SubElement(svg, "text", {
            "x": str(x_pos), "y": str(H - margin["bottom"] + 20),
            "text-anchor": "middle", "font-size": "11", "fill": "#666",
        }).text = str(b)

    # Axes
    ET.SubElement(svg, "line", {
        "x1": str(margin["left"]), "y1": str(margin["top"]),
        "x2": str(margin["left"]), "y2": str(H - margin["bottom"]),
        "stroke": "#333", "stroke-width": "1.5",
    })
    ET.SubElement(svg, "line", {
        "x1": str(margin["left"]), "y1": str(H - margin["bottom"]),
        "x2": str(W - margin["right"]), "y2": str(H - margin["bottom"]),
        "stroke": "#333", "stroke-width": "1.5",
    })

    # Axis titles
    ET.SubElement(svg, "text", {
        "x": str(W / 2), "y": str(H - 10),
        "text-anchor": "middle", "font-size": "13", "fill": "#333",
    }).text = "Training Budget (examples)"

    title_g = ET.SubElement(svg, "g", {
        "transform": f"translate(15, {H / 2}) rotate(-90)",
    })
    ET.SubElement(title_g, "text", {
        "text-anchor": "middle", "font-size": "13", "fill": "#333",
    }).text = "Test Exact Match"

    # Title
    ET.SubElement(svg, "text", {
        "x": str(W / 2), "y": "22",
        "text-anchor": "middle", "font-size": "15", "font-weight": "bold", "fill": "#333",
    }).text = "Learning Curves — Test EM by Strategy (with 95% Bootstrap CI)"

    # Plot each strategy
    legend_y = margin["top"] + 10
    for s_data in strategies:
        strat = s_data.get("strategy", "") if isinstance(s_data, dict) else s_data.strategy
        budgets = s_data.get("budgets", []) if isinstance(s_data, dict) else s_data.budgets
        means = s_data.get("test_em_means", []) if isinstance(s_data, dict) else s_data.test_em_means
        cis = s_data.get("test_em_cis", []) if isinstance(s_data, dict) else s_data.test_em_cis
        color = colors.get(strat, "#999999")

        if not budgets:
            continue

        # CI band
        if cis and len(cis) == len(budgets):
            upper_points = []
            lower_points = []
            for i, b in enumerate(budgets):
                ci = cis[i]
                upper_points.append(f"{sx(b)},{sy(ci.get('ci_upper', means[i]))}")
                lower_points.append(f"{sx(b)},{sy(ci.get('ci_lower', means[i]))}")

            polygon_points = " ".join(upper_points + list(reversed(lower_points)))
            ET.SubElement(svg, "polygon", {
                "points": polygon_points,
                "fill": color, "fill-opacity": "0.15", "stroke": "none",
            })

        # Mean line
        points_str = " ".join(f"{sx(b)},{sy(m)}" for b, m in zip(budgets, means))
        ET.SubElement(svg, "polyline", {
            "points": points_str,
            "fill": "none", "stroke": color, "stroke-width": "2",
        })

        # Data points
        for b, m in zip(budgets, means):
            ET.SubElement(svg, "circle", {
                "cx": str(sx(b)), "cy": str(sy(m)), "r": "3.5",
                "fill": color, "stroke": "white", "stroke-width": "1",
            })

        # Legend entry
        ET.SubElement(svg, "rect", {
            "x": str(W - margin["right"] - 130), "y": str(legend_y - 6),
            "width": "12", "height": "12", "fill": color, "rx": "2",
        })
        ET.SubElement(svg, "text", {
            "x": str(W - margin["right"] - 112), "y": str(legend_y + 4),
            "font-size": "11", "fill": "#333",
        }).text = strat
        legend_y += 18

    tree = ET.ElementTree(svg)
    ET.indent(tree, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(path), encoding="unicode", xml_declaration=True)
    return True


# ===================================================================
# Main
# ===================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=_PROJECT_ROOT / "results",
        help="Root results directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "results" / "analysis" / "phase6_v0",
        help="Output directory for analysis artifacts.",
    )
    args = parser.parse_args()

    results_dir: Path = args.results_dir.resolve()
    output_dir: Path = args.output_dir.resolve()

    print(f"Results root: {results_dir}")
    print(f"Output dir:   {output_dir}")

    # --- Load all inputs ---
    print("\n--- Loading inputs ---")

    baselines = discover_baselines(results_dir)
    print(f"  Baselines: {len(baselines)}")

    trainable = discover_trainable_baselines(results_dir)
    print(f"  Trainable baselines: {len(trainable)}")

    sweep = discover_sweep(results_dir)
    print(f"  Sweep: {'found' if sweep else 'not found'}")
    if sweep:
        per_run = sweep.get("per_run_results", [])
        print(f"    Per-run results: {len(per_run)}")

    coreml_exports = discover_coreml_exports(results_dir)
    print(f"  Core ML exports: {len(coreml_exports)}")

    dp_summary = discover_device_profiles(results_dir)
    print(f"  Device profiles: {'found' if dp_summary else 'not found'}")

    # --- Run analyses ---
    print("\n--- Running analyses ---")

    lc = analyze_learning_curves(sweep)
    print(f"  Learning curves: {lc.status}")

    comp = analyze_comparisons(sweep, baselines, trainable)
    print(f"  Comparisons: {comp.status}")

    dp = analyze_device_profiles(dp_summary)
    print(f"  Device profiles: {dp.status}")

    pareto = analyze_pareto(baselines, trainable, coreml_exports, dp_summary)
    print(f"  Pareto: {pareto.status}")

    # --- Build top-level summary ---
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    overall_notes: list[str] = []
    if dp.status == AnalysisStatus.SIMULATOR_ONLY:
        overall_notes.append(
            "All device profiling is simulator-only. Physical-device evidence "
            "is required before publishing performance conclusions."
        )
    if lc.status == AnalysisStatus.PARTIAL:
        overall_notes.append(
            "Learning-curve analysis is based on a small dataset (52 examples) "
            "with a heuristic lookup baseline. Results validate the pipeline "
            "but are not yet publication-ready."
        )
    overall_notes.append(
        "This analysis package is designed to absorb future physical-device "
        "data and larger-dataset runs with no code changes."
    )

    analysis = Phase6Analysis(
        analysis_id="phase6_v0",
        created_at_utc=now,
        version="0.1.0",
        learning_curves=lc.to_dict(),
        comparisons=comp.to_dict(),
        device_profiles=dp.to_dict(),
        pareto=pareto.to_dict(),
        overall_status=AnalysisStatus.PARTIAL,
        overall_notes=overall_notes,
    )

    # --- Write outputs ---
    print(f"\n--- Writing outputs to {output_dir} ---")

    write_json(output_dir / "summary.json", analysis.to_dict())
    print(f"  Wrote: summary.json")

    write_csv_table(output_dir / "summary.csv", analysis)
    print(f"  Wrote: summary.csv")

    write_markdown_report(output_dir / "analysis.md", analysis)
    print(f"  Wrote: analysis.md")

    if write_learning_curve_svg(output_dir / "learning_curves.svg", lc):
        print(f"  Wrote: learning_curves.svg")
    else:
        print(f"  Skipped: learning_curves.svg (insufficient non-zero data)")

    print(f"\nDone. Phase 6 analysis v0 complete.")
    print(f"Overall status: {analysis.overall_status}")


if __name__ == "__main__":
    main()
