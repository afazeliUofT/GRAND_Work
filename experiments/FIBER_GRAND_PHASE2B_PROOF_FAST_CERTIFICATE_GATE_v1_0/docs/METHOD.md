# Method

The compiled implementation reproduces the Phase 2A candidate order, code-membership interface, exact aggregate score, strict tie-set certificate, forward/even-odd alignment schedules, and all three bounds. It uses a fixed-capacity 512-bit multiword unsigned integer with explicit overflow detection. This is exact for the frozen Phase-2B range (n<=32 in all runs; the implementation contract is n<=63 and odds denominator a<=99), so stopping comparisons contain no floating-point approximation.

The C++ executable is built with `-O3 -DNDEBUG -std=c++17` into `~/.cache/fiber_grand_phase2b_v1_0`; the binary is not committed. The three decoder modes are executed in a rotated order across trial IDs to reduce systematic timing-order bias.

Before the frozen replay, 198 deterministic synthetic cases compare all three compiled bounds with the Python exact reference using irregular frontiers, exhausted streams, zero/nonuniform deletion weights, and several odds ratios. The replay then compares status, completion, exact scores, final bounds, complete ML tie sets, decoded representatives, emitted histories, distinct candidates, membership calls, exact-score evaluations, and frontier updates against the frozen Phase 2A CSV. Timing is measured anew and is not compared byte-for-byte.

The targeted pilot uses identical observations and code instances across the three exact modes. Four code/rate cells are used: n=32, p_s=0.05, rates near 2/3 and 3/4, and random-systematic/CRC-defined linear codes. No other channel model is added.
