#!/usr/bin/env python3
"""Generate paper-ready assets from existing analysis artifacts.

Usage:
    python3 ml/scripts/build_paper_assets.py
    python3 ml/scripts/build_paper_assets.py --output-dir paper/assets/generated

Reads from:
    results/analysis/phase6_v0/summary.json
    results/analysis/phase6_v0/learning_curves.svg
    results/device_profiles/analysis/summary.json

Writes to {output_dir}/:
    learning_curves.svg          — copied from analysis output
    model_comparison.csv         — flat model comparison table
    device_profile_summary.csv   — per-session latency summary
    results_snapshot.md          — concise machine-generated results packet
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from io import StringIO
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent


def load_json(path: Path) -> dict[str, Any] | None:
    """Load a JSON file or return None if missing."""
    if not path.exists():
        print(f"  [skip] {path.relative_to(_PROJECT_ROOT)} not found")
        return None
    with open(path) as f:
        return json.load(f)


def copy_learning_curves(analysis_dir: Path, output_dir: Path) -> bool:
    """Copy the learning curves SVG from analysis output."""
    src = analysis_dir / "learning_curves.svg"
    if not src.exists():
        print("  [skip] learning_curves.svg not found in analysis output")
        return False
    dst = output_dir / "learning_curves.svg"
    shutil.copy2(src, dst)
    print(f"  [ok] learning_curves.svg ({dst.stat().st_size:,} bytes)")
    return True


def build_model_comparison(analysis: dict[str, Any], output_dir: Path) -> bool:
    """Build a flat model comparison CSV from the analysis summary."""
    rows: list[dict[str, str]] = []

    # Baseline comparison
    baseline = analysis.get("comparisons", {}).get("baseline_comparison", {})
    heuristic = baseline.get("heuristic_baseline", {})
    trainable = baseline.get("trainable_baseline", {})

    # Pareto data for latency/size
    pareto_points = {
        p["model_id"]: p for p in analysis.get("pareto", {}).get("points", [])
    }

    for model_data, model_type in [
        (heuristic, "heuristic baseline"),
        (trainable, "trainable baseline"),
    ]:
        model_id = model_data.get("model_id", "")
        if not model_id:
            continue
        pareto = pareto_points.get(model_id, {})

        rows.append({
            "model_id": model_id,
            "type": model_type,
            "pool_em": f"{model_data.get('pool_em', 0):.4f}",
            "test_em": f"{model_data.get('test_em', 0):.4f}",
            "val_em": f"{model_data.get('val_em', 0):.4f}",
            "params_m": str(model_data.get("params", "")),
            "latency_p50_ms": str(pareto.get("latency_p50_ms", "")),
            "latency_env": pareto.get("latency_environment", ""),
            "artifact_size_mb": str(pareto.get("artifact_size_mb", "")),
            "is_pareto_optimal": str(pareto.get("is_pareto_optimal", "")),
        })

    if not rows:
        print("  [skip] No model data found for comparison table")
        return False

    dst = output_dir / "model_comparison.csv"
    fields = list(rows[0].keys())
    with open(dst, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  [ok] model_comparison.csv ({len(rows)} models)")
    return True


def build_device_profile_summary(
    device_summary: dict[str, Any], output_dir: Path
) -> bool:
    """Build a per-session device profile CSV."""
    sessions = device_summary.get("sessions", [])
    if not sessions:
        print("  [skip] No device profile sessions found")
        return False

    rows: list[dict[str, str]] = []
    for s in sessions:
        lat = s.get("latency", {})
        rows.append({
            "session_dir": s.get("session_dir", ""),
            "model_id": s.get("model_id", ""),
            "device_name": s.get("device_name", ""),
            "system_version": s.get("system_version", ""),
            "is_placeholder": str(s.get("is_placeholder", "")),
            "iterations": str(s.get("benchmark_records", 0)),
            "p50_ms": str(lat.get("p50_ms", "")),
            "p95_ms": str(lat.get("p95_ms", "")),
            "mean_ms": str(lat.get("mean_ms", "")),
            "min_ms": str(lat.get("min_ms", "")),
            "max_ms": str(lat.get("max_ms", "")),
            "environment": "simulator" if "sim" in s.get("session_dir", "") else "physical_device",
        })

    dst = output_dir / "device_profile_summary.csv"
    fields = list(rows[0].keys())
    with open(dst, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  [ok] device_profile_summary.csv ({len(rows)} sessions)")
    return True


def build_results_snapshot(
    analysis: dict[str, Any],
    device_summary: dict[str, Any] | None,
    output_dir: Path,
) -> bool:
    """Build a concise machine-generated results snapshot for the paper draft."""
    lines: list[str] = []
    lines.append("# Results Snapshot")
    lines.append("")
    lines.append(f"Generated from: `results/analysis/phase6_v0/summary.json`")
    lines.append(f"Analysis version: {analysis.get('version', 'unknown')}")
    lines.append(f"Overall status: **{analysis.get('overall_status', 'unknown')}**")
    lines.append("")

    # Dataset info
    ds = analysis.get("learning_curves", {}).get("dataset_info", {})
    lines.append("## Dataset")
    lines.append("")
    lines.append(f"- Pool: {ds.get('pool_size', '?')}")
    lines.append(f"- Val: {ds.get('val_size', '?')}")
    lines.append(f"- Test: {ds.get('test_size', '?')}")
    fp = ds.get("fingerprint", {}).get("combined_sha256", "?")
    lines.append(f"- Fingerprint: `{fp[:16]}...`")
    lines.append("")

    # Baseline comparison
    baseline = analysis.get("comparisons", {}).get("baseline_comparison", {})
    lines.append("## Model Comparison")
    lines.append("")
    lines.append("| Model | Pool EM | Test EM | Val EM |")
    lines.append("|-------|---------|---------|--------|")
    for key in ["heuristic_baseline", "trainable_baseline"]:
        m = baseline.get(key, {})
        if m:
            lines.append(
                f"| {m.get('model_id', '?')} | "
                f"{m.get('pool_em', 0):.4f} | "
                f"{m.get('test_em', 0):.4f} | "
                f"{m.get('val_em', 0):.4f} |"
            )
    lines.append("")

    # Learning curves summary
    strategies = analysis.get("learning_curves", {}).get("strategies", [])
    if strategies:
        lines.append("## Learning Curves (Test EM at Full Pool)")
        lines.append("")
        lines.append("| Strategy | Full-Pool EM | Power-Law R^2 | Fit Status |")
        lines.append("|----------|-------------|---------------|------------|")
        for s in strategies:
            means = s.get("test_em_means", [])
            full_pool_em = means[-1] if means else 0
            pf = s.get("power_law_fit", {})
            r2 = pf.get("r_squared", "—")
            if isinstance(r2, float):
                r2 = f"{r2:.4f}"
            lines.append(
                f"| {s['strategy']} | {full_pool_em:.4f} | {r2} | {pf.get('status', '?')} |"
            )
        lines.append("")

    # Device profiles
    if device_summary:
        sessions = device_summary.get("sessions", [])
        sim_sessions = [s for s in sessions if "sim" in s.get("session_dir", "")]
        phys_sessions = [s for s in sessions if "sim" not in s.get("session_dir", "")]
        lines.append("## Device Profiles")
        lines.append("")
        lines.append(f"- Simulator sessions: {len(sim_sessions)}")
        lines.append(f"- Physical-device sessions: {len(phys_sessions)}")
        if sim_sessions:
            best = min(sim_sessions, key=lambda s: s.get("latency", {}).get("p50_ms", 9999))
            lat = best.get("latency", {})
            lines.append(f"- Best simulator p50: {lat.get('p50_ms', '?')} ms ({best.get('benchmark_records', '?')} iterations, Release)")
        if not phys_sessions:
            lines.append("- **Physical-device data: NOT YET AVAILABLE**")
        lines.append("")

    # Pareto
    pareto = analysis.get("pareto", {})
    points = pareto.get("points", [])
    if points:
        lines.append("## Pareto Summary")
        lines.append("")
        lines.append(f"- Points: {len(points)}")
        lines.append(f"- Status: {pareto.get('status', '?')}")
        for p in points:
            lat_str = f"{p['latency_p50_ms']} ms ({p['latency_environment']})" if p.get("latency_p50_ms") else "unavailable"
            lines.append(
                f"- {p['model_id']}: EM={p['quality_value']:.3f}, latency={lat_str}, size={p.get('artifact_size_mb', '?')} MB"
            )
        lines.append("")

    # Honest notes
    notes = analysis.get("overall_notes", [])
    if notes:
        lines.append("## Caveats")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    dst = output_dir / "results_snapshot.md"
    with open(dst, "w") as f:
        f.write("\n".join(lines))

    print(f"  [ok] results_snapshot.md ({len(lines)} lines)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper-ready assets")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "paper" / "assets" / "generated",
        help="Output directory for generated assets",
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=_PROJECT_ROOT / "results" / "analysis" / "phase6_v0",
        help="Analysis output directory to read from",
    )
    parser.add_argument(
        "--device-profiles-dir",
        type=Path,
        default=_PROJECT_ROOT / "results" / "device_profiles" / "analysis",
        help="Device profiles analysis directory",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building paper assets into: {args.output_dir}")
    print()

    # Load sources
    analysis = load_json(args.analysis_dir / "summary.json")
    device_summary = load_json(args.device_profiles_dir / "summary.json")

    if analysis is None:
        print("\nERROR: Phase 6 analysis summary.json not found. Run:")
        print("  python3 ml/scripts/run_statistical_analysis.py")
        sys.exit(1)

    ok_count = 0
    skip_count = 0

    # 1. Copy learning curves SVG
    if copy_learning_curves(args.analysis_dir, args.output_dir):
        ok_count += 1
    else:
        skip_count += 1

    # 2. Build model comparison CSV
    if build_model_comparison(analysis, args.output_dir):
        ok_count += 1
    else:
        skip_count += 1

    # 3. Build device profile summary CSV
    if device_summary and build_device_profile_summary(device_summary, args.output_dir):
        ok_count += 1
    else:
        skip_count += 1

    # 4. Build results snapshot
    if build_results_snapshot(analysis, device_summary, args.output_dir):
        ok_count += 1
    else:
        skip_count += 1

    print()
    print(f"Done: {ok_count} assets generated, {skip_count} skipped.")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
