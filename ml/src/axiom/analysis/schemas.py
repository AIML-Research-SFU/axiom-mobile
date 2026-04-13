"""Typed schemas for Phase 6 statistical analysis outputs.

Every analysis result carries an explicit ``status`` field from a fixed
vocabulary so downstream consumers (paper draft, presentation) can never
accidentally overstate what the data supports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------

class AnalysisStatus:
    """Fixed vocabulary for analysis result statuses."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    INSUFFICIENT_DATA = "insufficient_data"
    SIMULATOR_ONLY = "simulator_only"
    PHYSICAL_DEVICE_REQUIRED = "physical_device_required"
    SKIPPED = "skipped"
    DEGENERATE = "degenerate"


# ---------------------------------------------------------------------------
# Bootstrap / interval schemas
# ---------------------------------------------------------------------------


@dataclass
class BootstrapInterval:
    """A bootstrap confidence interval for a metric."""

    metric_name: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    ci_level: float  # e.g. 0.95
    n_bootstrap: int
    n_observations: int
    status: str  # AnalysisStatus value
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Learning-curve / scaling analysis
# ---------------------------------------------------------------------------


@dataclass
class PowerLawFit:
    """Result of attempting a power-law fit y = a * x^b."""

    status: str  # complete | skipped | degenerate | insufficient_data
    reason: str
    a: float | None = None
    b: float | None = None
    r_squared: float | None = None
    residuals_mean: float | None = None
    n_points: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class StrategyCurve:
    """Aggregated learning curve for one strategy."""

    strategy: str
    budgets: list[int]
    test_em_means: list[float]
    test_em_cis: list[dict[str, Any]]  # per-budget bootstrap CIs
    val_em_means: list[float]
    power_law_fit: dict[str, Any]
    status: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearningCurveAnalysis:
    """Complete learning-curve analysis across all strategies."""

    status: str
    reason: str
    strategies: list[dict[str, Any]]
    dataset_info: dict[str, Any]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Strategy comparison
# ---------------------------------------------------------------------------


@dataclass
class PairedComparison:
    """Result of comparing two strategies via paired resampling."""

    strategy_a: str
    strategy_b: str
    metric: str
    budget: int
    mean_diff: float  # A - B
    ci_lower: float
    ci_upper: float
    ci_level: float
    n_bootstrap: int
    n_seeds: int
    status: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonAnalysis:
    """All strategy comparisons."""

    status: str
    reason: str
    baseline_comparison: dict[str, Any]
    pairwise_comparisons: list[dict[str, Any]]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Device-profile analysis
# ---------------------------------------------------------------------------


@dataclass
class LatencyAnalysis:
    """Latency analysis for a specific environment."""

    environment: str  # "simulator" | "physical_device"
    model_id: str
    n_sessions: int
    n_total_records: int
    p50_ms: float
    p95_ms: float
    mean_ms: float
    min_ms: int
    max_ms: int
    bootstrap_ci_p50: dict[str, Any] | None
    threshold_evaluations: list[dict[str, Any]]
    status: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeviceProfileAnalysis:
    """Complete device-profile analysis separating simulator and physical."""

    status: str
    reason: str
    simulator: list[dict[str, Any]]
    physical_device: list[dict[str, Any]]
    memory_status: str
    memory_reason: str
    energy_status: str
    energy_reason: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pareto analysis
# ---------------------------------------------------------------------------


@dataclass
class ParetoPoint:
    """A single point on a quality-vs-efficiency Pareto chart."""

    model_id: str
    quality_metric: str
    quality_value: float
    latency_p50_ms: float | None
    latency_environment: str  # "simulator" | "physical_device" | "unavailable"
    artifact_size_mb: float | None
    is_pareto_optimal: bool
    status: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParetoAnalysis:
    """Pareto-style quality vs efficiency analysis."""

    status: str
    reason: str
    points: list[dict[str, Any]]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Top-level analysis summary
# ---------------------------------------------------------------------------


@dataclass
class Phase6Analysis:
    """Complete Phase 6 statistical analysis summary."""

    analysis_id: str
    created_at_utc: str
    version: str
    learning_curves: dict[str, Any]
    comparisons: dict[str, Any]
    device_profiles: dict[str, Any]
    pareto: dict[str, Any]
    overall_status: str
    overall_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
