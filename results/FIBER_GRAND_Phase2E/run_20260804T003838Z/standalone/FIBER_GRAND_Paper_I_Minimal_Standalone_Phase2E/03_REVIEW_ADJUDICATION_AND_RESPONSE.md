# Phase 2E independent-review adjudication and response

## Final scientific decision

**ITW_READY_AFTER_REVIEW_REPAIR**

The four reviews agree that the theorem chain is correct and that the work is publishable only after
narrowing its novelty claims. Two mathematical reviews return `PASS_WITH_EDITS`; two novelty reviews
return `ITW_READY_AFTER_REPAIR`. No review supports rejection, and no review supplies a
counterexample to exactness. The repairs in this package require no new simulation.

The paper is **not positioned as ISIT-ready**. Its defensible contribution is a workshop-scale,
channel-specific theorem package:

1. an explicit strict binary deletion-alignment-component/aggregate-ML reversal family and exact
   threshold;
2. the closed-form unseen-shell aggregate bound `U_s`;
3. a complete-tie exact stopping certificate using that bound;
4. the code-independent realization-dependent stop `S <= min{m,T+L_n-1}`;
5. exact finite-length evidence with generation, membership, complete scoring, and time reported
   separately;
6. a new explanatory random-code occupancy benchmark for the scoring measurements.

The aggregate likelihood principle, minimum deletion-alignment metric, generic threshold logic,
GRAND membership interface, one-insertion sphere, and the BSC `h_2(p_s)` typical-volume mechanism
are not claimed as new.

## Materials adjudicated

The source reviews are included verbatim under `reviews/source_reviews/` and are identified by their
SHA-256 hashes in `SOURCE_REVIEW_MANIFEST.sha256`.

- N1: `FIBER_GRAND_PaperI_Independent_Novelty_Review.md`
- N2: `FIBER_GRAND_Paper_I_Independent_Novelty_Review_2026-08-03.pdf`
- M1: `FIBER_GRAND_Paper_I_Independent_Mathematical_Review.md`
- M2: `FIBER_GRAND_Paper_I_Independent_Mathematical_Review.pdf`

## Independent validation performed in Phase 2E

The following points were independently rechecked rather than accepted solely because a reviewer
stated them.

- The two proof-domain issues in M2 are real: `U_s` had been invoked outside its declared domain in
  the exhaustion branch, and the exponent proof used an unjustified equality from only an upper
  bound on `S/m`. Both are repaired.
- The simple strictness witness from M2 is exact:
  `n=4`, `y=001`, `p_s=1/3`, `C={0010,0000}` gives alignment-distance vectors
  `(2,2,1,0)` and `(1,1,1,1)`, and both words have likelihood `U_0=4/27` while only the first is
  seen at shell zero.
- The reversal regime statement in N1 is correct: at `p_s=0.05`,
  `n p_s > 1+2p_s^2` holds exactly for integer `n>=21`; it fails at `n=16` and holds at
  `n=24,32`.
- The random-code occupancy calculation is correct after making its conditioning explicit. For a
  fixed query set `A` of size `G` containing the transmitted word and a uniform `M`-word codebook
  conditioned on that word,

  `E[|A intersect C| | A,x0] = 1 + (G-1)(M-1)/(2^n-1)`.

  With `n=32` and shell-one generation cap `G=1056`, it predicts `1.52`, `5.12`, and `17.48`
  completely scored words for `k=21,24,26`, close to the observed medians. It is retained as a
  benchmark, not asserted for structured codes or stopping-conditioned medians.
- Primary literature was rechecked. Bahl-Jelinek establishes aggregate IDS likelihood computation;
  GRAND establishes the membership-first first-hit rule for likelihood-ordered additive noise;
  Gershon-Cassuto uses the minimum Hamming mismatch across one-deletion alignments with linear
  computation; Sabary et al. make alignment multiplicity explicit for deletion-channel ML;
  de la Higuera-Oncina and modern GCD work establish generic incumbent-versus-unfinished-bound
  exact search. These sources narrow the claims but do not disclose the exact strict family,
  `U_s`, or `T+L_n-1` theorem located here.
- A targeted 2023-2026 search of indexed DNA-storage, reconstruction, deletion/substitution-code,
  and guessing-decoder literature found neighboring error-ball, sequence-reconstruction, and
  code-design results, but no direct antecedent for this exact shell-certified aggregate decoder.
  This is a bounded academic search, not proof of worldwide priority; non-indexed and thesis
  literature remains a residual risk.

## Claim-by-claim adjudication

| Issue raised | Decision | Scientific response implemented |
|---|---|---|
| Aggregate likelihood over alignments is established prior art | **ACCEPT** | Bahl-Jelinek and deletion-ML sources are cited; Eq. (likelihood) is presented as a specialization, not a contribution. |
| General best-path versus aggregate-string mismatch is known | **ACCEPT** | The claim is narrowed to the explicit binary two-codeword family and its exact strict threshold. |
| The exact strict reversal family is directly known | **REJECT** | No review or primary source identifies the same family or threshold. The generic phenomenon is known; the exact family remains provisionally distinct. |
| Discovery metric `min_j d_j` is new | **REJECT AS A NOVELTY CLAIM** | Gershon-Cassuto is added. The metric is treated as known up to orientation; only its immediate first-appearance role is used. |
| Generic incumbent/threshold stopping is new | **REJECT AS A NOVELTY CLAIM** | Fagin, probabilistic-string search, and GCD are cited. Novelty is concentrated in the closed-form channel-specific `U_s`. |
| `U_s` is merely the generic threshold rule | **REJECT** | The rule is generic, but the exact aggregate unseen-word bound is channel-specific and no direct antecedent was found. It remains a narrow distinct claim. |
| Realization-dependent `T+L_n-1` stop is distinct | **ACCEPT** | It is promoted as the strongest analysis theorem. No direct antecedent was located. |
| `h_2(p_s)` is a new guessing-decoder exponent | **REJECT** | The value and typical-volume mechanism are classical. It is demoted to a standard corollary of the new exact stop theorem. |
| The paper's high-probability theorem is wholly known | **MODIFY** | Its entropy mechanism is known; applying it to this exact synchronization decoder is a new but mathematically direct specialization. It is not a headline contribution. |
| Add Bahl-Jelinek, Gershon-Cassuto, Sabary, Yang, and exact-search antecedents | **ACCEPT** | All are added with explicit technical comparisons. |
| State the reversal regime at `p_s=0.05` | **ACCEPT** | The manuscript states that the family reverses for integer `n>=21`, hence at `24,32` but not `16`. |
| Stopping proof must split exhaustion before using `U_s` | **ACCEPT** | The proof now first handles `s_0>=m` by exhaustion; `U_{s_0}` is used only for `s_0<m`. |
| Exponent proof equality is unjustified | **ACCEPT** | It now defines deterministic `a_n`, uses `S/m<=a_n`, monotonicity of Hamming volume and `h_2`, and continuity. |
| Use “largest deletion-alignment component,” not ambiguous full history | **ACCEPT** | Terminology is changed and the common deleted-coordinate factor is explained. |
| Include a strictness witness for complete ties | **ACCEPT** | The simpler exact `n=4`, `p_s=1/3` witness is included. |
| Add random-code scoring prediction | **ACCEPT WITH CAVEAT** | An exact fixed-query-set occupancy proposition is added. It is explicitly not a theorem for structured codes or conditional medians. |
| Small-n experiments show `U_s` is not tight | **NO ACTION REQUIRED** | Plausible and compatible with prior Phase 2B work, but not needed for the repaired Paper I and based on a limited auxiliary scan. No new practical-bound claim is made. |
| The theorem chain is mathematically invalid | **REJECT** | All four reviews affirm correctness; the two identified issues are proof-writing/domain repairs, not false statements. |
| More simulations are required before repair | **REJECT** | Every required change is analytical, bibliographic, or packaging-related. Frozen Phase 2C evidence remains unchanged. |

## Resolution of disagreements among the reviews

### Exact reversal: `DISTINCT` versus `PARTIALLY_ANTICIPATED`

Both labels can be correct at different granularity. The general fact that one path need not maximize
an aggregate output is known; the exact binary family and threshold were not located. The repaired
paper states this distinction explicitly and labels only the construction as provisionally distinct.

### Query exponent: `KNOWN` versus `PARTIALLY_ANTICIPATED`

The exponent value and proof mechanism are known for BSC typical-volume/GRAND analysis. The exact
synchronization decoder's inheritance of that upper exponent follows only after the new stopping
bound. The repaired paper therefore treats it as a standard corollary in a new setting, not as an
independent foundational contribution.

### Mathematical review: “all PASS” versus two precise repairs

The theorem statements are correct, which explains the all-PASS assessment. The second review
correctly identifies two local proof-writing gaps. They are repaired because rigorous presentation
requires the finite-exhaustion case split and a monotone upper-bound argument; neither changes a
statement or any numerical result.

## Empirical claim discipline retained

- `|C|/Q_score` counts avoided complete codeword-likelihood evaluations, not universal latency.
- `|C|/Q_mem` depends on the membership implementation.
- Only 16 `n=32` exhaustive timing calibrations were run, all at `k=21`.
- The generic branch-and-bound comparator completed only on the preregistered capped subset.
- FIBER was faster in four of five `n=32` branch-calibration cells, not universally.
- The `n+1` generator reduced attempts but failed its wall-clock gate.
- Selected representative differences are not strict pathwise failures; zero sampled tie-set pair
  was disjoint.
- The channel remains exactly one uniform deletion plus hard BSC substitutions.

## Venue and program verdict

The repaired manuscript is a defensible **ITW candidate**. The current result should not be sold as
a new universal synchronization decoder or as an ISIT-level new complexity exponent. A future ISIT
or Transactions extension would require an additional non-direct theorem, such as a sharp
lower/near-optimality result, a distributional expected-query law beyond standard Hamming-volume
counting, or a broader exact tractability result. None is required for the present workshop paper.

## Computation decision

**No new simulation is authorized or required.** The Phase-2E WSL run performs only integrity,
proof-regression, citation/claim-discipline, standalone-compilation, and Git provenance checks.
