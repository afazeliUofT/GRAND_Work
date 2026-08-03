# Phase 2B-R1 proof audit

## Channel-coding status

The likelihood identity, sliding recurrence, strict reversal factorization, independent certificate, shell implication, exact `U_AC` DP invariant, recurrence-relaxed hierarchy, forward-prefix degeneracy construction, and strict nonmonotone example remain internally marked **PASS**.

The Phase-2B proof source already makes two necessary qualifications:

1. `O(n^3)` and `O(n^2)` are arithmetic-operation counts; bit complexity depends on exact-integer operand length.
2. Boundary cases `p_s=0`, `p_s=1/2`, exhausted streams, and zero deletion weights are stated explicitly.

## R1 provenance closure

The separate note `PHASE2B_R1_MANIFEST_REPAIR_ARGUMENT.md` gives the exact closed-world argument for accepting the five CSV line-ending normalizations and the four-line post-manifest console append. This repair changes no theorem, algorithm, or numerical evidence.

## Not closed by this package

- absolute worldwide novelty;
- an infinite-family emitted-history separation;
- an external independent proof certificate;
- practical value of `U_AC`, which is decided by the compiled replay and targeted gate;
- the final baseline comparison needed for conference submission.
