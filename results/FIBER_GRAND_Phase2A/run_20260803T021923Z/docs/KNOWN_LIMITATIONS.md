# Known limitations of the bounded package

1. This is not the final 99th- or 99.9th-percentile conference campaign. Cells have only screening-level sample sizes and are explicitly marked insufficient for tail claims.
2. `U_AC` is exact for the shell-consistency relaxation, but it does not exclude already discovered candidates or exploit within-shell rank. It can therefore remain loose.
3. The optimized exact DP is O(n^3) and is not incremental across frontier updates. Its wall-clock overhead may dominate its reduction in search work.
4. `U_CR` is O(n^2), but a theorem in the proof source shows that it equals `U_ind` on ordinary forward prefix frontiers. The even/odd schedule is an exploratory remedy, not an established final design.
5. The performance pilot uses only two linear-code families and two rates. It is a kill test, not generality evidence.
6. Full later certification—such as all two-word codebooks through n=8 and broader adversarial n<=16 testing—is unauthorized unless Phase 2A passes.
7. Novelty relative to constrained/correlated rank aggregation and exact synchronization-error search must be refreshed independently before submission.
