# FIBER-GRAND Paper I — Phase 2C baseline exact-decoder gate

Generated: 2026-08-03T12:51:40+00:00

## Scientific decision

**GO_PAPER_I_BASELINE_EXACT_DECODER**

The baseline exact decoder passed correctness and demonstrated large, repeated codeword-likelihood savings together with a material exact-exhaustive wall-clock advantage.

This is a bounded evidence decision. It is not a conference acceptance, an absolute novelty determination, or authorization for a broader channel campaign.

## Exactness and execution

- Theorem-support checks: **PASS** (335146 exact cases).
- C++17 build/self-test: **PASS**.
- Preregistered trials: **996**; natural: 896; stress: 100.
- Validation violations: **0**.
- Complete deduplicated exact decodes: 996/996.
- Exhaustive exact-ML comparisons completed: 384.
- Complete branch-and-bound comparisons: 432.

## Main n=32 evidence

| cell_id | natural_trials | dedup_censor_fraction | median_q_membership | median_q_score | median_codeword_score_savings | p10_codeword_score_savings | median_codebook_membership_ratio | median_exhaustive_over_dedup_walltime | median_branch_over_dedup_walltime | bestpath_selected_disagreement_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| n32_k21_crc_defined_linear_R2_3 | 64 | 0 | 970.5 | 3 | 6.991e+05 | 1.907e+05 | 2161 | 522 | 0.9906 | 0.3906 |
| n32_k21_random_systematic_linear_R2_3 | 64 | 0 | 972 | 1.5 | 1.573e+06 | 2.621e+05 | 2158 | 465.6 | 1.665 | 0.2812 |
| n32_k24_crc_defined_linear_R3_4 | 64 | 0 | 964.5 | 4 | 4.194e+06 | 2.097e+06 | 1.739e+04 | -- | 1.204 | 0.4219 |
| n32_k24_random_systematic_linear_R3_4 | 64 | 0 | 966.5 | 4 | 4.194e+06 | 1.864e+06 | 1.736e+04 | -- | 2.394 | 0.5469 |
| n32_k26_extended_hamming_HAMMING | 64 | 0 | 954 | 13.5 | 4.978e+06 | 3.355e+06 | 7.034e+04 | -- | 2.18 | 0.6094 |

## Structural and practical interpretation

1. `codeword_score_savings` is the codebook size divided by the number of complete aggregate-likelihood evaluations. It directly measures avoided codeword-wise ML scoring, not a universal runtime ratio.
2. `codebook_membership_ratio` is the codebook size divided by distinct code-membership queries. Membership tests and complete likelihood evaluations are intentionally reported separately.
3. The history-pair and insertion-sphere generators return the same exact ML result. A reduction in generated hypotheses is useful only if it survives end-to-end overhead.
4. Exhaustive and branch-and-bound timings are code/implementation baselines, not claims of instance-optimality against every specialized decoder.
5. Best-path disagreement is reported separately from strict disjointness of the best-path and aggregate-ML tie sets.

## Finite-length theorem table

| n | p_s | delta | L_n | binomial_error_weight_quantile | certified_stop_shell | deduplicated_generated_cap | history_pair_generated_cap | exact_expected_membership_cap | h2_p |
|---|---|---|---|---|---|---|---|---|---|
| 16 | 0.05 | 0.01 | 1 | 3 | 3 | 9792 | 18432 | 902.2 | 0.2864 |
| 16 | 0.05 | 0.001 | 1 | 4 | 4 | 32997 | 62112 | 902.2 | 0.2864 |
| 24 | 0.05 | 0.01 | 2 | 4 | 5 | 1113800 | 2138496 | 8.261e+04 | 0.2864 |
| 24 | 0.05 | 0.001 | 2 | 5 | 6 | 3637475 | 6983952 | 8.261e+04 | 0.2864 |
| 32 | 0.05 | 0.01 | 2 | 5 | 6 | 31107417 | 60329536 | 1.724e+06 | 0.2864 |
| 32 | 0.05 | 0.001 | 2 | 6 | 7 | 117883392 | 228622336 | 1.724e+06 | 0.2864 |

## Decision gates

- Exact correctness: **yes**.
- Repeated n=32 query/score savings: **yes**.
- Exact exhaustive wall-clock calibration: **yes**.
- Deduplicated-generation wall-clock gate: **no**.
- Natural-channel completion gate: **yes**.

## Scope discipline

The expensive alignment-consistent `U_AC` certificate was already narrowed to a mathematical result in Phase 2B-R1. Phase 2C evaluates only the baseline shell-certified exact decoder, a classical insertion-sphere deduplication, best-path behavior, exhaustive codeword ML where feasible, and a generic exact branch-and-bound comparator. Multiple deletions, insertions, soft information, general transducers, code design, and hardware remain outside Paper I.

## Required review before writing claims

- independent proof review of the theorem source;
- updated novelty review against GRAND complexity theory, deletion-channel exact search, and correlated/threshold aggregation;
- claim-by-claim distinction between oracle/query complexity and wall-clock complexity.

## Files

- `theory/FIBER_GRAND_Phase2C_Baseline_Exact_Decoder_Theorems.tex`
- `theory/THEORY_CHECKS.json`
- `campaign/TRIAL_RESULTS.csv`
- `campaign/CELL_SUMMARY.csv`
- `campaign/STRESS_SUMMARY.csv`
- `campaign/VALIDATION_VIOLATIONS.json`
- `SCIENTIFIC_DECISION.json`
