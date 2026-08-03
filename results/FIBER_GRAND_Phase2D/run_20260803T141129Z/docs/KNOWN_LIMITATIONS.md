# Known limitations

1. The main empirical campaign uses only `p_s=0.05`, blocklengths through 32, and 64 natural trials per cell.
2. Exhaustive `n=32` wall-clock calibration is limited to 16 `k=21` cases.
3. Generic branch-and-bound is a comparator, not a proof of superiority to all exact code-specific decoders.
4. The membership-oracle exponent does not price the implementation cost of every membership test.
5. The high-probability exponent follows from a Hamming-volume argument and may be viewed as mathematically direct; significance requires external review.
6. The finite campaign observed selected best-path representatives different from the selected ML representative, but no strictly disjoint best-path/ML tie sets.
7. High ML block-error rates at the chosen high-rate operating points do not invalidate exactness, but they limit system-performance interpretation.
8. Absolute novelty and independent proof certification are not supplied by the package.
