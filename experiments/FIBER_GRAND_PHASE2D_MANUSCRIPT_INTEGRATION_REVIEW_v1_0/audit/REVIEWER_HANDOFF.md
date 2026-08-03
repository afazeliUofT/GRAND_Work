# External reviewer handoff

## What is being reviewed

A narrow conference candidate on exact ML decoding of arbitrary membership-testable binary codes under exactly one uniformly located deletion and independent BSC substitutions.

## Minimal review bundle

1. `manuscript/FIBER_GRAND_Paper_I_Conference_Candidate.pdf`
2. `supplement/FIBER_GRAND_Paper_I_Proof_Supplement.pdf`
3. `audit/EXTERNAL_PROOF_REVIEW_CHECKLIST.md`
4. `audit/CLAIM_NOVELTY_MATRIX.md`
5. `audit/RESULTS_CLAIM_CHECKLIST.md`
6. `frozen_evidence/` summaries exported from Phase 2C

## Questions for the reviewer

1. Are all theorems correct under the exact channel model and tie conventions?
2. Is any proposed contribution directly anticipated by primary prior work?
3. Is the query-complexity result substantial enough for ISIT, or should the work be positioned as an ITW paper?
4. Are the empirical claims correctly separated into query, scoring, generation, and wall-clock costs?
5. Which single change would most improve the paper without broadening the channel model?

## Required decision

Return one of:

- `ISIT_CANDIDATE`
- `ITW_CANDIDATE`
- `MAJOR_REVISION`
- `REJECT_CURRENT_CLAIMS`

The review must not certify novelty merely because no counterexample was found.
