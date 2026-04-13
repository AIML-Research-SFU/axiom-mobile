# AXIOM-Mobile Presentation Slide Deck v3
## Optimized for PowerPoint Conversion

<!-- Global Design Direction:
- Theme: Dark background (#1A1A2E or #0F0F23) with white text
- Accent colors: Electric blue (#00D4FF) for highlights, coral (#FF6B6B) for FAIL/warnings, green (#4ECB71) for PASS
- Font: Title slides use bold sans-serif (e.g., Calibri Light or Segoe UI), body uses regular weight
- All slides: generous whitespace, no walls of text
- Charts: minimal gridlines, accent-colored data series on dark backgrounds
-->

---

## Slide 1 — Title

# AXIOM-Mobile
## Minimal Data for On-Device Domain Reasoning

- Annie Boltwood, Mahim Chaudhary, Ariel Tyson
- Simon Fraser University -- CMPT 416

<!-- Design: Full-bleed dark gradient background (#1A1A2E to #0F0F23). Title in large white bold text, subtitle in electric blue (#00D4FF). Author names and university in smaller light gray text at bottom. Consider a subtle geometric pattern or circuit-board motif in the background at low opacity. -->

<!-- Speaker Notes: Welcome everyone. Today we present AXIOM-Mobile, a research project investigating the minimum amount of training data needed to achieve effective on-device domain reasoning. This is joint work between Annie, Mahim, and myself for CMPT 416 at SFU. -->

---

## Slide 2 — The Problem

# The Mobile Reasoning Dilemma

- Mobile devices are the primary computing platform for billions of users
- Domain-specific reasoning (e.g., answering questions about screenshots) requires training data
- Mobile deployment imposes hard constraints: latency, energy, memory, model size
- **Core tension**: quality demands large datasets, but deployment demands small, fast models

<!-- Design: Split layout. Left side: icon of a phone with a brain/lightbulb (representing reasoning). Right side: icon of a stopwatch + battery (representing constraints). A large double-headed arrow or "vs" between them to visualize the tension. Use coral (#FF6B6B) for the constraint side, blue (#00D4FF) for the quality side. -->

<!-- Speaker Notes: The fundamental challenge is a tension between two competing demands. On one hand, achieving high-quality domain reasoning typically requires large datasets and powerful models. On the other hand, mobile deployment imposes strict physical constraints on latency, energy consumption, memory footprint, and model size. Our project investigates where these two pressures meet. -->

---

## Slide 3 — Research Question

# What is k*?

**The minimal training set size for effective on-device domain reasoning**

- "Effective" = passing ALL six thresholds simultaneously:

| Metric | Threshold |
|--------|-----------|
| Exact Match (EM) | >= 70% |
| Latency p50 / p95 | <= 400 ms / 600 ms |
| Energy | < 5% battery/hr |
| Memory | < 500 MB |
| Model size | < 100 MB |

<!-- Design: Large "k*" in electric blue at top, with a question mark motif. The table should be styled as a clean, dark-themed table with thin borders. Each row uses a small colored dot: green for hardware-type metrics, blue for quality. Keep the table compact on the right, with the "k*" question prominent on the left. -->

<!-- Speaker Notes: Our research question is precise: what is k-star, the minimum number of training examples needed to be effective? And we define effective rigorously -- a model must pass all six thresholds simultaneously. This is not just about accuracy. A model that scores 90% but takes 2 seconds per query on device would fail. We need quality, speed, efficiency, and compactness all at once. -->

---

## Slide 4 — Section Divider: System

# System

<!-- Design: Full-bleed dark slide with the word "System" in very large (72pt+), bold white text centered on screen. A thin electric blue horizontal line beneath the word. Subtle blueprint/schematic pattern in background at 5-10% opacity. -->

<!-- Speaker Notes: Let me walk you through the system we built to investigate this question. -->

---

## Slide 5 — System Architecture

# Two-Component Architecture

- **iOS Testbed App**: SwiftUI + Core ML inference engine
- **Python ML Pipeline**: data curation, training, CoreML export, analysis
- Automation via launch arguments enables reproducible benchmarking
- CSV export for offline statistical analysis

<!-- Design: Central diagram showing two rounded rectangles side by side. Left box labeled "iOS App" (blue accent) with sub-items: SwiftUI, Core ML, Benchmark Mode. Right box labeled "Python Pipeline" (coral accent) with sub-items: Training, Export, Analysis. Arrows flow between them: "CoreML model" arrow from Python to iOS, "CSV results" arrow from iOS to Python. Dark background. -->

<!-- Speaker Notes: The system has two components. First, a native iOS app built with SwiftUI and Core ML that serves as both a user-facing demo and a benchmark testbed. Second, a Python ML pipeline that handles everything from data curation through training, model export, and statistical analysis. The two connect through CoreML model files going to the device and CSV benchmark results coming back for analysis. Launch arguments let us automate benchmark runs for reproducibility. -->

---

## Slide 6 — iOS App Demo

# iOS App Highlights

- Screenshot import from Photos or camera
- Free-text question input with real-time Core ML inference
- Per-query latency display and benchmark mode with CSV export
- Design system: glass-morphism cards, animations, haptic feedback, TipKit onboarding

<!-- Design: Mockup or screenshot of the app on the right side of the slide (phone frame). Left side has the four bullet points. Use a subtle glow or shadow behind the phone mockup. If no screenshot is available, use a stylized phone outline with labeled UI zones. -->

<!-- Speaker Notes: The iOS app is more than a research prototype -- it has a polished design system with glass-morphism cards, staggered animations, and haptic feedback. Users can import screenshots, type a question, and get an answer with latency displayed in real time. The benchmark mode runs batch evaluations and exports results as CSV, which feeds directly into our analysis pipeline. We also integrated Apple's TipKit for onboarding. -->

---

## Slide 7 — Section Divider: Data & Models

# Data & Models

<!-- Design: Full-bleed dark slide with "Data & Models" in very large bold white text, centered. Thin electric blue line beneath. Subtle data-grid or scatter-plot pattern in background at 5-10% opacity. -->

<!-- Speaker Notes: Now let's talk about the datasets we curated and the models we trained. -->

---

## Slide 8 — Dataset Evolution

# 452
### Training Examples in Dataset v2

- **v1**: 52 examples, 24 classes -- initial pipeline validation
- **v2**: 452 examples, 128 classes -- current default
- 8.7x scale-up in examples, 5.3x in class diversity
- Frozen train/val/test splits per version for reproducibility

<!-- Design: The number "452" should be the hero element -- very large (120pt+), bold, electric blue, centered at top. Below it, a simple visual: two bars or circles showing v1 (small) and v2 (large) side by side with scale factors labeled. Bullet points below in smaller text. -->

<!-- Speaker Notes: We curated two dataset versions. Dataset v1 had just 52 examples across 24 classes and was used for initial pipeline validation and learning curve experiments. Dataset v2 scaled up dramatically to 452 examples and 128 classes -- an 8.7x increase in examples and 5.3x increase in class diversity. Both versions have frozen splits to ensure reproducibility. The screenshots are private and stored off-repo on Google Drive. Labels are currently single-annotator, with dual-annotator agreement via Cohen's kappa planned as future work. -->

---

## Slide 9 — Model Architecture

# Model: Tiny Multimodal (47K params)

- CNN image encoder processes screenshot features
- Text embedding encodes the natural-language question
- Features are concatenated and passed through a classifier head
- Output: probability distribution over 128 answer classes
- Entire model exports to CoreML at just 0.5 MB

<!-- Design: A flow diagram from left to right. Left: "Screenshot" icon -> "CNN Encoder" box. Below: "Question" icon -> "Text Embedding" box. Both arrows merge into a "Concat + Classifier" box. Right: "Answer" output. Use blue for the image path, coral for the text path, and green for the output. All on dark background. -->

<!-- Speaker Notes: Our model is intentionally small. It has roughly 47,000 parameters. A CNN processes the screenshot image, a text embedding encodes the question, and their features are concatenated before a classification head produces a distribution over 128 answer classes. The entire model converts to CoreML at just half a megabyte. This is by design -- we are exploring the lower bound of what minimal models can achieve, before scaling up to larger architectures. -->

---

## Slide 10 — v0 to v1 Results

# 2.75x
### EM Improvement from v0 to v1

| Model | Dataset | Params | Size | Test EM |
|-------|---------|--------|------|---------|
| question_lookup_v0 | v1 | -- | 0.1 MB | ~10% |
| tiny_multimodal_v0 | v1 | 40K | 96 KB | ~10% |
| tiny_multimodal_v1 | v2 | 47K | 0.5 MB | 27.5% |

- Improvement driven primarily by dataset scaling (52 -> 452 examples)
- Architecture change is minor (40K -> 47K params)

<!-- Design: Hero number "2.75x" in large bold electric blue at top, with an upward arrow icon. Clean table below with alternating subtle row shading. A small annotation arrow from v0 row to v1 row labeled "2.75x". -->

<!-- Speaker Notes: The jump from v0 to v1 is our first concrete evidence that dataset scaling improves quality within this architecture. Both v0 models scored around 10% exact match on their test sets. The v1 model, trained on the larger dataset v2, reaches 27.5% -- a 2.75x improvement. Importantly, the architecture barely changed; the gains come almost entirely from having more and more diverse training data. This is exactly the kind of scaling behavior our research question is designed to study. -->

---

## Slide 11 — Section Divider: Experiments

# Experiments

<!-- Design: Full-bleed dark slide with "Experiments" in very large bold white text, centered. Thin electric blue line beneath. Subtle chart/graph pattern in background at 5-10% opacity. -->

<!-- Speaker Notes: Let me now walk through our experimental methodology and learning curve analysis. -->

---

## Slide 12 — Selection Strategies

# Active Learning Selection Strategies

- **Random (RAND)**: Uniform sampling from the training pool
- **Uncertainty (UNC)**: Select examples with highest prediction entropy
- **Diversity (DIV)**: k-center greedy for maximum feature-space coverage
- **KG-guided**: Blocked pending Knowledge Graph v1

Sweep design: 3 strategies x 6 budgets x 3 seeds = **54 runs**

<!-- Design: Three colored icons or cards in a row representing RAND (dice icon, blue), UNC (question mark icon, coral), DIV (scatter-points icon, green). Below them, a fourth card for KG-guided shown grayed out with a lock icon. The sweep formula at the bottom in a highlight box. -->

<!-- Speaker Notes: We implemented three active learning selection strategies to study how data selection affects learning efficiency. Random sampling is our baseline. Uncertainty sampling picks the examples the model is least confident about. Diversity sampling uses k-center greedy to maximize coverage of the feature space. A fourth strategy, KG-guided, is planned but blocked on building the knowledge graph. Our sweep design crosses 3 strategies, 6 training budgets, and 3 random seeds for a total of 54 experimental runs. Note that all sweeps so far were conducted under the v0 dataset-v1 regime. -->

---

## Slide 13 — Learning Curves

# Learning Curves (Dataset v1)

- All strategies converge to ~10% EM at full pool size (37 examples)
- Power-law fits show low R-squared (0.17 diversity, 0.02 random)
- Uncertainty strategy: degenerate -- all-zero predictions except at budget = 37
- **Conclusion**: 52 examples insufficient for meaningful strategy differentiation

<!-- Design: A line chart placeholder on the right two-thirds of the slide. X-axis: "Training Budget (k)", Y-axis: "Test EM (%)". Three lines: blue for Random, coral for Uncertainty, green for Diversity. All converging near 10% at the right. Left third has the bullet points. Label the chart area with "[learning_curves.svg]" if embedding the actual chart. -->

<!-- Speaker Notes: The learning curves from our dataset v1 experiments are sobering but informative. All three strategies converge to roughly 10% exact match at full pool size. The power-law fits have very low R-squared values, meaning the curves don't follow clean scaling laws at this data scale. The uncertainty strategy was essentially degenerate -- producing all-zero predictions at every budget except the maximum. The key takeaway is that 52 examples are simply not enough to differentiate between selection strategies. This motivates our dataset v2 scaling and planned re-runs of the sweeps. -->

---

## Slide 14 — Section Divider: On-Device Results

# On-Device Results

<!-- Design: Full-bleed dark slide with "On-Device Results" in very large bold white text, centered. Thin electric blue line beneath. Subtle stopwatch or chip icon in background at 5-10% opacity. -->

<!-- Speaker Notes: Now for the results that matter most for our mobile deployment story -- actual physical device measurements. -->

---

## Slide 15 — Physical Device Latency

# 14 ms
### Median Inference Latency on iPhone 15 Pro Max

- **Device**: A17 Pro chip, iOS 26.4.1
- p50: 14.0 -- 14.5 ms across all sessions and models
- p95: 22.0 -- 26.2 ms (worst case)
- Latency threshold (400 ms) passed with **28x margin**

<!-- Design: Hero number "14 ms" in massive font (140pt+), bold, electric blue, top-center. Below: a horizontal bar chart showing the 400ms threshold as a long gray bar, with the 14ms actual as a tiny blue bar at the left end. This visually dramatizes the 28x margin. Device name in smaller text at bottom. -->

<!-- Speaker Notes: This is our headline hardware result. On an iPhone 15 Pro Max with the A17 Pro chip, our model achieves a median inference latency of just 14 milliseconds. The p95 latency -- meaning 95% of queries complete within this time -- is still only about 25 milliseconds. Our threshold was 400 milliseconds, so we pass with a 28x margin. This holds across both model versions and across cold-start and warm-cache sessions. The model is so small that there is essentially no performance difference between v0 and v1 on device. -->

---

## Slide 16 — Simulator vs Device

# Simulator vs Physical Device

| Environment | p50 | p95 | Status |
|-------------|-----|-----|--------|
| Simulator Debug (v0) | 199.5 ms | 304.2 ms | Pipeline validation only |
| Simulator Release (v0) | 98.0 ms | 112.8 ms | Pipeline validation only |
| Physical Device (v0) | 14.0 ms | 26.2 ms | PASS |
| Physical Device (v1) | 14.5 ms | 24.6 ms | PASS |

- Physical device is **7x faster** than simulator release builds
- Simulator numbers are for pipeline validation only -- never for thresholds

<!-- Design: Table with color-coded Status column: gray for "Pipeline validation only", green for "PASS". Consider a bar chart below the table showing the 7x gap visually. Simulator bars in gray, physical device bars in electric blue. -->

<!-- Speaker Notes: An important methodological point: simulator performance is dramatically different from physical device performance. The simulator in release mode shows about 98ms latency -- roughly 7x slower than the 14ms we measure on the actual device. Debug simulator builds are even worse at 200ms. This is why we insist on physical device measurements for threshold evaluation. Simulator runs are useful only for validating that the pipeline works end to end. Any paper reporting only simulator numbers for on-device claims would be misleading. -->

---

## Slide 17 — Effectiveness Scorecard

# 27.5%
### Current EM (Target: 70%)

| Metric | Target | v1 Result | Status |
|--------|--------|-----------|--------|
| Exact Match | >= 70% | 27.5% | FAIL |
| Latency p50 | <= 400 ms | 14.5 ms | PASS |
| Latency p95 | <= 600 ms | 24.6 ms | PASS |
| Energy | < 5%/hr | -- | UNAVAILABLE |
| Memory | < 500 MB | -- | UNAVAILABLE |
| Model size | < 100 MB | 0.5 MB | PASS |

<!-- Design: Hero number "27.5%" in large coral (#FF6B6B) to indicate it is the failing metric. Table below with color-coded Status: green for PASS, coral/red for FAIL, gray for UNAVAILABLE. Each status cell could have a small icon (checkmark, X, dash). Summary at bottom: "3/6 PASS | 1/6 FAIL | 2/6 UNAVAILABLE". -->

<!-- Speaker Notes: Here is the honest scorecard. Three of six thresholds pass convincingly -- latency p50, latency p95, and model size. Two thresholds -- energy and memory -- have not yet been measured; we need Apple Instruments profiling for those. The critical failure is quality: 27.5% exact match versus our 70% target. This is improved from 10% with v0, but still a large gap. Closing this gap is the primary focus of our next phase of work, likely requiring a stronger model architecture with a pretrained backbone. -->

---

## Slide 18 — Pareto View

# Pareto Frontier

| Model | EM | Latency p50 | Size |
|-------|-----|-------------|------|
| question_lookup_v0 | 10% | N/A | 0.1 MB |
| tiny_multimodal_v0 | 10% | 14.0 ms | 0.5 MB |
| tiny_multimodal_v1 | 27.5% | 14.5 ms | 0.5 MB |

- v1 is **Pareto-dominant** over v0: higher EM, equivalent latency and size
- Frontier becomes more meaningful as stronger models are added
- Next model will test whether quality can improve without breaking latency

<!-- Design: A scatter plot placeholder. X-axis: "Latency p50 (ms)", Y-axis: "Test EM (%)". Three points plotted. v1 is highlighted with a glow or larger marker. A dashed line showing the Pareto frontier connecting v1 upward. Optional: a ghost point at (14ms, 70%) labeled "target" to show where we need to reach. -->

<!-- Speaker Notes: Looking at the Pareto frontier across our model variants, v1 strictly dominates v0 -- it achieves higher quality at essentially the same latency and model size. The lookup baseline lacks a latency measurement so it remains technically non-dominated, but it is clearly inferior. The interesting question going forward is whether we can push the EM upward toward 70% without breaking through the latency ceiling. If a stronger model can hit, say, 50 or 60% EM while staying under 400ms, that would be a much more interesting Pareto frontier to analyze. -->

---

## Slide 19 — Section Divider: Discussion

# Discussion

<!-- Design: Full-bleed dark slide with "Discussion" in very large bold white text, centered. Thin electric blue line beneath. -->

<!-- Speaker Notes: Let me wrap up with our key contributions, honest limitations, and next steps. -->

---

## Slide 20 — Key Contributions

# Key Contributions

1. **End-to-end reproducible pipeline**: data curation through deployment and analysis
2. **Physical-device latency evidence**: 14 ms p50 on A17 Pro, 28x below threshold
3. **Honest status tracking**: explicit vocabulary prevents overstatement of partial results
4. **Scalable infrastructure**: supports stronger models and larger datasets without changes
5. **Dataset v2**: 52 to 452 examples, 24 to 128 classes
6. **v1 model with 2.75x EM lift**: first evidence that dataset scaling improves quality

<!-- Design: Six items in a 2x3 grid of cards on a dark background. Each card has a small icon (gear, stopwatch, checkmark, expand arrows, database, chart-up) and a short title in bold with one line of detail. Use subtle card backgrounds (#1E1E3F) with thin blue borders. -->

<!-- Speaker Notes: We want to highlight six contributions. First, the pipeline is fully reproducible from data curation through training, CoreML export, on-device benchmarking, and statistical analysis. Second, we have real physical device measurements showing 14ms inference, not simulator estimates. Third, we developed an honest status vocabulary -- every result is labeled as complete, partial, blocked, or degenerate, which prevents accidental overstatement. Fourth, the infrastructure is designed to scale -- plugging in a stronger model or larger dataset requires no architectural changes. Fifth, we demonstrated that scaling from dataset v1 to v2 is tractable. And sixth, the 2.75x EM improvement from v0 to v1 is our first empirical evidence that more data helps within this architecture. -->

---

## Slide 21 — Limitations

# Limitations

- **Quality gap**: 27.5% EM vs 70% target -- large distance remains
- **Model capacity**: 47K params with no pretrained backbone
- **Single annotator**: no inter-annotator agreement measured yet
- **Energy/memory**: not yet profiled via Instruments
- **Selection sweeps**: only conducted on v1 dataset (52 examples)
- **Statistical power**: 3 seeds per condition limits confidence interval reliability

<!-- Design: Clean list on dark background. Each bullet has a small yellow/amber warning icon. Text in white, key phrases in coral. Keep this slide visually restrained -- it should feel honest, not alarming. -->

<!-- Speaker Notes: We want to be transparent about limitations. The biggest is the quality gap -- we are still 42.5 percentage points below our EM target. Our model is intentionally tiny with no pretrained features, which limits its ceiling. We have only one annotator so far, meaning we cannot report inter-annotator agreement. Energy and memory thresholds are unmeasured. Our selection strategy sweeps used only the small v1 dataset, and with only 3 seeds per condition, our bootstrap confidence intervals are unreliable. Each of these is a concrete item on our roadmap. -->

---

## Slide 22 — Next Steps

# Next Steps

- Train a stronger model (LoRA-adapted VLM or equivalent) to close the EM gap
- Build Knowledge Graph v1 for KG-guided selection strategy
- Re-run selection strategy sweeps on dataset v2 (452 examples)
- Collect Apple Instruments traces for energy and memory thresholds
- Format and submit paper to target venue

<!-- Design: A vertical timeline or roadmap graphic on the right side, with five milestone nodes connected by a line. Each node has a short label. Left side has the bullet text. Use blue for the timeline line, with white node circles. -->

<!-- Speaker Notes: Looking ahead, the highest priority is closing the quality gap by training a stronger model -- likely using a LoRA-adapted vision-language model with a pretrained backbone. In parallel, we need to build the knowledge graph infrastructure to enable KG-guided data selection. We also plan to re-run all selection strategy sweeps on the larger dataset v2 where we expect to see meaningful differentiation between strategies. On the measurement side, we need Instruments profiling for energy and memory. Finally, we are working toward formatting and submitting the paper to our target venue. -->

---

## Slide 23 — Thank You

# Thank You

**Repository**: github.com/arieltyson/axiom-mobile

Annie Boltwood, Mahim Chaudhary, Ariel Tyson
Simon Fraser University -- CMPT 416

Questions?

<!-- Design: Dark gradient background matching the title slide. "Thank You" in large white bold text. Repository link in electric blue, underlined. Author names and university in light gray. Consider adding a QR code graphic placeholder on the right side that links to the GitHub repo. Subtle geometric pattern matching Slide 1. -->

<!-- Speaker Notes: Thank you for your attention. The full codebase, including the iOS app, Python pipeline, and all analysis scripts, is available on GitHub. We welcome questions about the methodology, results, or next steps. -->
