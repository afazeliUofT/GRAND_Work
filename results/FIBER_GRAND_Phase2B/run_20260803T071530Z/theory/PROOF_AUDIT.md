# Phase 2B proof audit

## Internal status

The likelihood identity, sliding recurrence, strict reversal factorization, independent certificate, shell implication, exact `U_AC` DP invariant, recurrence-relaxed hierarchy, forward-prefix degeneracy construction, and strict nonmonotone example are internally marked **PASS**.

Phase 2B makes two corrections to the earlier presentation:

1. `O(n^3)` and `O(n^2)` are exact arithmetic-operation counts. Bit complexity depends on the exact-integer operand length; the Phase-2B compiled implementation uses a verified 512-bit capacity for the frozen range.
2. Boundary cases `p_s=0`, `p_s=1/2`, exhausted streams, and zero deletion weights are stated explicitly.

## Not closed by this package

- absolute worldwide novelty;
- an infinite-family emitted-history separation;
- an external independent proof certificate;
- practical value of `U_AC`, which is decided by the compiled replay and targeted gate.
