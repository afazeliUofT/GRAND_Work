# Scientific gate and stopping rules

## Authorized Phase 2A sequence

1. Independently review the proof-only source. Do not use simulation as a substitute for proof.
2. Require exact agreement among exhaustive maximization, the literal four-coordinate DP, and the optimized three-coordinate DP for `U_AC`.
3. Require exact agreement between exhaustive recurrence relaxation and the O(n^2) DP for `U_CR`, and verify `U_AC <= U_CR <= U_ind`.
4. Require zero false certificates for every nonempty codebook, every observation, all three bounds, and both alignment schedules through n=4.
5. Only after items 1–4 pass, run the paired bounded pilot using identical code membership, candidate stream, and tie policy within each schedule.
6. Review search-work reduction and wall-clock overhead together. A tighter mathematical bound that materially slows decoding is not, by itself, an algorithmic conference result.
7. Refresh the targeted literature audit before claiming novelty for the constrained DPs, schedule co-design, or a complexity theorem.

## Phase-2A outcome rules

- **Continue candidate:** correctness passes and a synchronization-specific mechanism repeatedly gives at least 2x median search-work reduction across several cells, with credible evidence that wall-clock benefit can survive.
- **Narrow/optimize candidate:** the strict theorem and bound are sound and materially tighter, but overhead dominates. This supports a mathematical/ITW route or one focused optimization attempt, not a large campaign.
- **Stop candidate:** any exactness failure, anticipation by prior art, or negligible tightening across useful cells.

The package never automatically declares a publication-level GO. `SCREENING_DECISION.json` is a conservative diagnostic requiring scientific review.
