# Verified novelty matrix after independent review

This is a bounded academic assessment through 3 August 2026, not a patent or worldwide-priority
opinion.

| Claim | Final classification | Closest antecedent and precise distinction |
|---|---|---|
| Aggregate one-deletion+BSC likelihood is a sum over deletion alignments | **KNOWN principle / channel specialization** | Bahl-Jelinek and deletion-channel ML already marginalize synchronization paths. The displayed closed form is the exact one-uniform-deletion+BSC specialization. |
| Linear recurrence for all alignment mismatch counts | **PARTIALLY ANTICIPATED implementation lemma** | Gershon-Cassuto linearly compute the corresponding minimum one-deletion alignment distance. Retaining every component via the explicit recurrence is useful but not a leading novelty claim. |
| Explicit strict binary reversal with `n p_s > 1+2p_s^2` | **DISTINCT construction (provisional)** | Path-versus-aggregate reversal and alignment multiplicity are known. No checked source gives this family or exact threshold. |
| Discovery metric `h_y(x)=min_j d_j(x,y)` | **KNOWN / directly anticipated up to orientation** | Gershon-Cassuto use the minimum Hamming mismatch over all one-deletion alignments and linear computation. First appearance under exhaustive shell/insertion enumeration is immediate. |
| Membership-based shell decoder architecture | **PARTIALLY ANTICIPATED synthesis** | GRAND, aggregate IDS inference, probabilistic-string search, and GCD supply the generic components. The exact one-deletion+BSC assembly is channel-specific. |
| Closed-form aggregate unseen-word bound `U_s` | **DISTINCT channel-specific bound (provisional)** | Generic potential/threshold bounds are known. No checked source gives this exact word-likelihood bound after a completed one-deletion+BSC substitution shell. |
| Strict incumbent `>U_s` returns complete ML tie set | **PARTIALLY ANTICIPATED logic; distinct only through `U_s`** | Strict incumbent-versus-bound exact search is generic. The complete-tie consequence is important but its channel-specific content is the valid `U_s`. |
| Realization-dependent stop `S<=min{m,T+L_n-1}` | **DISTINCT (provisional)** | GRAND/GRANDAB analyze noise rank and abandonment, but no direct exact code-independent synchronization bound with this logarithmic alignment penalty was located. |
| Finite work cap `(n+1)Vol(m,S)` | **PARTIALLY ANTICIPATED direct consequence** | Uses classical insertion-sphere and Hamming-ball counting; the new input is the stopping theorem. |
| High-probability exponent `h_2(p_s)` | **KNOWN mechanism / new-setting corollary** | BSC typical-volume and GRAND analysis establish the exponent mechanism. The paper shows that one exact deletion adds only subexponential overhead after the new stop theorem. |
| `n+1` binary insertion sphere | **KNOWN** | Classical Levenshtein insertion/deletion combinatorics. |
| Generic threshold stopping | **KNOWN** | Fagin-style thresholding, probabilistic-string search, branch-and-bound, and modern GCD stopping. |
| Code membership interface | **KNOWN** | Defining feature of GRAND-style universal decoding. |
| Fixed-query-set random-code occupancy identity | **DISTINCT explanatory proposition, elementary** | Exact hypergeometric occupancy conditioned on the transmitted word; added to explain, not inflate, finite scoring evidence. |
| Frozen 996-trial exact campaign | **DISTINCT evidence record** | Original data and implementation verification, with explicitly limited generalization. |

## Claims prohibited in the repaired paper

- “first exact decoder for synchronization errors”;
- “new deletion/substitution distance”;
- “new threshold aggregation principle”;
- “new `h_2` law for guessing decoding”;
- “universal orders-of-magnitude latency speedup”;
- any extension to multiple deletions, insertions, soft information, transducers, hardware, or code design.
