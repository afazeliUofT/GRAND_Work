# Exact next step after execution

Do not launch a larger Monte Carlo campaign automatically.

1. Confirm `RUN_STATUS.json` and `validation/exact_validation_summary.json` are PASS.
2. Inspect `pilot/SCREENING_DECISION.json`, but treat it only as a screening label.
3. Review `paired_trials.csv`, `cell_summary.csv`, `schedule_summary.csv`, and the bound overhead fields together.
4. Return the Git branch, commit hash, and result directory for scientific review.
5. Authorize later work only after a human verdict:
   - correctness failure: stop and repair the smallest counterexample;
   - material bound reduction but dominant overhead: one focused optimization/theorem step only;
   - repeated search-work and wall-clock gains: expand to the pre-registered tail campaign;
   - negligible gain: stop the algorithmic route rather than adding more channel cases.
