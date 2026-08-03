# Computational method

## Exact arithmetic

The pilot uses only `p_s=0.01=1/100` and `p_s=0.05=1/20`, with uniform deletion. Let `a=(1-p_s)/p_s`, so `a` is 99 or 19. Every candidate likelihood is a common positive factor times

`S(x,y) = sum_j a^(n-1-d_j(x,y))`.

All candidate scores and stopping bounds are compared as exact Python integers. No floating-point tolerance enters any decoding certificate.

## Candidate streams and schedules

For each mismatch shell, error masks are ordered lexicographically by their coordinate tuple and the inserted/deleted bit is ordered 0 then 1. Two alignment tie orders are tested:

- `forward`: 0,1,...,n-1;
- `even_odd`: 0,2,4,...,1,3,5,....

Under uniform deletion, alignment components in the same mismatch shell have equal probability, so both orders preserve nonincreasing likelihood. All three certificate modes use the identical candidate stream within a paired trial. A candidate is membership-tested only on first discovery and is fully scored only if it belongs to the code.

## Lazy bound hierarchy

The decoder first tests the cheap independent sum `U_ind`. Only when an incumbent exists and `U_ind` fails does it evaluate the O(n^2) recurrence relaxation `U_CR`. The exact O(n^3) alignment-consistent DP `U_AC` is called only if both cheaper bounds fail. The hierarchy is

`U_AC <= U_CR <= U_ind`.

The bound is rechecked when a frontier changes or the incumbent improves. Values are cached for unchanged frontier vectors.

## Code families

- `random_systematic_linear`: a reproducible systematic linear code with seeded dense parity rows;
- `crc_defined_linear`: a systematic linear code induced by a frozen binary generator polynomial and converted to the same parity-row membership interface.

These are unmodified membership-oracle codes. They are not optimized for the deletion channel.

## Bounded workload

The natural pilot covers n={16,24,32}, two rates, two code families, and p_s={0.01,0.05}. Four paired realizations per cell and schedule are used only as a screening experiment, not as final tail evidence. A small forced-error-weight set probes difficult shells. Every decoder has a hard history cap; censored trials are retained and reported rather than silently dropped.
