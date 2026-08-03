# Phase 2B scientific gate

## Mandatory order

1. Verify the frozen Phase 2A commit is an ancestor of the current repository state.
2. Repair the Phase 2A manifest without rerunning any computation; all mismatches must be explained solely by CRLF-to-LF normalization.
3. Pass exact proof-support checks and the compiled self-test.
4. Match all frozen Phase 2A bound values and decoder stopping/output records exactly.
5. Require at least 50x `U_AC` kernel acceleration over the independent Python reference.
6. On replay cases with at least 10x search-work reduction, require at least three cases and median cost-aware compiled-mode/independent end-to-end time no greater than 2.
7. Only then run the preregistered n=32, p_s=0.05, four-cell targeted pilot.

## Targeted-pilot gate

A conference-specialization candidate requires either:

- at least 2x median emitted-history reduction and 1.2x median wall-clock speedup in at least three of four cells; or
- no more than 10% median overhead and at least 2x 95th-percentile latency improvement in at least three cells.

Zero exact disagreements and zero censoring are mandatory.

Passing this gate authorizes only a later evidence phase. It does not establish novelty, a final ISIT result, or a Transactions extension.
