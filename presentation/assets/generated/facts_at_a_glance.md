# AXIOM-Mobile — Facts at a Glance

Generated for presentation use. All numbers from repo artifacts.

## Dataset
- **Total examples:** 52
- **Split:** pool=37, val=5, test=10
- **Answer classes:** 24
- **Target scale:** 200+ screenshots / 500+ QA pairs (not yet reached)

## Models
- **question_lookup_v0:** heuristic, pool EM=73.0%, test EM=10.0%
- **tiny_multimodal_v0:** 40K params, 96KB Core ML, test EM=10.0%
- **Quality target:** 70% EM — NOT MET

## Physical-Device Latency (iPhone 15 Pro Max, A17 Pro)
- **Session 1 (cold):** p50=14.0ms, p95=26.2ms, mean=18.0ms (50 iterations)
- **Session 2 (warm):** p50=14.5ms, p95=22.0ms, mean=16.8ms (50 iterations)
- **All latency thresholds:** PASS (28× below p50 limit)

## Simulator Comparison
- Best simulator p50: 98.0ms (Release)
- Physical device is ~7× faster

## Selection Strategies
- **3 strategies × 6 budgets × 3 seeds = 54 runs**
- All converge to 10% test EM at full pool
- No strategy differentiation detected (expected with tiny dataset)
- KG-guided: blocked pending KG v1

## Effectiveness Scorecard Summary
- EM ≥ 70%: **FAIL** (10%)
- Latency p50 ≤ 400ms: **PASS** (14.0ms)
- Latency p95 ≤ 600ms: **PASS** (26.2ms)
- Energy < 5%/hr: **UNAVAILABLE**
- Memory < 500MB: **UNAVAILABLE**
- Size < 100MB: **PASS** (96KB)
