# Known limitations

1. The proof document is an internally audited closure candidate; independent human proof review remains required.
2. The targeted literature refresh is not an absolute novelty or patent search.
3. The targeted pilot contains two code families and 256 trials per cell; it is not the final three-family or 99.9th-percentile campaign.
4. A fast compiled implementation does not by itself create algorithmic novelty.
5. `U_AC` remains a shell-consistency bound and does not exclude already discovered candidates or exploit within-shell rank.
6. The exact C++ implementation uses 64-bit words for candidates and a checked 512-bit score capacity; its declared contract is n<=63 and odds denominator a<=99. The preregistered experiment uses n=32.
7. Exhaustive codeword ML is not rerun at n=32; exactness is established by agreement among certified modes and the frozen exhaustive checks at feasible sizes.
