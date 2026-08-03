# Phase-2A proof obligations

An independent mathematical review must mark each item PASS or return the smallest counterexample.

1. Verify the one-deletion likelihood by conditioning on the deletion coordinate, including the equivalence of substituting before or after deletion.
2. Verify the sliding recurrence and coordinate conventions.
3. Recompute every mismatch multiplicity and the factorization in the strict reversal family.
4. Verify that each alignment stream contains exactly one component for every candidate.
5. Verify that the independent certificate bounds only completely undiscovered candidates and that strict inequality is necessary for complete tie-set certification.
6. Verify the shell implication: a completely undiscovered candidate satisfies every `d_j >= r_j` constraint, including partially processed shells and exhausted streams.
7. Verify the recurrence-relaxed feasible set, the hierarchy `U_AC <= U_CR <= U_ind`, and the O(n^2)-time/O(n)-memory DP.
8. Verify the forward-prefix degeneracy construction and the strict n=3 nonmonotone-frontier example.
9. Verify the optimized exact-DP invariant `(current bit, current d, remaining suffix mismatches)` and terminal condition `remaining=0`.
10. Verify the O(n^3)-time/O(n^2)-memory count; the earlier O(n^4)/O(n^3) formulation must remain a structurally independent reference implementation.
11. Verify the strict `U_AC < U_ind` family and boundary cases `p_s=0`, `p_s=1/2`, small n, and exhausted streams.
12. Keep novelty, proof correctness, implementation correctness, and empirical usefulness as four separate verdicts.
