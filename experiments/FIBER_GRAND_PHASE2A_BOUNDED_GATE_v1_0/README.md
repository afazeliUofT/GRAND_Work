# FIBER-GRAND Paper I — Phase 2A bounded gate v1.0

This package implements the bounded continuation authorized by the corrected Phase-1 novelty audit. The order is deliberate:

1. freeze and expose the proof obligations;
2. run exact arithmetic and complete small-world checks;
3. only after correctness passes, run a small paired computational pilot;
4. return all evidence for a human GO/NARROW/STOP review.

Theorems do not require simulations to become true. The computational work is included to detect proof-to-code mistakes and to determine whether the stronger certificate has enough practical value to justify continuing.

## What the package tests

- exact one-deletion likelihood and sliding mismatch recurrence;
- strict non-tie-dependent best-history/aggregate-ML reversal;
- independent unseen-candidate certificate;
- O(n^2) recurrence-relaxed certificate `U_CR`;
- exact O(n^3) alignment-consistent certificate `U_AC`;
- brute-force/reference/optimized agreement for the bounds;
- every nonempty codebook and every observation through n=4;
- paired decoders using identical candidate streams and tie policy;
- forward and even/odd equal-likelihood alignment schedules;
- two unmodified systematic linear-code families, n={16,24,32}, two rates, and p_s={0.01,0.05};
- a bounded forced-error-weight stress set and a code-independent frontier scan.

The package is dependency-free and uses only the Python standard library. It is designed to be launched by the accompanying `RUN_FIBER_GRAND_PHASE2A.py` wrapper from `/home/afazeli2006/GRAND_Work`.

## Scientific status

A successful run means the implementation evidence is internally consistent. It does **not** automatically establish novelty, useful latency, or conference readiness. Review `PHASE2A_REPORT.md`, the raw CSV files, and the proof source before issuing the scientific verdict.
