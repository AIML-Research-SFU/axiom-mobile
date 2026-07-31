# Sweep v2: Real Trainable-Model Selection Sweep

The first selection-strategy sweep run against a real trainable model
(`axiom_lora_v1`), not the `question_lookup_v0` memorization heuristic
`sweep_v1_committed` used. Unblocked by fixing the MPS device-management
bug that caused this class of experiment to overheat a laptop in the
prior attempt (see `ml/src/axiom/models/tiny_multimodal.py`).

- 80 runs: 4 strategies (random, uncertainty, diversity, kg_guided) x
  4 budgets (50, 150, 300, 600) x 5 seeds
- Dataset: locally-regenerated auto-generated portion (699 examples,
  52 manual examples excluded -- see `docs/PRIVATE_DATA_SETUP.md` Option D)
- 20 epochs, class-weighted cross-entropy

See `results/analysis/selection_sweep_trainable_v1/summary.json` for
aggregate statistics (per-budget means, power-law fits, paired bootstrap
significance tests) and `paper/PAPER_DRAFT_v5.md` Section 6.2 for the
full writeup, including a real failure mode this sweep revealed that the
heuristic-only sweep could not: Uncertainty and Diversity selection
collapse to near-0% test EM through budget 300 -- a training failure,
not a generalization gap.
