# AXIOM-Mobile — SPEC

## Research Question and “Effective” Thresholds

**Research Question:**  
**What is the minimal training set size (k\*) that achieves effective domain reasoning on mobile devices under strict quality + latency + energy constraints?**

**Operational Definition of “Effective” (must satisfy all):**

- **Exact Match (EM):** ≥ 70% on a fixed held-out test set
- **Latency:** p50 ≤ 400 ms and p95 ≤ 600 ms per query (measured on device)
- **Energy:** < 5% battery drain per hour during continuous use (measured on device)
- **Model size:** < 100 MB total app footprint attributable to models + supporting data
- **Memory:** peak < 500 MB RAM during inference (measured on device)

---

## Experiment Grid

**Budgets:**  
**k = {10, 25, 50, 100, 250, 500}**

**Selection Strategies:**

- **RAND**
- **UNC**
- **DIV**
- **KG-guided**

---

## Deliverables

- **iOS/macOS testbed** (SwiftUI + Core ML) for on-device evaluation and CSV logging
- **Learning curves** and analysis identifying k\* per strategy under device constraints
- **6–8 page research paper** documenting method, experiments, results, and limitations
