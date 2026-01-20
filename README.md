# 🧠📱 **AXIOM-Mobile — Minimal Data for On‑Device Domain Reasoning**  
### *Selection Strategies • Learning Curves • Core ML Deployment • Real Device Profiling*

<p align="center">
  <img alt="AXIOM-Mobile Banner" src="https://dummyimage.com/1200x260/0b1020/ffffff&text=AXIOM-Mobile:+Minimal+Data+for+Mobile+Reasoning" />
</p>

<p align="center">
  <b>AXIOM-Mobile</b> is a research-driven iOS/macOS system + experiment that measures the <b>minimal dataset</b> required for effective domain reasoning <b>under real mobile constraints</b>.
</p>

<p align="center">
  <i>SwiftUI + Core ML on device • Python (PyTorch/Transformers/LoRA) for training • Reproducible learning curves</i>
</p>

---

## 🎯 **Research Question**
> **What is the minimal training set size (k\*) that achieves effective domain reasoning on mobile devices under strict quality + latency + energy constraints?**

### ✅ Operational Definition of “Effective”
A model is **effective** only if it satisfies **both** categories simultaneously:

**Quality Threshold**
- **≥ 70% Exact Match (EM)** on a held-out test set  
- Alternative metrics (task-dependent): **BLEU-4 ≥ 0.65**, **hit@5 ≥ 0.80**  
- **Hallucination rate < 10%** (answers must be grounded in visible content or KG)

**Device Constraints** *(measured on iPhone 14+ and M1/M2 Mac)*
- Latency: **p50 ≤ 400ms**, **p95 ≤ 600ms** per query  
- Energy: **< 5% battery drain per hour** during continuous use  
- Model size: **< 100MB** total app footprint (models + supporting data)  
- Memory: **Peak < 500MB RAM**

---

## 🧩 **What AXIOM-Mobile Builds**

### 🖥️ The System (On-Device App)
- **iOS/macOS app** using **SwiftUI + Core ML**  
- Captures/loads **screen content (screenshots)** and answers **natural language questions**  
- Uses **vision + text + compact knowledge graph grounding**  
- Runs **entirely on-device** with **zero network transmission**

### 🧪 The Experiment (Data-Efficiency Study)
We run a controlled scaling study:
1. Curate **500** high-quality screenshot-question-answer triples  
2. Train models on progressively larger subsets:  
   **k = {10, 25, 50, 100, 250, 500}**
3. Compare four selection strategies:  
   **RAND**, **UNC**, **DIV**, **KG-guided**  
4. Deploy each model to iPhone/Mac and measure:  
   **quality + latency + energy + memory** 
5. Identify **k\*** per strategy and determine which reaches **k\*** fastest 

---

## 🚀 **Key Features**

### 🧠 Data-Efficient Training
- **LoRA (PEFT)** fine-tuning for efficient adaptation
- **24 model variants** (4 strategies × 6 budgets), plus **multiple seeds** for rigor

### 🧭 Selection Strategies
| Strategy | Idea | Implementation Sketch |
|---|---|---|
| **RAND** | Uniform random sampling | Sample k from pool |
| **UNC** | Pick examples with highest uncertainty | Entropy / margin |
| **DIV** | Maximize coverage of feature space | k-center / clustering |
| **KG-guided** | Cover underrepresented KG regions | Entity/relation coverage |

(Defined explicitly in project methodology.)

### 📦 Core ML Deployment + Compression
- **PyTorch → Core ML (.mlpackage)** conversion
- Accept conversion only if **accuracy drop ≤ 3%** 
- **Post-training quantization** targeting ~4× size reduction 

### 📏 Real Device Profiling (Not Just Offline Metrics)
- Evaluate on **iPhone/Mac hardware** with airplane mode enabled 
- Log to **CSV** automatically for analysis
- Analyze learning curves with power-law fits and compare strategies statistically

---

## 🧰 **Installation**

### ✅ Python (Training + Evaluation)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e "ml[dev]"
```

> The repository does **not** store raw screenshots. See `data/README.md` for dataset handling and split manifests.

### ✅ iOS/macOS (App)
1. Open `app/AXIOMMobile.xcodeproj` (or `.xcodeworkspace`) in Xcode  
2. Select an iPhone simulator or your device  
3. Build + Run

---

## 🔎 **1) Prepare Dataset Manifests**
Dataset format follows a simple triple:
- screenshot → question → answer  
with optional metadata (bbox, difficulty, KG entities).

Expected (recommended) split proportions:  
- **Test 20%**, **Validation 10%**, **Pool 70%**  

**Example layout**
```
data/
  manifests/
    pool.jsonl
    val.jsonl
    test.jsonl
  schema/
    example.schema.json
```

---

## 🤖 **2) Train Models at Label Budget k**
Train one strategy at one budget (example):
```bash
python -m axiom.train \
  --strategy RAND \
  --k 50 \
  --seed 0 \
  --outdir results/runs/RAND_k50_seed0
```

Train the full sweep (24 configs):
```bash
python -m axiom.sweep \
  --strategies RAND,UNC,DIV,KG \
  --budgets 10,25,50,100,250,500 \
  --seeds 0,1,2 \
  --outdir results/runs
```

Outputs (per run):
- `metrics_offline.json`  
- `model_checkpoint/`  
- `export_coreml/AXIOMMobile.mlpackage`

---

## 📦 **3) Export to Core ML**
```bash
python -m axiom.export_coreml \
  --run results/runs/RAND_k50_seed0 \
  --outdir artifacts/coreml/RAND_k50_seed0
```

Acceptance gate:
- Export is accepted only if **accuracy drop ≤ 3%** after conversion

---

## 📱 **4) On-Device Evaluation (iPhone/Mac)**
AXIOM-Mobile measures on-device performance across **all models**: 
- **Exact Match, BLEU-4, hallucination rate, grounding accuracy**  
- **Latency p50/p95, peak memory, battery drain via Instruments**

The app writes a CSV like:
```
timestamp,device,model_id,strategy,k,seed,em,bleu,lat_p50_ms,lat_p95_ms,mem_peak_mb,battery_pct_per_hr
```

---

## 🧪 **5) Run Tests**
```bash
pytest -q
```

---

## 🗂️ **Project Structure**
```
axiom-mobile/
├── app/                      # SwiftUI + Core ML app (iOS/macOS)
│   └── AXIOMMobile/
├── ml/                       # Python package (training, selection, eval, export)
│   ├── src/axiom/
│   │   ├── data/
│   │   ├── selection/
│   │   ├── training/
│   │   ├── eval/
│   │   └── export/
│   └── scripts/
├── kg/                       # Compact KG (JSON/SQLite) embedded in app
├── data/                     # Manifests + schema (no raw screenshots)
├── results/                  # Run outputs (gitignored except README)
├── docs/                     # Spec, milestones, paper outline
└── README.md
```

---

## 🧭 **Roadmap (Semester Phases)**
- **Phase 1 (Weeks 1–4):** Dataset curation + QC (2 annotators, κ ≥ 0.75), KG assembly  
- **Phase 2 (Weeks 5–6):** Baseline model selection; verify constraints on device
- **Phase 3 (Weeks 7–10):** Implement selection strategies and train 24 models (+ seeds)  
- **Phase 4 (Weeks 11–12):** Compression + Core ML conversion + accuracy gate 
- **Phase 5 (Weeks 13–14):** On-device evaluation with Instruments logging
- **Phase 6 (Weeks 15–16):** Analysis + publication-quality write-up

---

## 🔐 Data Policy
- **No raw screenshots** are stored in Git.  
- Use `data/manifests/` + secure storage (private drive / DVC / S3) for images.  
- All on-device evaluation runs in **airplane mode** to preserve privacy and measurement validity.

---

## ✍️ Citation (Draft)
If you build on this work, please cite (placeholder):
```bibtex
@misc{axiom_mobile_2026,
  title        = {AXIOM-Mobile: Minimal Data for On-Device Domain Reasoning},
  author       = {Last Name, First Name},
  year         = {2026},
  howpublished = {GitHub repository}
}
```

---

## 📄 License
MIT License © 2026  
Annie Boltwood, Mahim Chaudhary & Ariel Tyson
