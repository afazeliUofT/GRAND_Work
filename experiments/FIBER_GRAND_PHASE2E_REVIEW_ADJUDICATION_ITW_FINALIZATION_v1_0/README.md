# FIBER-GRAND Paper I - Phase 2E review adjudication and ITW finalization

This is a minimal, standalone scientific package produced after four independent reviews.

## Decision

`ITW_READY_AFTER_REVIEW_REPAIR`

The theorem chain is correct after two proof-writing repairs. The novelty claims are narrowed to the
explicit strict reversal family, the one-deletion+BSC unseen-shell bound, complete-tie exact
certification, the realization-dependent stopping theorem, and the original exact evidence. The
`h_2(p_s)` mechanism, discovery distance, aggregate-path principle, generic threshold, GRAND
membership interface, and insertion-sphere cardinality are treated as prior art or standard
consequences.

## Minimal contents

- `manuscript/FIBER_GRAND_Paper_I_ITW_Candidate_Phase2E.tex/.pdf`
- `supplement/FIBER_GRAND_Paper_I_Proof_Supplement_Phase2E.tex/.pdf`
- `reviews/REVIEW_ADJUDICATION_AND_RESPONSE.md`
- `reviews/VERIFIED_NOVELTY_MATRIX.md`
- `reviews/VERIFIED_PRIOR_ART.md`
- `reviews/source_reviews/` - exact four source reviews
- `evidence/FROZEN_PHASE2C_SUMMARY.json`
- `evidence/OCCUPANCY_BENCHMARK.csv`
- `run_phase2e.py` and `tests/` - no-simulation integrity and compilation gate

## No new simulation

Phase 2E performs exact algebraic regression checks, frozen-evidence checks, claim-discipline
checks, standalone LaTeX compilation, provenance, and Git handoff only. It does not rerun any
Phase-2C trial.
