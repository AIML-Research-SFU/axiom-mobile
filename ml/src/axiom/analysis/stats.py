"""Statistical helper functions for Phase 6 analysis.

All methods use stdlib only (``random``, ``math``). No numpy/scipy required.

Design choices:
- Bootstrap confidence intervals instead of parametric assumptions,
  because sample sizes are tiny (3 seeds, 5–50 observations).
- Paired bootstrap for strategy comparisons instead of t-tests,
  because the independence and normality assumptions are dubious.
- Power-law fitting via log-log OLS only when the data is non-degenerate.
- Deterministic behaviour via explicit seed control.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from .schemas import AnalysisStatus, BootstrapInterval, PowerLawFit


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals
# ---------------------------------------------------------------------------


def bootstrap_ci(
    values: Sequence[float],
    *,
    statistic: str = "mean",
    ci_level: float = 0.95,
    n_bootstrap: int = 10_000,
    seed: int = 42,
) -> BootstrapInterval:
    """Compute a bootstrap confidence interval for a sample.

    Parameters
    ----------
    values : sequence of float
        The observed values.
    statistic : str
        One of ``"mean"`` or ``"median"``.
    ci_level : float
        Confidence level, e.g. 0.95 for 95%.
    n_bootstrap : int
        Number of bootstrap resamples.
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    BootstrapInterval
        Contains point estimate, CI bounds, and status.
    """
    n = len(values)
    if n == 0:
        return BootstrapInterval(
            metric_name=statistic,
            point_estimate=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            ci_level=ci_level,
            n_bootstrap=0,
            n_observations=0,
            status=AnalysisStatus.INSUFFICIENT_DATA,
            reason="No observations provided.",
        )

    if n == 1:
        val = float(values[0])
        return BootstrapInterval(
            metric_name=statistic,
            point_estimate=val,
            ci_lower=val,
            ci_upper=val,
            ci_level=ci_level,
            n_bootstrap=0,
            n_observations=1,
            status=AnalysisStatus.INSUFFICIENT_DATA,
            reason="Only 1 observation; CI is degenerate (point estimate only).",
        )

    rng = random.Random(seed)
    vals = list(values)

    def _stat(sample: list[float]) -> float:
        if statistic == "median":
            s = sorted(sample)
            mid = len(s) // 2
            if len(s) % 2 == 0:
                return (s[mid - 1] + s[mid]) / 2.0
            return float(s[mid])
        # mean
        return sum(sample) / len(sample)

    point = _stat(vals)

    boot_stats: list[float] = []
    for _ in range(n_bootstrap):
        resample = [rng.choice(vals) for _ in range(n)]
        boot_stats.append(_stat(resample))

    boot_stats.sort()
    alpha = 1.0 - ci_level
    lo_idx = max(0, int(math.floor((alpha / 2) * n_bootstrap)))
    hi_idx = min(n_bootstrap - 1, int(math.ceil((1 - alpha / 2) * n_bootstrap)) - 1)

    status = AnalysisStatus.COMPLETE
    reason = ""
    if n < 5:
        status = AnalysisStatus.PARTIAL
        reason = f"Only {n} observations; bootstrap CI may be unreliable."

    return BootstrapInterval(
        metric_name=statistic,
        point_estimate=round(point, 6),
        ci_lower=round(boot_stats[lo_idx], 6),
        ci_upper=round(boot_stats[hi_idx], 6),
        ci_level=ci_level,
        n_bootstrap=n_bootstrap,
        n_observations=n,
        status=status,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Paired bootstrap comparison
# ---------------------------------------------------------------------------


def paired_bootstrap_diff(
    values_a: Sequence[float],
    values_b: Sequence[float],
    *,
    ci_level: float = 0.95,
    n_bootstrap: int = 10_000,
    seed: int = 42,
) -> dict:
    """Paired bootstrap CI for the difference in means (A - B).

    Pairs are matched by index (e.g. same seed). If lengths differ,
    the comparison is skipped.

    Returns a dict with keys: mean_diff, ci_lower, ci_upper, ci_level,
    n_bootstrap, n_pairs, status, reason.
    """
    if len(values_a) != len(values_b):
        return {
            "mean_diff": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "ci_level": ci_level,
            "n_bootstrap": 0,
            "n_pairs": 0,
            "status": AnalysisStatus.SKIPPED,
            "reason": f"Unequal pair counts ({len(values_a)} vs {len(values_b)}); cannot pair.",
        }

    n = len(values_a)
    if n == 0:
        return {
            "mean_diff": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "ci_level": ci_level,
            "n_bootstrap": 0,
            "n_pairs": 0,
            "status": AnalysisStatus.INSUFFICIENT_DATA,
            "reason": "No paired observations.",
        }

    diffs = [float(a) - float(b) for a, b in zip(values_a, values_b)]
    mean_diff = sum(diffs) / len(diffs)

    if n < 2:
        return {
            "mean_diff": round(mean_diff, 6),
            "ci_lower": round(mean_diff, 6),
            "ci_upper": round(mean_diff, 6),
            "ci_level": ci_level,
            "n_bootstrap": 0,
            "n_pairs": n,
            "status": AnalysisStatus.INSUFFICIENT_DATA,
            "reason": "Only 1 pair; CI is degenerate.",
        }

    rng = random.Random(seed)
    boot_means: list[float] = []
    for _ in range(n_bootstrap):
        resample = [rng.choice(diffs) for _ in range(n)]
        boot_means.append(sum(resample) / len(resample))

    boot_means.sort()
    alpha = 1.0 - ci_level
    lo_idx = max(0, int(math.floor((alpha / 2) * n_bootstrap)))
    hi_idx = min(n_bootstrap - 1, int(math.ceil((1 - alpha / 2) * n_bootstrap)) - 1)

    status = AnalysisStatus.COMPLETE
    reason = ""
    if n < 5:
        status = AnalysisStatus.PARTIAL
        reason = f"Only {n} pairs; paired bootstrap may be unreliable."

    return {
        "mean_diff": round(mean_diff, 6),
        "ci_lower": round(boot_means[lo_idx], 6),
        "ci_upper": round(boot_means[hi_idx], 6),
        "ci_level": ci_level,
        "n_bootstrap": n_bootstrap,
        "n_pairs": n,
        "status": status,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Power-law fitting (log-log OLS)
# ---------------------------------------------------------------------------


def fit_power_law(
    x_values: Sequence[float],
    y_values: Sequence[float],
    *,
    min_points: int = 3,
    min_nonzero_y: int = 2,
) -> PowerLawFit:
    """Attempt a power-law fit y = a * x^b via log-log OLS.

    Skipped when:
    - Fewer than ``min_points`` data points.
    - Fewer than ``min_nonzero_y`` non-zero y values (degenerate curve).
    - Any x <= 0 (log undefined).

    Parameters
    ----------
    x_values, y_values : sequences of float
        The data to fit. Must be same length.
    min_points : int
        Minimum number of points required to attempt the fit.
    min_nonzero_y : int
        Minimum number of non-zero y values required.

    Returns
    -------
    PowerLawFit
        Includes status explaining whether the fit was performed.
    """
    xs = list(x_values)
    ys = list(y_values)

    if len(xs) != len(ys):
        return PowerLawFit(
            status=AnalysisStatus.SKIPPED,
            reason=f"x and y lengths differ ({len(xs)} vs {len(ys)}).",
        )

    if len(xs) < min_points:
        return PowerLawFit(
            status=AnalysisStatus.INSUFFICIENT_DATA,
            reason=f"Only {len(xs)} points; need >= {min_points} for power-law fit.",
            n_points=len(xs),
        )

    # Check for degenerate y (all zeros or near-zero)
    nonzero_y = sum(1 for y in ys if y > 1e-12)
    if nonzero_y < min_nonzero_y:
        return PowerLawFit(
            status=AnalysisStatus.DEGENERATE,
            reason=(
                f"Only {nonzero_y} non-zero y values out of {len(ys)}; "
                f"power-law fit is meaningless on a degenerate curve."
            ),
            n_points=len(xs),
        )

    # Filter to positive pairs only (log requires > 0)
    pairs = [(x, y) for x, y in zip(xs, ys) if x > 0 and y > 0]
    if len(pairs) < min_points:
        return PowerLawFit(
            status=AnalysisStatus.INSUFFICIENT_DATA,
            reason=(
                f"Only {len(pairs)} positive (x,y) pairs after filtering; "
                f"need >= {min_points}."
            ),
            n_points=len(pairs),
        )

    # Log-log OLS: log(y) = log(a) + b * log(x)
    log_x = [math.log(p[0]) for p in pairs]
    log_y = [math.log(p[1]) for p in pairs]
    n = len(pairs)

    mean_lx = sum(log_x) / n
    mean_ly = sum(log_y) / n

    ss_xx = sum((lx - mean_lx) ** 2 for lx in log_x)
    ss_xy = sum((lx - mean_lx) * (ly - mean_ly) for lx, ly in zip(log_x, log_y))

    if ss_xx < 1e-15:
        return PowerLawFit(
            status=AnalysisStatus.DEGENERATE,
            reason="All x values are identical; cannot compute slope.",
            n_points=n,
        )

    b = ss_xy / ss_xx
    log_a = mean_ly - b * mean_lx
    a = math.exp(log_a)

    # R-squared in log space
    ss_tot = sum((ly - mean_ly) ** 2 for ly in log_y)
    predicted = [log_a + b * lx for lx in log_x]
    ss_res = sum((ly - yhat) ** 2 for ly, yhat in zip(log_y, predicted))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-15 else 0.0

    # Residuals in original scale
    residuals = [y - a * (x ** b) for x, y in pairs]
    res_mean = sum(abs(r) for r in residuals) / len(residuals)

    return PowerLawFit(
        status=AnalysisStatus.COMPLETE,
        reason=f"Power-law fit on {n} points. R^2={r_squared:.4f} (log-space).",
        a=round(a, 6),
        b=round(b, 6),
        r_squared=round(r_squared, 6),
        residuals_mean=round(res_mean, 6),
        n_points=n,
    )


# ---------------------------------------------------------------------------
# Percentile helper (reused from device_profiles but stdlib-only)
# ---------------------------------------------------------------------------


def percentile(sorted_values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile on a pre-sorted sequence."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    k = (pct / 100.0) * (n - 1)
    f = int(math.floor(k))
    c = min(int(math.ceil(k)), n - 1)
    if f == c:
        return float(sorted_values[f])
    return float(sorted_values[f]) + (k - f) * float(sorted_values[c] - sorted_values[f])
