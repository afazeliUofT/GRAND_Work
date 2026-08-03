# Known limitations

1. The proof document is an internally audited closure candidate; independent human proof review remains required.
2. The targeted literature refresh is not an absolute novelty or patent search.
3. The targeted pilot, if authorized, has two code families and 256 trials per cell; it is not the final three-family or 99.9th-percentile campaign.
4. A fast compiled implementation does not itself create algorithmic novelty.
5. `U_AC` remains a shell-consistency bound and does not exclude already discovered candidates or exploit within-shell rank.
6. The exact C++ implementation uses 64-bit candidates and a checked 512-bit score capacity; its declared contract is `n<=63` and odds denominator `a<=99`. The preregistered experiment uses `n=32`.
7. Exhaustive codeword ML is not rerun at `n=32`; exactness rests on agreement among certified modes and frozen exhaustive checks at feasible sizes.
8. The R1 repair proves consistency of the frozen artifacts under a closed transformation set. It does not certify the physical machine, Git host, or SHA-256 implementation against malicious compromise.
