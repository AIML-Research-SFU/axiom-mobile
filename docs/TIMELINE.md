# AXIOM-Mobile Timeline and Progress Tracker

Last updated: 2026-04-13

This file tracks the 16-week project plan and marks what is complete based on the current repository state.

## Status Legend

- `[x]` Complete (verified in repo)
- `[~]` In progress / partially complete
- `[ ]` Not started or not verifiable from repo

## Quick Verification: Annie + Mahim Deliverables

### Annie (Step 1: schema + repo rules)

- `[x]` `data/schema/example.schema.json` exists and defines the dataset example format.
- `[x]` `data/README.md` exists with labeling and privacy rules.
- `[x]` `.gitignore` blocks raw screenshot/image files (`data/raw/`, `data/images/`, `*.png`, `*.jpg`, `*.jpeg`, `*.heic`, `*.webp`).
- `[ ]` Branch/PR workflow steps are not verifiable from local files alone.

### Mahim (Step 2: toy dataset + split + inspector)

- `[x]` `data/manifests/pool.jsonl`, `val.jsonl`, and `test.jsonl` are populated.
- `[x]` Dataset v2 freeze: 452 total examples (pool=382, val=30, test=40) with stratified splits covering 20 question types. v1 archived.
- `[x]` `ml/scripts/inspect_dataset.py` exists and validates required fields + split overlap.
- `[x]` `python3 ml/scripts/inspect_dataset.py` runs successfully on current manifests.
- `[x]` Shared private screenshot storage is now verifiable from Drive screenshots (`archive/`, `review/`, `screenshots_v0/`, `screenshots_v1/`).
- `[x]` The reviewed screenshot set has been copied into `screenshots_v1/` and the first dataset freeze is organized in Drive.
- `[ ]` Branch/PR workflow steps are not verifiable from local files alone.

## 16-Week Timeline (Planned vs Current State)

## Phase 0 (Week 0-1): Repo and Workflow Foundation

- `[x]` Data schema path exists: `data/schema/example.schema.json`.
- `[x]` Manifest files exist: `data/manifests/{pool,val,test}.jsonl`.
- `[x]` Dataset validation script exists: `ml/scripts/inspect_dataset.py`.
- `[x]` Annotation QC script exists: `ml/scripts/annotation_qc.py`.
- `[~]` Repo skeleton exists (`app/`, `ml/`, `kg/`, `results/`) but many components are placeholders.
- `[x]` CI workflows exist for repo guards, dataset validation, and annotation QC (`.github/workflows/guards.yml`, `.github/workflows/python-checks.yml`).

Deliverable status: `[x]` Complete (all verifiable items done; skeleton will fill in over later phases).

## Phase 1 (Weeks 1-4): Dataset Curation

- `[x]` Labeling protocol/rules documented (`data/README.md`).
- `[x]` Initial toy dataset created (10 examples total).
- `[x]` Splits are present (pool/val/test).
- `[x]` Shared Google Drive folder structure exists for private screenshots (`archive/`, `review/`, `screenshots_v0/`, `screenshots_v1/`).
- `[x]` Dataset has been expanded beyond the first 50-example checkpoint (52 manual + 75 auto-generated = 127 total examples in manifests).
- `[x]` The reviewed screenshots have been copied into `screenshots_v1/`.
- `[x]` The first reviewed dataset split is frozen at `pool=37`, `val=5`, `test=10`.
- `[x]` Annotation QC helper script exists and runs successfully on the frozen split.
- `[x]` Simulator-based screenshot automation harness: `scripts/capture_screenshots.sh` (simctl orchestrator, v0.2.0), `scripts/capture_scenarios.json` (20 deterministic scenarios), `ml/scripts/index_generated_screenshots.py` (candidate indexer with auto-promotion), `AXIOMMobileUITests` XCUITest target for fine-grained navigation. Documented in `docs/SCREENSHOT_AUTOMATION.md`.
- `[x]` Exact-answer scenario system: `scripts/generate_exact_scenarios.py` produces deterministic scenarios where every QA pair has a visually verified exact answer. Answers grounded in status bar state (time, battery%), charging indicator, Apple Account sign-in state, and Maps search bar text.
- `[x]` Promotion workflow with `auto_exact` / `needs_review` / `needs_labeling` classification. Auto-promote appends exact entries directly to pool.jsonl with rename mapping for private screenshot storage.
- `[x]` iOS 26 Settings layout discovery: Settings main screen no longer shows connectivity toggles (Airplane, Wi-Fi, Bluetooth). Scenario generator only emits questions about visually verified content.
- `[x]` **Dataset v2 freeze** (2026-04-13): 452 total examples (pool=382, val=30, test=40) with deterministic stratified split (seed=20260413). 400 auto-exact entries from 100 screenshots (batch `exact_v3_batch001`, 50 status bar variants x 2 apps). v1 manifests archived to `data/manifests/v1/` with SHA256 fingerprints. Freeze script: `ml/scripts/freeze_dataset_v2.py`.
- `[x]` Dataset target exceeded: 452 QA pairs from 152 unique source screenshots (52 manual + 100 auto-generated). Val/test now cover 9 question types each, including rare manual types (calculator, maps, bluetooth, etc.).
- `[ ]` Dual-annotator agreement workflow (Cohen's kappa >= 0.75) not implemented in repo.
- `[ ]` Bounding box grounding metadata pipeline not implemented.
- `[ ]` KG v1 (~1000 entities + API + app loader) not implemented yet.

Deliverable status: `[~]` In progress.

## Phase 2 (Weeks 5-6): Model Selection and Baseline

- `[x]` Initial model harness exists under `ml/src/axiom/models/` with a shared interface for `train()`, `predict()`, and `export_coreml()`.
- `[x]` Candidate model configs exist under `ml/configs/models/` for Florence, LLaVA Mobile, Qwen-VL INT4, and the executable local baseline (`question_lookup_v0`).
- `[x]` Baseline experiment runner exists (`ml/scripts/run_baseline.py`) and writes reproducible metrics/artifacts to `results/baselines/`.
- `[x]` Baseline results generated and committed (`results/baselines/question_lookup_v0_seed0/`); summary script and results note merged in PR #20.
- `[x]` Model selection rubric is documented in `docs/MODEL_SELECTION.md`.
- `[x]` SwiftUI testbed shell implemented with screenshot import, question input, model picker, run button, answer card, and debug metrics panel.
- `[x]` First real trainable multimodal baseline (`tiny_multimodal_v0`): image-root-aware data loading, PyTorch CNN+embedding model, checkpoint/vocab/architecture artifacts, training runner (`ml/scripts/run_trainable_baseline.py`). Documents Phase 4 export path in `docs/MODEL_SELECTION.md`.
- `[x]` Core ML baseline conversion pipeline implemented: `ml/scripts/export_coreml.py` with `torch.jit.trace` → `coremltools.convert` → `.mlpackage` + accuracy gate.

Deliverable status: `[x]` Complete (all Phase 2 items done; Core ML export pipeline now operational).

## Phase 3 (Weeks 7-10): Selection Strategies and Training Pipeline

- `[x]` Selection strategy interfaces (RAND/UNC/DIV/KG) implemented under `ml/src/axiom/selection/`.
- `[x]` Sweep runner (`ml/scripts/run_selection_sweep.py`) executes 3 strategies x 6 budgets x 3 seeds over the current baseline; KG-guided is honestly blocked pending KG v1.
- `[x]` Per-run JSON results + aggregate `summary.json` + `summary.csv` written to `results/selection_sweeps/`.
- `[x]` Selection strategies documented in `docs/SELECTION_STRATEGIES.md` with proxy rationale and limitations.
- `[x]` Learning curve generation script (`ml/scripts/generate_learning_curves.py`) produces aggregated JSON, CSV, and deterministic SVG plots; documented in `docs/LEARNING_CURVES.md`.
- `[x]` App benchmark mode with CSV logging hooks implemented; single-run and batch instrumentation with deterministic export format.
- `[ ]` KG-guided strategy blocked — requires KG v1 infrastructure (Phase 1 dependency).

Deliverable status: `[~]` In progress (KG-guided blocked on Phase 1 dependency; all other Phase 3 items complete).

## Phase 4 (Weeks 11-12): Compression and Core ML Conversion

- `[ ]` Quantization pipeline not implemented.
- `[x]` Automated PyTorch -> Core ML export pipeline: `ml/scripts/export_coreml.py` traces a trained checkpoint via `torch.jit.trace`, converts with `coremltools.convert`, and writes `.mlpackage` + `traced_model.pt` + `label_vocab.json` + `conversion_report.json`.
- `[x]` Post-conversion accuracy-drop gate (<= 3%): export script compares PyTorch vs Core ML predictions on val/test splits, reports per-split pass/fail with accuracy drop.
- `[x]` Private screenshot-root bootstrap: `ml/scripts/locate_screenshot_root.py` discovers `screenshots_v1/` on macOS; `docs/PRIVATE_DATA_SETUP.md` documents setup.
- `[x]` `export_coreml()` method implemented on `TinyMultimodalBaseline` (in `ml/src/axiom/models/tiny_multimodal.py`).
- `[x]` `coremltools>=8.0` added as `[export]` optional dependency in `ml/pyproject.toml`.
- `[x]` App integration for `.mlpackage` loading: `CoreMLInferenceService` loads bundled `TinyMultimodal.mlpackage` (96KB, 24 classes, trained on real 52-screenshot frozen dataset), preprocesses image+text, runs Core ML prediction, returns real `InferenceResult` with `isPlaceholder=false`. `TestbedViewModel` routes to real service when `isCoreMLReady` is true.
- `[x]` Model catalog updated: `tiny_multimodal_v0` is the first entry with `isCoreMLReady: true`, `backend: "coreml"`.
- `[x]` Benchmark pipeline distinguishes real vs placeholder inference via `isPlaceholder` field in CSV and `_meta.json`.

Deliverable status: `[x]` Complete (export pipeline, accuracy gate, and app integration all done; quantization deferred).

## Phase 5 (Weeks 13-14): On-Device Evaluation

- `[x]` Benchmark mode in app implemented with configurable iterations, progress tracking, and session summary.
- `[x]` Instruments profiling runbook: `docs/INSTRUMENTS_RUNBOOK.md` with reproducible protocol, pre-run checklist, output contract, and companion `_meta.json` session metadata export.
- `[x]` CSV logging with deterministic schema and share/export implemented; captures placeholder results now, ready for real Core ML metrics.
- `[x]` Device-profile ingestion and metric-summary pipeline: `ml/scripts/summarize_device_profiles.py` with typed schemas (`ml/src/axiom/results/device_profiles.py`), session folder contract, optional Instruments trace metrics sidecar, honest threshold evaluation, and analysis artifact outputs. Documented in `docs/DEVICE_PROFILES.md`.

- `[x]` First real profiling session captured: `tiny_multimodal_v0` on iPhone 17 Pro Simulator (iOS 26.4), 20 iterations, real Core ML inference (`is_placeholder: false`). Latency p50=199.5ms (PASS), p95=304.2ms (PASS).
- `[x]` Session staging script: `ml/scripts/stage_device_profile_session.py` copies app exports into `results/device_profiles/` following the documented session contract.
- `[x]` Auto-benchmark launch argument: `--auto-benchmark` triggers a headless benchmark session for repeatable profiling workflows.
- `[x]` Summarizer exercised on real session data: per-session JSON, aggregate `summary.json`, `summary.csv`, `summary.md` written to `results/device_profiles/analysis/`.
- `[x]` Benchmark-input hardening: `BenchmarkInputProvider` loads persisted real screenshot from Documents or generates a deterministic synthetic test pattern. Auto-benchmark now exercises the full image preprocessing pipeline (`image_loaded=true`) instead of using a blank input.
- `[x]` Second simulator session: 50-iteration Release build, synthetic test pattern input, p50=98.0ms (PASS), p95=112.8ms (PASS). Validates hardened benchmark path.
- `[x]` Simulator xctrace workflow validated: Time Profiler and Allocations traces captured via `xcrun xctrace record` with `--attach`. Traces are minimal on Simulator but confirm the tooling pipeline works for physical-device sessions.
- `[x]` Physical-device profiling sessions — AT-X (iPhone 15 Pro Max, A17 Pro, iOS 26.4.1): 2 sessions, 50 iterations each, real Core ML inference. Session 1 (cold): p50=14.0ms, p95=26.2ms. Session 2 (warm, with Time Profiler): p50=14.5ms, p95=22ms. All latency thresholds passed with wide margin.
- `[x]` Physical-device Instruments trace: Time Profiler captured on AT-X during 30s auto-benchmark session (3.6MB trace).

Deliverable status: `[x]` Complete (physical-device profiling done on AT-X with 2 sessions, Time Profiler trace captured, all latency thresholds pass).

## Phase 6 (Weeks 15-16): Analysis and Publication

- `[x]` Statistical analysis package: `ml/src/axiom/analysis/` with typed schemas (`schemas.py`) and stdlib-only statistical helpers (`stats.py`). Bootstrap CIs, paired bootstrap comparisons, power-law fitting with degenerate-data guards.
- `[x]` Analysis runner: `ml/scripts/run_statistical_analysis.py` ingests baselines, sweeps, CoreML exports, and device profiles. Writes JSON, CSV, Markdown, and SVG to `results/analysis/phase6_v0/`.
- `[x]` Honest status vocabulary: every result carries an explicit status (complete, partial, blocked, insufficient_data, simulator_only, physical_device_required, skipped, degenerate).
- `[x]` Simulator vs physical-device separation enforced in all device-profile analysis.
- `[x]` Documentation: `docs/STATISTICAL_ANALYSIS.md` covers methods, inputs, outputs, status vocabulary, and extension points.
- `[x]` Paper draft v1: `paper/PAPER_DRAFT_v1.md` — full research paper skeleton grounded in current repo results, with honest limitations throughout.
- `[x]` Paper asset generator: `ml/scripts/build_paper_assets.py` produces deterministic SVG, CSV, and Markdown assets from analysis outputs.
- `[x]` Demo flow script: `docs/DEMO_FLOW.md` — rehearsable 3-minute demo with interactive, auto-benchmark, and demo-mode paths.
- `[x]` Demo mode in app: `--demo-mode` launch argument sets up a single-shot inference with `tiny_multimodal_v0` for presentation-ready state.
- `[x]` Design system v0: `DesignSystem/` layer with semantic color, spacing, shape, typography, motion, and elevation tokens. Reusable components: `GlassCard`, `AXPrimaryButtonStyle`, `AXSecondaryButtonStyle`, `StatusBadge`, `SectionHeader`. All feature views refactored to consume tokens. Documented in `docs/DESIGN_SYSTEM.md`.
- `[x]` Testbed UI redesign: gradient background, glass cards with hierarchy levels, prominent CTA, status badges, collapsible debug section, dashed empty states, metric tiles in benchmark summary.
- `[x]` Design system v1 polish: custom app icon (1024×1024 programmatic + export script), branded launch screen, haptic feedback tokens (`AXHaptics`) mapped to 9 interaction points, staggered card entrance animations (`AXTransition`), iPad responsive layout (`AXLayout.axResponsiveContainer()`), light mode contrast refinement, TipKit onboarding (4 contextual tips).
- `[x]` Paper assets regenerated with physical-device data: device_profile_summary.csv (4 sessions), results_snapshot.md, Pareto view with real latency (14.0ms on A17 Pro).
- `[x]` Input-contract UX guardrail: domain hint in ScreenshotSection ("Import a mobile app screenshot"), AnswerCard footer explaining 24-class fixed vocabulary for tiny_multimodal_v0. Addresses out-of-domain input confusion without model changes.
- `[x]` Final presentation / slide deck: `presentation/SLIDE_DECK_v1.md` (18-slide Marp deck), `SPEAKER_NOTES.md`, `README.md`, and `ml/scripts/build_presentation_assets.py` deterministic asset generator. Paper advanced to `PAPER_DRAFT_v2.md` with physical-device latency data.

Deliverable status: `[x]` Complete.

## Next Practical Milestones

- `[x]` Expand manifests from 10 -> 50 examples while keeping question/answer quality constraints.
- `[x]` Add a reusable Python dataset module under `ml/src/axiom/data/` (loader + validation + split stats).
- `[x]` Freeze a balanced reviewed split for the first dataset checkpoint (`37/5/10` over 52 examples).
- `[x]` Add baseline CI workflows for Python checks and dataset QC.
- `[x]` Add Phase 2 scaffold for model selection, baseline execution, and result artifact writing.
- `[x]` Run baseline experiment and commit results + summary analysis (PR #20).

## Upcoming Work

- `[~]` Scale dataset to 200+ screenshots / 500+ QA pairs (Phase 1 completion). Current: 127 QA pairs from 72 unique screenshots. Next: extend XCUITest to Settings sub-pages, add more simulator apps when available, review/promote remaining candidates.
- `[x]` Build SwiftUI testbed shell for on-device testing.
- `[x]` Implement selection strategies (RAND/UNC/DIV) and sweep runner (Phase 3); KG-guided blocked pending KG v1.
- `[x]` Core ML export pipeline + accuracy gate (Phase 4) — `ml/scripts/export_coreml.py` with 96KB `.mlpackage` output.
- `[x]` App integration for `.mlpackage` loading (Phase 4 completion) — `CoreMLInferenceService` + bundled model in app.
- `[ ]` Quantization pipeline (Phase 4 compression — deferred; model is already 96KB).
- `[x]` Real profiling sessions on Simulator with `tiny_multimodal_v0` (Phase 5) — 20-iter Debug: p50=199.5ms; 50-iter Release: p50=98.0ms, both PASS.
- `[x]` Device-profile summarizer exercised on real session data (Phase 5).
- `[x]` Benchmark-input hardening: `BenchmarkInputProvider` with persisted/synthetic screenshot support; `image_loaded=true` for all iterations.
- `[x]` xctrace profiling workflow validated on Simulator (Time Profiler + Allocations).
- `[x]` Physical-device profiling on AT-X (iPhone 15 Pro Max, A17 Pro): 2 sessions × 50 iterations, p50=14.0ms/14.5ms, all thresholds pass.
- `[x]` Physical-device Time Profiler trace captured on AT-X (30s session, 3.6MB).
- `[x]` Phase 6: Statistical analysis package — bootstrap CIs, paired comparisons, power-law fits, Pareto views, reproducible outputs.
- `[x]` Phase 6: Paper draft v1 + demo flow + asset generator + `--demo-mode` launch argument.
- `[x]` Phase 6: Design system v1 — app icon, launch screen, haptic refinement, staggered transitions, iPad layout, light mode polish, TipKit onboarding.
- `[x]` Phase 6: Paper assets regenerated with physical-device data (4 sessions, Pareto view with real latency).
- `[x]` Phase 6: Input-contract UX guardrail for out-of-domain inputs.
- `[x]` Phase 6: Final presentation / slide deck — `presentation/SLIDE_DECK_v1.md`, speaker notes, generated assets, paper v2.
- `[x]` Exact-answer dataset scaling pipeline: scenario generator (v0.3.0, 50 variants), status bar variants, visually-verified promotion, 400 auto-exact entries promoted in batch `exact_v3_batch001`.
- `[x]` Dataset v2 freeze with deterministic stratified splits and SHA256 fingerprints. v1 manifests archived.
- `[ ]` Retrain model with expanded answer/task coverage (new label vocabulary needed: 24 → ~134 unique answers).
- `[ ]` Extend XCUITest for Settings sub-pages (General, Accessibility, etc.) and Maps navigation.
- `[ ]` Add dual-annotator agreement workflow (Cohen's kappa >= 0.75).
