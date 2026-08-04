# Verified primary-source positioning

The following sources are the load-bearing references for the repaired manuscript.

1. L. R. Bahl and F. Jelinek, “Decoding for Channels with Insertions, Deletions, and
   Substitutions with Applications to Speech Recognition,” *IEEE Transactions on Information
   Theory*, 21(4):404-411, 1975, DOI 10.1109/TIT.1975.1055419.
   - Establishes variable-length IDS channel likelihood `Pr{Y|X}` and efficient computation.
   - Anticipates aggregate path marginalization, but not the present strict binary family or shell
     certificate.

2. K. R. Duffy, J. Li, and M. Medard, “Capacity-Achieving Guessing Random Additive Noise
   Decoding,” *IEEE Transactions on Information Theory*, 65(7):4023-4040, 2019,
   DOI 10.1109/TIT.2019.2896110.
   - Establishes likelihood-ordered additive-noise guessing, first codebook hit, membership-only
     code access, and guesswork/typical-set complexity.
   - Explains what fails when synchronization histories coalesce and why `h_2(p_s)` is not a new
     entropy mechanism.

3. Y. Gershon and Y. Cassuto, “Genomic Compression with Decoder Alignment under Single Deletion
   and Multiple Substitutions,” *IEEE ISIT*, 2022, pp. 998-1003,
   DOI 10.1109/ISIT50566.2022.9834472.
   - Uses the minimum Hamming mismatch across all one-deletion alignments and linear computation.
   - Directly anticipates the discovery metric up to orientation.

4. O. Sabary, E. Yaakobi, and A. Yucovich, “The Error Probability of Maximum-Likelihood Decoding
   over Two Deletion/Insertion Channels,” *IEEE ISIT*, 2020, pp. 763-768, arXiv:2001.05582.
   - Makes deletion-alignment/embedding multiplicity explicit in ML objectives.

5. K. Yang, J. Ren, C. Tian, J. Wang, and H. V. Poor, “Decoding Binary Linear Codes Over Channels
   With Synchronization Errors,” *IEEE Journal on Selected Areas in Communications*, 38(12):
   2853-2863, 2020, DOI 10.1109/JSAC.2020.3005491.
   - Provides a code-specific ML optimization/certification contrast for deletion synchronization
     errors. It does not disclose the membership-oracle shell certificate here.

6. C. de la Higuera and J. Oncina, “Computing the Most Probable String with a Probabilistic Finite
   State Machine,” FSMNLP, 2013.
   - Establishes path-versus-aggregate-string distinction and potential-probability exact search.

7. R. Fagin, A. Lotem, and M. Naor, “Optimal Aggregation Algorithms for Middleware,” *JCSS*,
   66(4):614-656, 2003, DOI 10.1016/S0022-0000(03)00026-6.
   - Establishes generic threshold aggregation; cited to disclaim ownership of the principle.

8. Q. Wang, J. Liang, P. Yuan, K. R. Duffy, M. Medard, and X. Ma, “Guessing Decoding of Short
   Blocklength Codes,” arXiv:2511.12108, 2025.
   - Gives unified GRAND/GCD analysis and ML under appropriate stopping criteria.
   - Anticipates generic incumbent-bound logic, not the present `U_s` or `T+L_n-1` theorem.

9. V. I. Levenshtein, “Binary Codes Capable of Correcting Deletions, Insertions, and Reversals,”
   *Soviet Physics Doklady*, 10(8):707-710, 1966.
   - Classical one-insertion/deletion combinatorics.

## Residual search boundary

A targeted search through recent indexed DNA-storage, sequence-reconstruction, error-ball, code
construction, and guessing-decoder literature found neighboring work on single-deletion plus one or
two substitutions, but no direct source for the exact shell-certified aggregate decoder, `U_s`, or
`T+L_n-1` result. This does not clear unpublished, thesis, patent, or non-indexed literature.
