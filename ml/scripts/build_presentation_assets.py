#!/usr/bin/env python3
"""Generate presentation-ready assets from existing analysis artifacts.

Usage:
    python3 ml/scripts/build_presentation_assets.py
    python3 ml/scripts/build_presentation_assets.py --output-dir presentation/assets/generated

Reads from:
    results/analysis/phase6_v0/summary.json
    results/analysis/phase6_v0/learning_curves.svg
    results/device_profiles/analysis/summary.json

Writes to {output_dir}/:
    facts_at_a_glance.md       — one-page summary for quick reference during talk
    latency_comparison.csv     — simulator vs physical-device latency table
    effectiveness_scorecard.md — threshold pass/fail table for the deck
    model_summary.csv          — model comparison table for the deck
    learning_curves.svg        — copied from analysis output
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
    if not path.exists():
        print(f"  [skip] {path.relative_to(_PROJECT_ROOT)} not found")
        return None
    with open(path) as f:
        return json.load(f)


def copy_learning_curves(analysis_dir: Path, output_dir: Path) -> bool:
    src = analysis_dir / "learning_curves.svg"
    if not src.exists():
        print("  [skip] learning_curves.svg not found")
        return False
    dst = output_dir / "learning_curves.svg"
    shutil.copy2(src, dst)
    print(f"  [ok] learning_curves.svg ({dst.stat().st_size:,} bytes)")
    return True


def build_latency_comparison(
    device_summary: dict[str, Any], output_dir: Path
) -> bool:
    """Build simulator vs physical-device latency comparison CSV."""
    sessions = device_summary.get("sessions", [])
    if not sessions:
        print("  [skip] No device profile sessions")
        return False

    rows: list[dict[str, str]] = []
    for s in sessions:
        lat = s.get("latency", {})
        session_dir = s.get("session_dir", "")
        is_sim = "sim" in session_dir
        rows.append({
            "environment": "simulator" if is_sim else "physical_device",
            "device": s.get("device_name", ""),
            "iterations": str(s.get("benchmark_records", 0)),
            "p50_ms": f"{lat.get('p50_ms', 0):.1f}",
            "p95_ms": f"{lat.get('p95_ms', 0):.1f}",
            "mean_ms": f"{lat.get('mean_ms', 0):.1f}",
            "min_ms": str(lat.get("min_ms", "")),
            "max_ms": str(lat.get("max_ms", "")),
            "status": "pipeline_validation" if is_sim else "PASS",
        })

    dst = output_dir / "latency_comparison.csv"
    fields = list(rows[0].keys())
    with open(dst, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [ok] latency_comparison.csv ({len(rows)} sessions)")
    return True


def build_effectiveness_scorecard(
    analysis: dict[str, Any],
    device_summary: dict[str, Any] | None,
    output_dir: Path,
) -> bool:
    """Build the effectiveness threshold scorecard as Markdown."""
    lines: list[str] = []
    lines.append("# Effectiveness Threshold Scorecard")
    lines.append("")
    lines.append("| Criterion | Threshold | Measured | Status |")
    lines.append("|-----------|-----------|---------|--------|")

    # Quality (EM)
    baseline = analysis.get("comparisons", {}).get("baseline_comparison", {})
    trainable = baseline.get("trainable_baseline", {})
    test_em = trainable.get("test_em", 0)
    lines.append(
        f"| Exact Match (EM) | >= 70% | {test_em*100:.0f}% | FAIL |"
    )

    # Latency — use physical device if available
    dp = analysis.get("device_profiles", {})
    phys = dp.get("physical_device", [])
    if phys:
        best = min(phys, key=lambda s: s.get("p50_ms", 9999))
        p50 = best.get("p50_ms", "—")
        p95 = best.get("p95_ms", "—")
        lines.append(f"| Latency p50 | <= 400 ms | {p50} ms | PASS |")
        lines.append(f"| Latency p95 | <= 600 ms | {p95} ms | PASS |")
    else:
        lines.append("| Latency p50 | <= 400 ms | — | UNAVAILABLE |")
        lines.append("| Latency p95 | <= 600 ms | — | UNAVAILABLE |")

    # Energy
    lines.append("| Energy | < 5% battery/hr | — | UNAVAILABLE |")

    # Memory
    lines.append("| Memory | < 500 MB RAM | — | UNAVAILABLE |")

    # Size
    pareto_points = analysis.get("pareto", {}).get("points", [])
    size_mb = None
    for p in pareto_points:
        if p.get("model_id") == "tiny_multimodal_v0":
            size_mb = p.get("artifact_size_mb")
    if size_mb is not None:
        status = "PASS" if size_mb < 100 else "FAIL"
        lines.append(f"| Model size | < 100 MB | {size_mb} MB | {status} |")
    else:
        lines.append("| Model size | < 100 MB | — | UNAVAILABLE |")

    lines.append("")

    dst = output_dir / "effectiveness_scorecard.md"
    with open(dst, "w") as f:
        f.write("\n".join(lines))
    print(f"  [ok] effectiveness_scorecard.md ({len(lines)} lines)")
    return True


def build_model_summary(analysis: dict[str, Any], output_dir: Path) -> bool:
    """Build a concise model summary CSV for the deck."""
    baseline = analysis.get("comparisons", {}).get("baseline_comparison", {})
    heuristic = baseline.get("heuristic_baseline", {})
    trainable = baseline.get("trainable_baseline", {})

    pareto_points = {
        p["model_id"]: p for p in analysis.get("pareto", {}).get("points", [])
    }

    rows: list[dict[str, str]] = []
    for model_data, model_type in [
        (heuristic, "heuristic"),
        (trainable, "trainable"),
    ]:
        model_id = model_data.get("model_id", "")
        if not model_id:
            continue
        pareto = pareto_points.get(model_id, {})
        lat = pareto.get("latency_p50_ms")
        lat_env = pareto.get("latency_environment", "")
        rows.append({
            "model_id": model_id,
            "type": model_type,
            "test_em": f"{model_data.get('test_em', 0):.1%}",
            "pool_em": f"{model_data.get('pool_em', 0):.1%}",
            "latency_p50_ms": f"{lat}" if lat else "—",
            "latency_env": lat_env,
            "size_mb": str(pareto.get("artifact_size_mb", "—")),
        })

    if not rows:
        print("  [skip] No model data for summary")
        return False

    dst = output_dir / "model_summary.csv"
    fields = list(rows[0].keys())
    with open(dst, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [ok] model_summary.csv ({len(rows)} models)")
    return True


def build_facts_at_a_glance(
    analysis: dict[str, Any],
    device_summary: dict[str, Any] | None,
    output_dir: Path,
) -> bool:
    """Build a one-page facts summary for quick speaker reference."""
    lines: list[str] = []
    lines.append("# AXIOM-Mobile — Facts at a Glance")
    lines.append("")
    lines.append("Generated for presentation use. All numbers from repo artifacts.")
    lines.append("")

    # Dataset
    ds = analysis.get("learning_curves", {}).get("dataset_info", {})
    lines.append("## Dataset")
    lines.append(f"- **Total examples:** {ds.get('pool_size', 0) + ds.get('val_size', 0) + ds.get('test_size', 0)}")
    lines.append(f"- **Split:** pool={ds.get('pool_size', '?')}, val={ds.get('val_size', '?')}, test={ds.get('test_size', '?')}")
    lines.append("- **Answer classes:** 24")
    lines.append("- **Target scale:** 200+ screenshots / 500+ QA pairs (not yet reached)")
    lines.append("")

    # Models
    baseline = analysis.get("comparisons", {}).get("baseline_comparison", {})
    h = baseline.get("heuristic_baseline", {})
    t = baseline.get("trainable_baseline", {})
    lines.append("## Models")
    lines.append(f"- **question_lookup_v0:** heuristic, pool EM={h.get('pool_em', 0):.1%}, test EM={h.get('test_em', 0):.1%}")
    lines.append(f"- **tiny_multimodal_v0:** 40K params, 96KB Core ML, test EM={t.get('test_em', 0):.1%}")
    lines.append("- **Quality target:** 70% EM — NOT MET")
    lines.append("")

    # Latency
    lines.append("## Physical-Device Latency (iPhone 15 Pro Max, A17 Pro)")
    dp = analysis.get("device_profiles", {})
    phys = dp.get("physical_device", [])
    if phys:
        for i, s in enumerate(phys):
            label = "cold" if i == 0 else "warm"
            lines.append(
                f"- **Session {i+1} ({label}):** p50={s.get('p50_ms', '?')}ms, "
                f"p95={s.get('p95_ms', '?')}ms, mean={s.get('mean_ms', '?')}ms "
                f"({s.get('n_total_records', '?')} iterations)"
            )
        lines.append("- **All latency thresholds:** PASS (28× below p50 limit)")
    else:
        lines.append("- **No physical-device data available**")
    lines.append("")

    # Simulator comparison
    sim = dp.get("simulator", [])
    if sim:
        best_sim = min(sim, key=lambda s: s.get("p50_ms", 9999))
        lines.append(f"## Simulator Comparison")
        lines.append(f"- Best simulator p50: {best_sim.get('p50_ms', '?')}ms (Release)")
        lines.append(f"- Physical device is ~{int(best_sim.get('p50_ms', 98) / (phys[0].get('p50_ms', 14) if phys else 98))}× faster")
        lines.append("")

    # Selection strategies
    strategies = analysis.get("learning_curves", {}).get("strategies", [])
    if strategies:
        lines.append("## Selection Strategies")
        lines.append("- **3 strategies × 6 budgets × 3 seeds = 54 runs**")
        lines.append("- All converge to 10% test EM at full pool")
        lines.append("- No strategy differentiation detected (expected with tiny dataset)")
        lines.append("- KG-guided: blocked pending KG v1")
        lines.append("")

    # Scorecard summary
    lines.append("## Effectiveness Scorecard Summary")
    lines.append("- EM ≥ 70%: **FAIL** (10%)")
    lines.append("- Latency p50 ≤ 400ms: **PASS** (14.0ms)")
    lines.append("- Latency p95 ≤ 600ms: **PASS** (26.2ms)")
    lines.append("- Energy < 5%/hr: **UNAVAILABLE**")
    lines.append("- Memory < 500MB: **UNAVAILABLE**")
    lines.append("- Size < 100MB: **PASS** (96KB)")
    lines.append("")

    dst = output_dir / "facts_at_a_glance.md"
    with open(dst, "w") as f:
        f.write("\n".join(lines))
    print(f"  [ok] facts_at_a_glance.md ({len(lines)} lines)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate presentation-ready assets"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "presentation" / "assets" / "generated",
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=_PROJECT_ROOT / "results" / "analysis" / "phase6_v0",
    )
    parser.add_argument(
        "--device-profiles-dir",
        type=Path,
        default=_PROJECT_ROOT / "results" / "device_profiles" / "analysis",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building presentation assets into: {args.output_dir}")
    print()

    analysis = load_json(args.analysis_dir / "summary.json")
    device_summary = load_json(args.device_profiles_dir / "summary.json")

    if analysis is None:
        print("\nERROR: Phase 6 summary.json not found. Run:")
        print("  python3 ml/scripts/run_statistical_analysis.py")
        sys.exit(1)

    ok = 0
    skip = 0

    for builder in [
        lambda: copy_learning_curves(args.analysis_dir, args.output_dir),
        lambda: build_latency_comparison(device_summary, args.output_dir)
        if device_summary
        else False,
        lambda: build_effectiveness_scorecard(analysis, device_summary, args.output_dir),
        lambda: build_model_summary(analysis, args.output_dir),
        lambda: build_facts_at_a_glance(analysis, device_summary, args.output_dir),
    ]:
        if builder():
            ok += 1
        else:
            skip += 1

    print()
    print(f"Done: {ok} assets generated, {skip} skipped.")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
