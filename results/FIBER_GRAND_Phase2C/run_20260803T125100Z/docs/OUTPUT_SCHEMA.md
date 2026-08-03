# Output schema

## Root

- `PHASE2C_REPORT.json`, `PHASE2C_REPORT.md`: consolidated result and interpretation.
- `SCIENTIFIC_DECISION.json`: preregistered bounded decision.
- `RUN_STATUS.json`: execution/correctness status, distinct from scientific significance.
- `MANIFEST.sha256`: result manifest before local return ZIP creation.

## Theory

- `theory/FIBER_GRAND_Phase2C_Baseline_Exact_Decoder_Theorems.tex`
- `theory/THEORY_CHECKS.json`
- `THEORY_FINITE_LENGTH_TABLE.csv`

## Campaign

- `campaign/TRIAL_SPECS.csv`: frozen trial metadata and code definitions.
- `campaign/CPP_INPUT.tsv`, `campaign/CPP_OUTPUT.tsv`: exact compiled input/output contract.
- `campaign/TRIAL_RESULTS.csv`: merged trial-level evidence.
- `campaign/CELL_SUMMARY.csv`: natural-channel cell statistics.
- `campaign/STRESS_SUMMARY.csv`: forced-error-weight summaries.
- `campaign/VALIDATION_VIOLATIONS.json`: all exact invariant failures; expected count zero.
- `campaign/CAMPAIGN_REPORT.json`: execution summary.

Key fields:

- `dedup_q_membership`: distinct code-membership queries;
- `dedup_q_score`: complete aggregate-likelihood evaluations;
- `codeword_score_savings`: `2^k / dedup_q_score`;
- `codebook_membership_ratio`: `2^k / dedup_q_membership`;
- `history_over_dedup_walltime`: paired exact generation timing;
- `exhaustive_over_dedup_walltime`: completed exhaustive calibration timing;
- `branch_over_dedup_walltime`: completed branch-and-bound calibration timing;
- `bestpath_selected_disagreement`: selected best-path representative differs from selected aggregate-ML representative;
- `bestpath_strict_disjoint`: the two complete tie sets are disjoint.
