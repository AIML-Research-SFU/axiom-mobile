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
- `[x]` App integration for `.mlpackage` loading: `CoreMLInferenceService` loads bundled `.mlpackage` and label vocab, preprocesses image+text, runs Core ML prediction, returns real `InferenceResult` with `isPlaceholder=false`. `TestbedViewModel` routes to real service when `isCoreMLReady` is true.
- `[x]` Model catalog updated: `tiny_multimodal_v1` is the default entry with `isCoreMLReady: true`; v0 remains available.
- `[x]` Model metadata sidecar system: per-model JSON files (`{model_id}_metadata.json`) bundle calibrated confidence threshold, class count, supported question types, and task summary. `InferenceResult`, `AnswerCard`, and `QuestionInputSection` consume metadata dynamically — no hardcoded class counts or thresholds.
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
- `[x]` `tiny_multimodal_v1` physical-device profiling — AT-X (iPhone 15 Pro Max, A17 Pro, iOS 26.4.1): 50 iterations, Release build, p50=14.5ms, p95=24.6ms. Negligible latency difference vs v0 (14.0ms), confirming that scaling from 24→128 output classes has no measurable cost on A17 Pro.
- `[x]` `tiny_multimodal_v1` simulator profiling — iPhone 17 Pro Sim (iOS 26.4): 50 iterations, Release build, p50=125.0ms.
- `[x]` Time Profiler trace captured for v1 on AT-X (15s session, 8.9MB).
- `[x]` Device-profile summarizer updated with 6 total sessions (3 simulator + 3 physical, spanning v0 and v1).

Deliverable status: `[x]` Complete (physical-device profiling done on AT-X for both v0 and v1, Time Profiler traces captured, all latency thresholds pass).

## Phase 6 (Weeks 15-16): Analysis and Publication

- `[x]` Statistical analysis package: `ml/src/axiom/analysis/` with typed schemas (`schemas.py`) and stdlib-only statistical helpers (`stats.py`). Bootstrap CIs, paired bootstrap comparisons, power-law fitting with degenerate-data guards.
- `[x]` Analysis runner: `ml/scripts/run_statistical_analysis.py` ingests baselines, sweeps, CoreML exports, and device profiles. Writes JSON, CSV, Markdown, and SVG to `results/analysis/phase6_v0/`.
- `[x]` Honest status vocabulary: every result carries an explicit status (complete, partial, blocked, insufficient_data, simulator_only, physical_device_required, skipped, degenerate).
- `[x]` Simulator vs physical-device separation enforced in all device-profile analysis.
- `[x]` Documentation: `docs/STATISTICAL_ANALYSIS.md` covers methods, inputs, outputs, status vocabulary, and extension points.
- `[x]` Paper draft v1: `paper/PAPER_DRAFT_v1.md` — full research paper skeleton grounded in current repo results, with honest limitations throughout.
- `[x]` Paper asset generator: `ml/scripts/build_paper_assets.py` produces deterministic SVG, CSV, and Markdown assets from analysis outputs.
- `[x]` Demo flow script: `docs/DEMO_FLOW.md` — rehearsable 3-minute demo with interactive, auto-benchmark, and demo-mode paths.
- `[x]` Demo mode in app: `--demo-mode` launch argument sets up a single-shot inference with the default Core ML model for presentation-ready state.
- `[x]` Design system v0: `DesignSystem/` layer with semantic color, spacing, shape, typography, motion, and elevation tokens. Reusable components: `GlassCard`, `AXPrimaryButtonStyle`, `AXSecondaryButtonStyle`, `StatusBadge`, `SectionHeader`. All feature views refactored to consume tokens. Documented in `docs/DESIGN_SYSTEM.md`.
- `[x]` Testbed UI redesign: gradient background, glass cards with hierarchy levels, prominent CTA, status badges, collapsible debug section, dashed empty states, metric tiles in benchmark summary.
- `[x]` Design system v1 polish: custom app icon (1024×1024 programmatic + export script), branded launch screen, haptic feedback tokens (`AXHaptics`) mapped to 9 interaction points, staggered card entrance animations (`AXTransition`), iPad responsive layout (`AXLayout.axResponsiveContainer()`), light mode contrast refinement, TipKit onboarding (4 contextual tips).
- `[x]` Paper assets regenerated with physical-device data: device_profile_summary.csv (6 sessions across v0+v1), results_snapshot.md, Pareto view with v1 data (27.5% EM, 14.5ms on A17 Pro).
- `[x]` Input-contract UX guardrail: domain hint in ScreenshotSection ("Import a mobile app screenshot"), AnswerCard footer with model-metadata-driven class count. No hardcoded 24-class text.
- `[x]` Presentation / slide deck: `presentation/SLIDE_DECK_v2.md` (updated Marp deck with v1+dataset-v2 facts), `SPEAKER_NOTES.md`, `README.md`, and `ml/scripts/build_presentation_assets.py` deterministic asset generator. Paper advanced to `paper/PAPER_DRAFT_v3.md` with v1 training results, dataset v2 facts, and v1 physical-device latency.
- `[x]` Evidence stack refresh: all analysis pipelines (`summarize_device_profiles.py`, `run_statistical_analysis.py`, `build_paper_assets.py`, `build_presentation_assets.py`) re-run with v1 data. Pareto frontier now shows v1 as strictly dominant over v0 (27.5% EM vs 10% at equivalent latency).

Deliverable status: `[x]` Complete.

## Next Practical Milestones

- `[x]` Expand manifests from 10 -> 50 examples while keeping question/answer quality constraints.
- `[x]` Add a reusable Python dataset module under `ml/src/axiom/data/` (loader + validation + split stats).
- `[x]` Freeze a balanced reviewed split for the first dataset checkpoint (`37/5/10` over 52 examples).
- `[x]` Add baseline CI workflows for Python checks and dataset QC.
- `[x]` Add Phase 2 scaffold for model selection, baseline execution, and result artifact writing.
- `[x]` Run baseline experiment and commit results + summary analysis (PR #20).

## Upcoming Work

- `[x]` Scale dataset beyond 200 examples: dataset v2 has 452 QA pairs from 152 unique screenshots (exceeds 200-screenshot target for QA pairs, not yet for unique screenshots).
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
- `[x]` Retrain model on dataset v2: `tiny_multimodal_v1` with 128 normalized answer classes, class-weighted CE loss, 40 epochs. Pool EM=30.9%, val EM=26.7%, test EM=27.5% (v0 was 16.2%/0%/10%).
- `[x]` Core ML export of v1: accuracy gate PASSED (0% drop on both val and test). 128-class `.mlpackage`.
- `[x]` Empirical confidence threshold calibration: correct predictions min confidence ~0.48, incorrect predictions mostly <0.15. Calibrated threshold: 0.45 (stored in model metadata sidecar, not hardcoded).
- `[x]` App integration of v1: `TinyMultimodalV1.mlpackage` + `tiny_multimodal_v1_labels.json` + `tiny_multimodal_v1_metadata.json` bundled. `CoreMLInferenceService` routes by model ID. `InferenceResult` reads threshold from metadata. `AnswerCard` and `QuestionInputSection` use `ModelMetadata` for dynamic copy. v1 is default model; v0 remains available.
- `[ ]` Extend XCUITest for Settings sub-pages (General, Accessibility, etc.) and Maps navigation.
- `[ ]` Add dual-annotator agreement workflow (Cohen's kappa >= 0.75).

## Semester 2 (Phases 7-13)

Last updated: 2026-07-29. Phases 1-6 above are semester 1 (through Paper Draft v3). This section tracks the semester 2 roadmap.

### Phase 7 (Dataset v3 scale-up) — Complete, committed (`0b13ec2`)

- `[x]` Extended `generate_exact_scenarios.py` to v0.4.0: 30 new variants x 2 apps x 5 QA (adds "How many cellular signal bars are shown?"), with a `--delta-only` mode so the already-promoted v0.3.0 base scenarios aren't re-captured/re-promoted as duplicates.
- `[x]` Investigated and rejected two candidate status-bar dimensions (wifi signal bars, carrier name) after visually confirming neither is reliably readable on this device — only shipped `cellular_bars`, which was.
- `[x]` Found and fixed a real bug in `capture_screenshots.sh`: per-scenario `cellular_bars` override was parsed but never applied.
- `[x]` Captured 60 new screenshots, 300 QA pairs, 0 skipped. Caught and removed 1 mislabeled example (a one-time "Enable Notifications" prompt covering the Maps search bar on the batch's first capture) via visual spot-check, not just pipeline trust.
- `[x]` `freeze_dataset_v3.py`: dataset v3 frozen at pool=681/val=30/test=40 (751 total), v2 archived with fingerprints.

### Phase 8 (Pretrained backbone + LoRA) — Complete, committed (`01ac454`)

- `[x]` De-risk spike: pretrained MobileNetV3-Small traces/converts via coremltools cleanly.
- `[x]` De-risk spike: pretrained transformer + LoRA text tower (bert-tiny, then all-MiniLM-L6-v2) attempted — fails at coremltools conversion, isolated (via a LoRA-removed control test) to the base transformer's traced graph, not LoRA-specific. Fell back to the roadmap's pre-registered plan B.
- `[x]` `axiom_lora_v1`: frozen pretrained MobileNetV3-Small backbone + genuine LoRA adapter (rank=8) on the final conv + unchanged char-level text encoder. Subclasses `TinyMultimodalBaseline` via a new `_build_net()` factory.
- `[x]` Real blocker found: committed dataset v3's original 452 images aren't on this machine (Drive not synced). Trained instead on a 699-QA machine-local recapture of the auto-generated portion of v3 — not committed, not the literal split.
- `[x]` CoreML export: accuracy gate passed, 0% drop, 2.04MB package.
- `[~]` Results are a wash vs `tiny_multimodal_v1` (30.0% vs 27.5% test EM, worse on val, different dataset) — reported honestly, not oversold. On-device latency only checked as a macOS-host proxy; real Simulator/device benchmarking needs Swift app integration, not done yet.

### Phase 9 (KG v1 + KG-guided strategy) — Complete, uncommitted

- `[x]` `ml/scripts/build_kg.py`: KG v1 extracted programmatically from dataset v3's own `notes`/`question`/`answer` fields — no manual curation. 235 entities (9 App, 19 Screen, 20 Attribute, 187 AnswerValue), 1,009 relations.
- `[x]` Found and fixed a real bug in the extraction logic before shipping: first-pass App/Screen parsing misclassified compound notes strings ("Bluetooth settings", "AirDrop tile") as standalone apps. Rewrote with explicit rules grounded in the actual 29 distinct notes prefixes in the dataset.
- `[x]` `kg_guided.py` implemented: round-robins across `(Screen, Attribute)` regions to maximize coverage breadth. Measured: 25/37 regions covered at budget=25 vs 11/37 for random sampling at the same budget.
- `[x]` Verified end to end: all 4 strategies (random/uncertainty/diversity/kg\_guided) run cleanly through the real sweep runner, 0 skipped.
- `[x]` `kg/README.md` (was empty) and `docs/SELECTION_STRATEGIES.md` updated.

### Phase 10 (Full selection sweep at scale) — Complete (heuristic baseline), trainable-model sweep deliberately abandoned

- `[x]` Found and fixed a real gap: `run_selection_sweep.py` never wired `image_root` through to trainable models — it had only ever been exercised with the heuristic baseline. Added `--image-root`/`--manifest-dir`/`--epochs`/`--class-weighted` CLI flags (kept — verified working, reusable infrastructure regardless of the scope decision below).
- `[x]` Full sweep on the **real committed dataset v3**: 4 strategies x budgets `{10,25,50,100,250,500}` x **10 seeds** (up from 3) x `question_lookup_v0`. 240 runs, 0 skipped, ~6.5 minutes. First-ever KG-guided results at scale on committed data.
- `[x]` Learning curves regenerated (`docs/LEARNING_CURVES.md` updated with real findings — e.g. random beats coverage-first strategies at tiny budgets for a memorization heuristic, but kg\_guided overtakes it by budget=50).
- `[x]` Attempted a matching sweep with `axiom_lora_v1` (real trainable model) on the local Phase 8 dataset (committed v3 images still unavailable — Drive sync gap). Calibrated real per-cell timing (~2.5 min worst case, ~4hr for the full grid), ran it, then parallelized across strategies + `caffeinate` to speed it up after sleep interruptions slowed the first attempt. **Abandoned partway through (50/240 runs) and deleted the partial results**: sustained multi-process training load made the laptop uncomfortably hot. Decided this class of experiment isn't worth running on personal laptop hardware — documented as a real, deliberate scope limitation in `docs/LEARNING_CURVES.md` and `docs/SELECTION_STRATEGIES.md`, not hidden or silently dropped.
- `[ ]` Not planned on this hardware going forward. Would need either a much smaller grid or non-laptop compute (e.g. a cloud/remote environment) to revisit.

### Phase 11 (Quantization + device profiling) — Complete except energy/memory (unreachable without a physical device)

- `[x]` `ml/scripts/quantize_coreml.py` (new): int8 post-training quantization via `coremltools.optimize`, same accuracy-gate discipline as export. `axiom_lora_v1`: 2.04MB -> 1.14MB (1.80x), 0% accuracy drop.
- `[x]` `axiom_lora_v1` bundled into the iOS app locally (mlpackage, labels, empirically-calibrated metadata sidecar), routed through `CoreMLInferenceService`, selectable in the picker but not made default (quality is a wash, not a win). Verified `*.mlpackage`/`*.mlmodel` are gitignored project-wide and even the existing `TinyMultimodalV1.mlpackage` (v0/v1) isn't tracked in git — this integration is exactly as real, and exactly as local-only, as every prior model integration in this project. Not a new gap; a pre-existing one, now documented.
- `[x]` Found and fixed a real bug while wiring this up: `TestbedViewModel.selectedModel` initialized from `ModelCatalog.all[0]` (array position) instead of the documented `defaultModelID` constant — adding a new picker entry first would have silently changed the real default.
- `[x]` Simulator latency profiling for `axiom_lora_v1`: p50=99.5ms (50 iter, Release, iPhone 17 Pro Sim) — labeled simulator_only, not publishable, consistent with this project's standing position.
- `[ ]` Allocations (memory) trace attempted via `xctrace record --attach`, hung across two bounded attempts, abandoned rather than burning more time on a flaky CLI interaction. Not a new gap — even Simulator memory was never considered meaningful by this project's own conventions.
- `[ ]` Energy: not measured, any model, any semester. Requires a physical device + Instruments Energy Log, unavailable on Simulator entirely (not just "not meaningful" — not present at all).
- **Near miss, caught before commit**: regenerating the device-profile aggregate summary after adding the new Simulator session would have silently dropped the real historical AT-X physical-device sessions (raw session folders are gitignored and were never on this machine). Reverted via `git checkout` before it could be committed.

### Phase 12 (Statistical rigor) — Complete for the heuristic-baseline sweep

- `[x]` Full statistical analysis re-run (`ml/scripts/run_statistical_analysis.py`) against the real Phase 10 sweep (240 runs) and the regenerated baselines.
- `[x]` **Three real bugs found and fixed** in the analysis pipeline itself: (1) hardcoded `sweep_v0` path silently ignored the real 240-run sweep; (2) Pareto view used a stale training-time size estimate instead of the measured CoreML export size; (3) memory status falsely reported "complete" by conflating "a trace sidecar exists" with "memory data exists." All three verified fixed and re-run clean.
- `[x]` Power-law fits improved (R^2 up to 0.49, from <0.2 in v3) with the larger budget range and 10 seeds — still not strong evidence of scaling, but real progress.
- `[x]` Pareto view now includes `question_lookup_v0`, `tiny_multimodal_v1` (regenerated), and `axiom_lora_v1` with real measured sizes: `axiom_lora_v1` is Pareto-dominated.
- `[ ]` `ml/scripts/build_paper_assets.py`/`build_presentation_assets.py` found to contain hardcoded/stale text in parts of their output (e.g. `facts_at_a_glance.md` claimed 54 sweep runs, blocked KG-guided, and 0% test EM — all wrong) that does not actually reflect the `--analysis-dir` data passed in. Documented as a known bug, **not fixed this pass** — paper v4 was hand-drafted from verified real numbers instead of trusting this generator's output.

### Phase 13 (Paper v4 + deck) — Complete

- `[x]` `paper/PAPER_DRAFT_v4.md`: full rewrite incorporating dataset v3, KG v1, the 240-run sweep, `axiom_lora_v1` (reported as a quality wash, not a win), quantization, Simulator profiling, and a dedicated section on the three analysis-pipeline bugs found this semester.
- `[x]` `presentation/SLIDE_DECK_v4.md` (new — `SLIDE_DECK_v3.md` already exists as a committed, differently-formatted deck from Ariel Tyson; used v4 to avoid overwriting a teammate's work).
- `[ ]` Energy/memory sections remain explicitly marked outstanding in both — not filled with placeholder or estimated numbers.
