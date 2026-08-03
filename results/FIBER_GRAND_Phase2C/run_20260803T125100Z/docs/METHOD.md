# Phase 2C method

## Frozen scientific question

Does the inexpensive baseline FIBER-GRAND decoder—not the costly `U_AC` certificate—provide a meaningful exact-ML result for Paper I?

The evidence is separated into four layers:

1. **Mathematical exactness:** discovery-shell characterization, shell certificate, realization-dependent stopping, and query bounds.
2. **Implementation exactness:** deduplicated and history-pair decoders must agree; exhaustive ML and completed branch-and-bound runs must agree.
3. **Query complexity:** code-membership calls and complete codeword-likelihood evaluations are measured separately from codebook size.
4. **Wall-clock calibration:** exact exhaustive and generic branch-and-bound timings are reported without claiming universal optimality.

## Decoder

For each substitution shell `s`, enumerate all length-`n-1` error patterns of Hamming weight `s`. For each altered observation, enumerate its `n+1` distinct binary one-insertion supersequences. A global seen set prevents repeated membership/scoring work. Codewords are assigned their full alignment-summed likelihood. After completing shell `s`, the decoder stops when the incumbent strictly exceeds the exact unseen-candidate shell bound.

## Comparators

- `history`: the same exact shell decoder, but generating all `2n` alignment-history pairs per error pattern before global deduplication;
- `exhaustive`: complete likelihood evaluation for every codeword where preregistered;
- `branch`: a generic exact branch-and-bound search over generator coefficients, subject to a time/node cap; only completed runs are compared as exact baselines;
- `bestpath`: the codeword tie set first encountered at the minimum alignment-mismatch shell, used only to quantify pathwise-versus-aggregate behavior.

## Campaign

The default campaign has 896 natural trials and 100 stress trials. Natural cells cover `n={16,24,32}`, rates near `2/3` and `3/4`, random systematic and CRC-defined codes, plus extended Hamming at `n=16,32`. Random-code cells rotate over four independently seeded code instances. The stress set fixes surviving substitution weights 0 through 4 at `n=32`.

All exact decisions use fixed-capacity 512-bit integer arithmetic with overflow checks. No floating-point comparison determines an ML result or stopping decision.
