# Speaker Notes -- AXIOM-Mobile Presentation

Target duration: ~15 minutes (roughly 45-50 seconds per slide).

---

## Slide 1: Title (30 seconds)

**Say**: "We're presenting AXIOM-Mobile, a research project investigating the minimal amount of training data needed to deploy effective domain reasoning on mobile devices. This is joint work by Annie Boltwood, Mahim Chaudhary, and Ariel Tyson for CMPT 416 at SFU."

**Emphasis**: The word "minimal" -- this is an efficiency question, not just an accuracy question.

---

## Slide 2: Problem / Motivation (1 minute)

**Say**: "Most users interact with computing primarily through their phones. When we want a model to reason about what's on screen -- answering questions about a UI screenshot, for example -- we need training data. But mobile deployment imposes hard constraints on latency, energy, memory, and model size. So there's a fundamental tension: quality usually demands more data and bigger models, but deployment demands the opposite."

**Transition**: "This tension leads directly to our research question."

---

## Slide 3: Research Question (1 minute)

**Say**: "We ask: what is k-star -- the minimum number of training examples needed for the model to be effective? And we define effective strictly: the model must simultaneously meet all six thresholds. It's not enough to be fast if accuracy is low, and it's not enough to be accurate if latency is unacceptable."

**Emphasis**: The joint definition of effectiveness. All six thresholds must be met simultaneously.

**Do not claim**: That we have answered this question. We have built the infrastructure to answer it.

---

## Slide 4: System Architecture (1 minute)

**Say**: "The system has two components. The iOS app is a SwiftUI testbed that loads Core ML models and runs inference with real-time latency measurement. The Python pipeline handles everything upstream: curating data, training models, running active-learning selection strategies, exporting to Core ML, and statistical analysis. The two connect through the exported model artifact."

**Emphasis**: End-to-end reproducibility -- every step is scripted.

---

## Slide 5: Dataset (45 seconds)

**Say**: "Our dataset consists of 52 screenshot-question-answer triples collected from real iOS applications, covering 24 answer classes. We use a frozen split: 37 examples in the training pool, 5 for validation, and 10 for test. The screenshots are private and stored off-repo. We currently have a single annotator; dual-annotator agreement is planned but not yet completed."

**Do not claim**: That the dataset is large enough. Acknowledge 52 is small.

---

## Slide 6: Models (45 seconds)

**Say**: "We evaluated two models. The first is a heuristic lookup baseline that memorizes question-to-answer mappings. The second is a 40-thousand-parameter CNN-plus-embedding model trained from scratch, which exports to a 96-kilobyte Core ML file. Both achieve about 10% test exact match. These models exist to validate the pipeline, not to represent our best possible accuracy."

**Emphasis**: "Pipeline validation, not final models." This framing is critical.

**Do not claim**: That 10% EM is a meaningful accuracy result on its own.

---

## Slide 7: Selection Strategies (45 seconds)

**Say**: "We implemented three active-learning selection strategies: random sampling, uncertainty-based selection using prediction entropy, and diversity-based selection using k-center greedy. A fourth strategy, guided by a knowledge graph, is blocked pending KG infrastructure. We ran a full sweep: three strategies, six budget levels, three random seeds -- 54 runs total."

**Transition**: "Let's look at what those 54 runs produced."

---

## Slide 8: Learning Curves (1 minute)

**Say**: "Here are the learning curves. The key finding is negative: all strategies converge to the same 10% exact match at full pool size, and the power-law fits have very low R-squared values. The uncertainty strategy is degenerate -- it produces all-zero predictions at every budget except the maximum. The conclusion is straightforward: with only 52 examples, there is not enough signal to differentiate strategies."

**Emphasis**: This is an honest negative result, not a failure. It tells us the dataset must grow.

**Do not claim**: That any strategy is better than another at this scale.

---

## Slide 9: On-Device Latency Results (1 minute)

**Say**: "For latency, we measured on a physical iPhone 15 Pro Max with an A17 Pro chip. In a cold-start session, the median latency was 14 milliseconds with a 95th percentile of 26 milliseconds. A warm session was comparable. The physical device is about seven times faster than the simulator in release mode. Both sessions pass all latency thresholds with a 28-times margin."

**Emphasis**: Physical device measurement, not simulator. The 28x margin means latency is not the bottleneck.

---

## Slide 10: Simulator vs Physical Device (45 seconds)

**Say**: "This table makes the simulator-versus-device gap concrete. The simulator in debug mode is roughly 14 times slower than the physical device. Even in release mode, the simulator is 7 times slower. This is why we report simulator numbers only as pipeline validation, never for threshold evaluation."

**Transition**: "Now let's see where we stand overall."

---

## Slide 11: Effectiveness Threshold Scorecard (1 minute)

**Say**: "Three of six thresholds pass: both latency targets and the model size target. Energy and memory are not yet measured -- we need Instruments traces for those. The quality threshold fails: 10% exact match versus the 70% target. This is the primary gap, and closing it requires both a larger dataset and a stronger model."

**Emphasis**: Honest accounting. Do not minimize the EM failure or overstate the latency success.

**Do not claim**: That passing 3/6 means the system is "mostly effective."

---

## Slide 12: Pareto View (30 seconds)

**Say**: "With only two model points, the Pareto frontier is trivial -- both are optimal by default. This view becomes meaningful once we add stronger models that trade off size and latency for accuracy."

**Transition**: Brief slide. Move to the demo.

---

## Slide 13: App Demo (1 minute)

**Say**: "The app supports the full workflow: import a screenshot, type a question, and get an answer with latency displayed in real time. Benchmark mode runs batch evaluation and exports results to CSV. The UI uses a glass-morphism design system with staggered animations, haptic feedback, and TipKit onboarding tips."

**If doing a live demo**: Walk through one screenshot import, one question, show the latency readout, then switch to benchmark mode briefly.

**If not doing a live demo**: Reference the demo flow document and show a screenshot of the app.

---

## Slide 14: Statistical Methods (45 seconds)

**Say**: "We use bootstrap confidence intervals with 10,000 resamples for all metric estimates, paired bootstrap for strategy comparisons, and power-law fits in log-log space for scaling analysis. Every output carries an explicit status label from a fixed vocabulary: complete, partial, blocked, or degenerate. This prevents us from accidentally presenting incomplete results as conclusions."

**Emphasis**: The status vocabulary -- this is a methodological contribution.

---

## Slide 15: Limitations (1 minute)

**Say**: "We want to be upfront about limitations. The quality gap is large -- 10% versus 70%. The dataset is small. The model has only 40 thousand parameters with no pretrained weights. We have a single annotator. Energy and memory are unmeasured. The KG-guided strategy is blocked. And three seeds per condition is not enough for reliable bootstrap intervals."

**Emphasis**: Read these as facts, not apologies. The pipeline is designed to address each one.

**Do not claim**: That these limitations are minor or easily fixed.

---

## Slide 16: Key Contributions (1 minute)

**Say**: "Despite the limitations, we make four contributions. First, a fully reproducible end-to-end pipeline from data curation through deployment and analysis. Second, physical-device latency evidence showing 14-millisecond inference on the A17 Pro. Third, an honest status tracking system that prevents overstatement. Fourth, infrastructure that is ready for stronger models and larger datasets without architectural changes."

**Emphasis**: Contributions are infrastructure and methodology, not accuracy claims.

---

## Slide 17: Next Steps (45 seconds)

**Say**: "Going forward, we plan to scale the dataset to at least 200 screenshots and 500 QA pairs, train a stronger model such as a LoRA-adapted vision-language model, collect Instruments traces for memory and energy, build the knowledge graph for KG-guided selection, and prepare the paper for submission."

**Transition**: "With that, we're happy to take questions."

---

## Slide 18: Thank You / Questions (open-ended)

**Say**: "Thank you. The repository is public on GitHub. We welcome questions."

---

# Handling Questions

## "Why is the EM so low?"

**Honest answer**: Two factors. The dataset has only 52 examples with 24 answer classes -- that is roughly 2 examples per class on average, which is not enough for generalization. The model is a 40-thousand-parameter network trained from scratch with no pretrained weights. Both the data scale and the model capacity need to increase.

**Do not say**: "It's just a baseline." Instead say: "The current model validates the pipeline. Reaching 70% EM requires a larger dataset and a stronger model, both of which the pipeline is designed to support."

## "Is 14ms a meaningful latency result?"

**Honest answer**: Yes, for two reasons. First, it confirms that the Core ML inference path works correctly on physical hardware. Second, it establishes that latency is not the binding constraint -- the 28x margin means we have substantial room to use a larger model before latency becomes a concern. But latency alone does not make the system effective; quality must improve.

## "Will you reach 70% EM?"

**Honest answer**: We believe so, but we cannot guarantee it with the current data. Reaching 70% EM will require scaling the dataset to at least 200-500 examples and using a model with pretrained visual features, such as a LoRA-adapted vision-language model. The pipeline is designed to support exactly this progression.

**Do not say**: "Definitely" or "Easily." The honest answer is "the infrastructure supports it, but we need to do the work."

## "What about energy and memory?"

**Honest answer**: We have not yet measured energy or memory on-device. These require Instruments Energy Log and Instruments Allocations traces, respectively. The benchmark infrastructure in the app is ready to collect this data; we simply have not completed those measurement sessions yet.

## "Why not use a bigger model?"

**Honest answer**: We deliberately started with a minimal model to validate the entire pipeline end-to-end: data curation, training, export, deployment, benchmarking, and analysis. Now that the pipeline is validated, the next step is to train a LoRA-adapted vision-language model, which the export and deployment infrastructure already supports.

## "How do you know 52 examples is too few?"

**Honest answer**: The learning curves show it. All three selection strategies converge to the same 10% EM, the power-law fits have very low R-squared, and the uncertainty strategy is degenerate. There is no signal to differentiate strategies, which means the dataset is below the threshold where active learning can demonstrate value.

## "Is this publishable?"

**Honest answer**: The infrastructure and methodology are solid. The empirical results are currently negative or partial. For a publication, we need to close the quality gap and complete the energy/memory measurements. The honest status tracking and reproducible pipeline are genuine contributions regardless of the final accuracy numbers.
