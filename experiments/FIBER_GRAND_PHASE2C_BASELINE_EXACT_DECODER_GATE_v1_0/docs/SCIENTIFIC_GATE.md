# Phase 2C scientific gate

## Mandatory correctness conditions

Any of the following stops the route:

- deduplicated and history-pair exact decoders return different complete ML signatures;
- a completed exhaustive or branch-and-bound baseline disagrees with the shell decoder;
- a realized stopping shell exceeds the proved realization-dependent cap;
- exact enumeration/accounting invariants fail.

## Bounded GO criteria

A Paper-I baseline-decoder GO requires:

1. no mandatory correctness failure;
2. natural-channel censoring at or below 2%;
3. at least four `n=32` cells each having:
   - median codebook-size/complete-score-evaluation ratio at least `10^5`;
   - 10th-percentile ratio at least `10^4`;
   - median codebook-size/membership-query ratio at least `100`;
4. median exact-exhaustive/deduplicated wall-clock ratio at least `5` over the preregistered `n=32` exhaustive calibrations.

The `n+1` insertion-sphere generator has a separate supporting gate: at least four `n=32` cells should show a median history-pair/deduplicated wall-clock ratio of at least `1.2`. Failure of this supporting gate does not reject the baseline exact decoder; it means the classical local deduplication should not be sold as a practical speedup.

## Possible labels

- `GO_PAPER_I_BASELINE_EXACT_DECODER`
- `NARROW_TO_THEOREM_AND_QUERY_COMPLEXITY`
- `NARROW_COMPLEXITY_TAIL_UNRESOLVED`
- `STOP_BASELINE_DECODER_ROUTE`
- `STOP_CORRECTNESS_FAILURE`

No label authorizes a broader multi-edit campaign or a Transactions submission.
