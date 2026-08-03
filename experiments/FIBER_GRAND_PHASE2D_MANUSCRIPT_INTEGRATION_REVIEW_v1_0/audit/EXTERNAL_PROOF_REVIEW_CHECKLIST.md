# Independent proof-review checklist

The reviewer should work from the proof supplement, not from the implementation. For every item, return **PASS** or the smallest counterexample/incorrect line.

1. Confirm the channel law when substitutions occur before deletion and the deleted-coordinate substitution is marginalized.
2. Recompute the sliding mismatch recurrence with the manuscript's coordinate convention.
3. Verify all mismatch multiplicities and the factorization in the strict reversal theorem, including `n=4` and the equality boundary.
4. Verify the `n+1` one-insertion-sphere generator and ensure it is labeled classical.
5. Prove both directions of the discovery-shell characterization.
6. Verify that an unseen word after shell `s` has every alignment distance at least `s+1`.
7. Check that strict incumbent comparison is necessary for complete ML tie-set certification.
8. Verify the `p_s=0` and `p_s=1/2` boundary statements.
9. Check the definition and floor formula for `L_n(p_s)`, especially exact logarithmic boundaries.
10. Verify the realization-dependent stopping ratio `n rho^{L_n}<1` and its indexing.
11. Recompute deterministic, finite-confidence, and expected query bounds.
12. Verify the Hoeffding/Hamming-ball argument and every `o(1)` transition in the high-probability exponent.
13. Confirm that the rate comparison is against exhaustive codeword-wise scoring, not all exact decoders.
14. Confirm that no theorem silently assumes a linear code, a particular parity-check cost, or unique ML decoding.
15. Confirm that empirical selected-representative disagreements are not presented as strict best-path failure.

## Reviewer return format

- Overall verdict: `PASS`, `PASS_WITH_EDITS`, or `REJECT`.
- Smallest mathematical defect, if any.
- Exact theorem/line affected.
- Whether the defect changes correctness, only presentation, or only scope.
