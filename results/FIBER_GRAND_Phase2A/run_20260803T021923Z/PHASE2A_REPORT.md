# FIBER-GRAND Paper I — Phase 2A bounded-gate report

Generated: 2026-08-03T02:20:04+00:00

## Automated screening label

**NARROW_OR_OPTIMIZE_CANDIDATE_REQUIRES_SCIENTIFIC_REVIEW**

The specialized bounds are materially tighter somewhere, but the conference-level net-complexity gate is not yet established.

This is not a paper-level GO verdict. The final verdict requires scientific review of the raw trials, proof source, and current literature.

## Correctness evidence

- **likelihood_recurrence_vs_explicit_channel**: PASS (2728 cases)
- **strict_reversal_family**: PASS (1062 cases)
- **uac_and_chain_bounds_vs_independent_references**: PASS (5336 cases)
- **all_nonempty_codebooks_n_le_4_all_observations**: PASS (1050660 cases)

Paired three-mode decoder disagreements: **0**  
Exhaustive codeword-ML failures: **0**  
Bound-hierarchy failures: **0**

## Natural-channel pilot by cell

| n | rate_label | family | alignment_schedule | p_s | trials | paired_complete | median_q_hist_ratio_ind_over_cr | median_walltime_ratio_ind_over_cr | median_q_hist_ratio_ind_over_ac | median_walltime_ratio_ind_over_ac | ind_censored | cr_censored | ac_censored | tail_status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 | R2_3 | crc_defined_linear | even_odd | 0.05 | 4 | 4 | 1.005 | 0.06288 | 1.059 | 0.01031 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R2_3 | crc_defined_linear | even_odd | 0.01 | 4 | 4 | 1.083 | 0.06091 | 1.333 | 0.01476 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R2_3 | crc_defined_linear | forward | 0.05 | 4 | 4 | 1 | 1.026 | 1.018 | 0.0159 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R2_3 | crc_defined_linear | forward | 0.01 | 4 | 4 | 1 | 1.012 | 1.072 | 0.007935 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R2_3 | random_systematic_linear | even_odd | 0.05 | 4 | 4 | 1.007 | 0.1082 | 1.099 | 0.02255 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R2_3 | random_systematic_linear | even_odd | 0.01 | 4 | 4 | 1.089 | 0.04004 | 1.298 | 0.01113 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R2_3 | random_systematic_linear | forward | 0.05 | 4 | 4 | 1 | 0.9234 | 1.001 | 0.01464 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R2_3 | random_systematic_linear | forward | 0.01 | 4 | 4 | 1 | 1.536 | 1.034 | 0.01281 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | crc_defined_linear | even_odd | 0.05 | 4 | 4 | 1.104 | 0.05696 | 1.192 | 0.009213 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | crc_defined_linear | even_odd | 0.01 | 4 | 4 | 1.111 | 0.04699 | 1.455 | 0.01516 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | crc_defined_linear | forward | 0.05 | 4 | 4 | 1 | 0.9517 | 1.091 | 0.008736 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | crc_defined_linear | forward | 0.01 | 4 | 4 | 1 | 0.9309 | 1.226 | 0.01011 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | random_systematic_linear | even_odd | 0.05 | 4 | 4 | 1.041 | 0.05128 | 1.183 | 0.01069 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | random_systematic_linear | even_odd | 0.01 | 4 | 4 | 1.192 | 0.0569 | 1.35 | 0.01136 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | random_systematic_linear | forward | 0.05 | 4 | 4 | 1 | 1.019 | 1.072 | 0.008116 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 16 | R3_4 | random_systematic_linear | forward | 0.01 | 4 | 4 | 1 | 1.034 | 1.096 | 0.008688 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | crc_defined_linear | even_odd | 0.05 | 4 | 4 | 1 | 0.08331 | 1.105 | 0.01102 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | crc_defined_linear | even_odd | 0.01 | 4 | 4 | 1.082 | 0.02757 | 1.31 | 0.005176 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | crc_defined_linear | forward | 0.05 | 4 | 4 | 1 | 0.9608 | 1.022 | 0.009029 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | crc_defined_linear | forward | 0.01 | 4 | 4 | 1 | 1.04 | 1.022 | 0.003187 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | random_systematic_linear | even_odd | 0.05 | 4 | 4 | 1.005 | 0.05934 | 1.171 | 0.0105 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | random_systematic_linear | even_odd | 0.01 | 4 | 4 | 1.002 | 0.02142 | 1.157 | 0.003788 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | random_systematic_linear | forward | 0.05 | 4 | 4 | 1 | 1.002 | 1.012 | 0.006239 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R2_3 | random_systematic_linear | forward | 0.01 | 4 | 4 | 1 | 0.9827 | 1 | 0.002565 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | crc_defined_linear | even_odd | 0.05 | 4 | 4 | 1.004 | 0.05982 | 1.202 | 0.01763 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | crc_defined_linear | even_odd | 0.01 | 4 | 4 | 1.061 | 0.02418 | 1.197 | 0.00318 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | crc_defined_linear | forward | 0.05 | 4 | 4 | 1 | 0.9911 | 1.077 | 0.01188 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | crc_defined_linear | forward | 0.01 | 4 | 4 | 1 | 0.9512 | 1.021 | 0.002907 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | random_systematic_linear | even_odd | 0.05 | 4 | 4 | 1.003 | 0.1155 | 1.21 | 0.01608 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | random_systematic_linear | even_odd | 0.01 | 4 | 4 | 1.125 | 0.05117 | 1.286 | 0.02279 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | random_systematic_linear | forward | 0.05 | 4 | 4 | 1 | 0.9858 | 1.059 | 0.0122 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 24 | R3_4 | random_systematic_linear | forward | 0.01 | 4 | 4 | 1 | 0.9437 | 1.022 | 0.02116 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | crc_defined_linear | even_odd | 0.05 | 4 | 4 | 1 | 0.2556 | 1.008 | 0.03463 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | crc_defined_linear | even_odd | 0.01 | 4 | 4 | 1.118 | 0.02827 | 1.39 | 0.01849 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | crc_defined_linear | forward | 0.05 | 4 | 4 | 1 | 0.9891 | 1.001 | 0.03365 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | crc_defined_linear | forward | 0.01 | 4 | 4 | 1 | 0.9593 | 1.156 | 0.01547 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | random_systematic_linear | even_odd | 0.05 | 4 | 4 | 1 | 0.05936 | 1.185 | 0.008051 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | random_systematic_linear | even_odd | 0.01 | 4 | 4 | 1 | 0.1256 | 1.028 | 0.02056 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | random_systematic_linear | forward | 0.05 | 4 | 4 | 1 | 1.042 | 1.025 | 0.005815 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R2_3 | random_systematic_linear | forward | 0.01 | 4 | 4 | 1 | 1.019 | 1.008 | 0.006122 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | crc_defined_linear | even_odd | 0.05 | 4 | 4 | 1.001 | 0.07174 | 1.171 | 0.01105 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | crc_defined_linear | even_odd | 0.01 | 4 | 4 | 1.005 | 0.07789 | 1.007 | 0.008032 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | crc_defined_linear | forward | 0.05 | 4 | 4 | 1 | 1.008 | 1.018 | 0.006493 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | crc_defined_linear | forward | 0.01 | 4 | 4 | 1 | 0.9277 | 1.001 | 0.005027 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | random_systematic_linear | even_odd | 0.05 | 4 | 4 | 1 | 0.05783 | 1.215 | 0.007829 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | random_systematic_linear | even_odd | 0.01 | 4 | 4 | 1.078 | 0.02677 | 1.354 | 0.006271 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | random_systematic_linear | forward | 0.05 | 4 | 4 | 1 | 0.9952 | 1.062 | 0.0052 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |
| 32 | R3_4 | random_systematic_linear | forward | 0.01 | 4 | 4 | 1 | 1.016 | 1.077 | 0.003768 | 0 | 0 | 0 | INSUFFICIENT_N_FOR_99TH |


`CR` is the O(n^2) recurrence-only chain relaxation; `AC` is the exact O(n^3) shell-consistent bound. A ratio above one favors the strengthened bound. Both use the same candidate stream as the independent certificate within a row. The two alignment schedules alter only the tie order among equal-probability alignment components. No 99th-percentile claim is made for cells with fewer than 100 paired complete trials.

## Structural bound scan by alignment schedule

- `even_odd`: U_CR strict in 864/1680 cases; U_AC strict in 1661/1680 cases; median U_ind/U_AC=2.998.
- `forward`: U_CR strict in 0/1680 cases; U_AC strict in 1658/1680 cases; median U_ind/U_AC=1.928.

Forward shell completion is included as a negative control: its prefix frontier often makes the recurrence-only relaxation equal to the independent sum. The even/odd order tests whether schedule co-design creates useful nonmonotone frontier geometry without changing likelihood order.

## Interpretation rules

1. Any exact-validation, hierarchy, exhaustive-ML, or decoder disagreement blocks the project.
2. A cheap U_CR wall-clock win is stronger practical evidence than a large U_AC work reduction whose DP overhead dominates.
3. A sound but expensive U_AC result supports at most a mathematical/ITW route unless a cheaper realization or stronger complexity theorem is found.
4. Schedule gains are algorithm-design evidence only; they do not create novelty by themselves.
5. Negligible tightening across both specialized bounds is a STOP signal; adding channel models is not a remedy.

## Files to inspect

- `validation/exact_validation_summary.json`
- `pilot/paired_trials.csv`
- `pilot/cell_summary.csv`
- `pilot/stress_summary.csv`
- `pilot/schedule_summary.csv`
- `pilot/bound_scan.csv`
- `pilot/bound_scan_summary.json`
- `pilot/SCREENING_DECISION.json`
- `theory/FIBER_GRAND_Phase2A_Proof_Closure_Candidate.tex`
