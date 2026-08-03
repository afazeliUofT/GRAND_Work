# Phase 2B-R1 scientific gate

## Mandatory order

1. Verify both the frozen Phase-2A PASS commit and the recorded failed Phase-2B diagnostic commit are ancestors of the current repository state.
2. Repair the Phase-2A manifest without rerunning computation. Accept only the five preregistered CSV normalizations and the exact four-line post-manifest console append.
3. Export `bound_scan.csv` and `paired_trials.csv` directly from the frozen commit and use those immutable exports for replay.
4. Pass exact proof-support checks and the compiled self-test.
5. Match all 3,360 frozen bound values and all 214 decoder stopping/output records exactly.
6. Require at least `50x` `U_AC` kernel acceleration over the Python reference.
7. On replay cases with at least `10x` search-work reduction, require at least three cases and median cost-aware compiled-mode/independent end-to-end time no greater than `2`.
8. Only then run the preregistered `n=32`, `p_s=0.05`, four-cell targeted pilot.

## Targeted-pilot gate

A conference-specialization candidate requires either:

- at least `2x` median emitted-history reduction and `1.2x` median wall-clock speedup in at least three of four cells; or
- no more than `10%` median overhead and at least `2x` 95th-percentile latency improvement in at least three cells.

Zero exact disagreements and zero censoring are mandatory.

Passing this gate authorizes only a later evidence phase. It does not establish worldwide novelty, final ISIT readiness, or a Transactions extension.
