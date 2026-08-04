# Independent Novelty Review — FIBER-GRAND Paper I

**Subject:** *FIBER-GRAND: Exact Inverse-Alignment Decoding for One Deletion and Substitutions* (conference candidate, 4 pp.) and its proof supplement (4 pp.)

**Bundle reviewed:** `FIBER_GRAND_Paper_I_External_Review_Bundle_Phase2D_R1.zip`
**SHA-256 (verified as received):** `a485bbf4f655f73b4250f9048a7b913b07db8d25000f6d8737f06373c0d02cd0`
**Internal manifest:** all 16 listed files verified against `BUNDLE_MANIFEST.sha256` — 16/16 OK.

**Review type:** independent, claim-by-claim novelty assessment, with supporting independent verification of the theorem chain. This is a scientific opinion for submission preparation. It is not a freedom-to-operate opinion, a patentability opinion, or a certificate of worldwide priority.

---

## 0. What was done

Three separate activities fed this report.

1. **Full read** of `01_Conference_Manuscript.pdf` / `.tex`, `02_Proof_Supplement.pdf` / `.tex`, `03_CLAIM_NOVELTY_MATRIX.md`, `04_EXTERNAL_PROOF_REVIEW_CHECKLIST.md`, `05_RESULTS_CLAIM_CHECKLIST.md`, `06_REVIEWER_HANDOFF.md`, `07`–`10`, and the frozen Phase-2C evidence in `11`/`12`.

2. **Independent mathematical verification**, performed from the supplement rather than from the authors' implementation, using exact rational arithmetic. Results are in §1. This matters for the novelty verdict: a claim cannot be scored against prior art until its actual content is pinned down, and several claims in the matrix are stated more broadly than the theorems support.

3. **Literature search** across the guessing-decoder family (GRAND, GRANDAB, SRGRAND, ORBGRAND, SOGRAND, GCD), guesswork/large-deviations theory, exact deletion- and insertion-channel maximum-likelihood (ML) decoding, sequence reconstruction and trace reconstruction, insertion/deletion/substitution (IDS) trellis decoding, and threshold aggregation. The searched space is the openly indexed primary literature; residual gaps are declared explicitly in §4 and one claim is scored `UNRESOLVED` on that basis.

---

## 1. Independent verification of the theorem chain

Novelty scoring below rests on these checks, all of which passed. They are reported because a reviewer should not classify a claim they have not first understood precisely.

| Obligation | Method | Result |
|---|---|---|
| Reversal identity `n(W(y\|x_B) − W(y\|x_A))/(1−p)^{n−4} = (1−2p)(np − 1 − 2p²)` | Exact rational recomputation, `n = 4…14`, six values of `p` spanning `(0, 1/2)` | **PASS**, exact equality in every case |
| Alignment multiplicities `1, 1, 1, n−3` at distances `0,1,2,3` for `x_A`; all-distance-one for `x_B` | Direct enumeration, same range | **PASS** |
| Strict best-history preference for `x_A`; aggregate preference for `x_B` iff `np > 1 + 2p²` | Same | **PASS**; sign flip confirmed numerically on both sides of the critical `p` |
| One-insertion sphere cardinality `n+1` from the stated generator | Asserted and checked on every generated set during the decoder replay below | **PASS**, exactly `n+1` distinct outputs in all cases |
| Decoder returns exact aggregate ML **and** the complete tie set | Independent reimplementation, 360 random trials, `n ∈ {6,8,10}`, random codes, exact rationals, compared against exhaustive aggregate ML with full tie enumeration | **PASS**, 0 mismatches |
| Stopping bound `S ≤ min{m, T + L_n − 1}` | Same 360 trials, realized `T` recorded per trial | **PASS**, 0 violations |
| `L_n = ⌊log_{(1−p)/p} n⌋ + 1`, including exact logarithmic boundaries | Exact comparison against `min{ℓ : ρ^ℓ < 1/n}` for five `p` values, `n = 2…199`; boundary case `p = 1/3`, `n = 2^j` checked separately | **PASS**, including the boundary case flagged in checklist item 9 |

No mathematical defect was found. The manuscript also does what the README asks on the oracle/wall-clock separation: it states the membership-oracle model explicitly, disclaims universal latency superiority, and reports the generator gate failure and the mixed branch-and-bound outcome rather than suppressing them. Claim discipline in `05_RESULTS_CLAIM_CHECKLIST.md` is met, item by item, in the text I read.

Two further quantitative checks, used in §4, were run:

- **Unseen-candidate bound tightness.** Exhaustive computation of `max W(y|x)` over words with `min_j d_j ≥ s+1`, at `p = 0.05`, `n ∈ {8,10,12}`. The ratio to `U_s` is exactly `1` at `s = 0` (attained only by the constant word, the sole word whose alignment distances are all equal) and falls to `0.37–0.64` at `s ∈ {1,2}`. `U_s` is therefore correct but not tight beyond the first shell.
- **Predictive model for the reported savings.** See §4.5.

---

## 2. Claim-by-claim verdicts

Legend: **DISTINCT** — no primary source found that anticipates the claim as stated. **PARTIALLY_ANTICIPATED** — the governing principle, or a strictly stronger form of it, is in the primary literature; the specific statement is a specialization or worked instance. **KNOWN** — the substance is established prior art. **UNRESOLVED** — search could not close the question.

### Summary

| # | Claim | Closest primary source | Verdict |
|---|---|---|---|
| C1 | Strict best-history / aggregate-ML reversal family, threshold `np_s > 1 + 2p_s²` | Bahl & Jelinek 1975; Sabary–Yaakobi–Yucovich ISIT 2020, Claims 1–2 | **PARTIALLY_ANTICIPATED** |
| C2 | Shell-certified exact decoder (Alg. 1, Prop. 2, Thm. 2) | Duffy–Li–Médard 2019; Wang–Liang–Yuan–Duffy–Médard–Ma 2025 (GCD stopping criteria); Fagin–Lotem–Naor 2003 | **PARTIALLY_ANTICIPATED** |
| C3 | Realization-dependent stopping `S ≤ min{m, T + L_n − 1}` | No direct antecedent located | **DISTINCT** |
| C4 | High-probability membership/query exponent `h_2(p_s)` | Duffy–Li–Médard 2019 §III; Christiansen–Duffy 2013; Arıkan 1996 | **KNOWN** |
| C5 | `n+1` one-insertion supersequence generator | Levenshtein (insertion ball cardinality `m+2`) | **KNOWN** (correctly disclaimed) |
| C6 | Threshold/monotone stopping principle | Fagin–Lotem–Naor 2003 | **KNOWN** (correctly disclaimed) |
| C7 | Membership-oracle code interface | Duffy–Li–Médard 2019 | **KNOWN** (correctly used as contrast) |
| C8 | Exact 996-trial finite-length evidence separating generation / membership / scoring / time | Original to this work | **DISTINCT** (with an interpretation caveat, §4.5) |
| C9 | Framing claim: first-hit noise guessing is not ML on a synchronization channel | Implicit in the additivity premise of GRAND; Ozaydin–Médard–Duffy 2022 workaround; embedding-number ML characterization | **PARTIALLY_ANTICIPATED** |
| C10 | Discovery-shell characterization `h_y(x) = min_j d_j` (Prop. 2) | Standard deletion-plus-substitution ball characterization | **PARTIALLY_ANTICIPATED** |
| C11 | Whether the exact composite appears in applied IDS/DNA-storage decoder literature, theses, or non-indexed venues | — | **UNRESOLVED** |

### C1 — Strict best-history / aggregate-ML reversal — `PARTIALLY_ANTICIPATED`

*Closest primary sources.* L. R. Bahl and F. Jelinek, "Decoding for channels with insertions, deletions, and substitutions with applications to speech recognition," *IEEE Trans. Inf. Theory*, 1975 (pagination to be confirmed at camera-ready). O. Sabary, E. Yaakobi and A. Yucovich, "The error probability of maximum-likelihood decoding over two deletion/insertion channels," *Proc. IEEE ISIT*, 2020 (arXiv:2001.05582), Claims 1 and 2.

*Comparison.* Bahl and Jelinek give the exact optimal decoder for channels with insertions, deletions and substitutions by forward recursion over an alignment/drift state, i.e. by summing over compatible edit histories rather than maximising over them. The aggregate objective the manuscript defends is that objective. Sabary et al. state the point in an even sharper form for the pure-deletion channel: `Pr{y | x} = p^{|x|−|y|} · Emb(x; y)`, so the ML rule is `argmax_c Emb(c; y)` — a pure alignment-multiplicity criterion in which no notion of a "best" alignment appears at all, because all compatible alignments carry identical weight. That is a *stronger* statement of the same phenomenon than Theorem 1: at `p_s = 0` the best-history ordering is not merely wrong, it is empty of information.

What the manuscript adds is the substitution-weighted binary instance and the closed-form boundary `np_s > 1 + 2p_s²`, together with a *strict* best-history preference in the opposite direction (Sabary's construction gives a best-history tie, not a strict reversal). I could not locate that specific family or that threshold in print, and the derivation is clean. But it is a worked example of a principle that is textbook in the IDS literature, obtainable in a few lines by anyone who writes down `W(y|x)`.

*Additional finding, adverse to the paper.* The family only reverses when `n p_s > 1 + 2 p_s²`, i.e. when the expected number of surviving substitutions exceeds roughly one. At the paper's own operating point `p_s = 0.05` this requires `n ≥ 21`: the example **does not reverse at `n = 16`**, one of the three simulated blocklengths. This regime restriction is not stated in the manuscript and should be.

### C2 — Shell-certified exact decoder — `PARTIALLY_ANTICIPATED`

*Closest primary sources.* K. R. Duffy, J. Li and M. Médard, *IEEE Trans. Inf. Theory* 65(7):4023–4040, 2019 (membership-oracle decoding, codebook-agnostic, non-linear codes admitted). Q. Wang, J. Liang, P. Yuan, K. R. Duffy, M. Médard and X. Ma, "Guessing decoding of short blocklength codes," arXiv:2511.12108, 2025 — which unifies GRAND and guessing codeword decoding (GCD) and, in its own words, proves ML optimality *under appropriate stopping criteria*, including a rule that terminates once no unqueried candidate can beat the incumbent. See also X. Zheng and X. Ma, "A universal list decoding algorithm...", and P. Yuan, M. Médard, K. Galligan and K. R. Duffy on soft-output GRAND, which computes an explicit bound on the probability mass of the *unqueried* candidate set. R. Fagin, A. Lotem and M. Naor, *JCSS* 66(4):614–656, 2003.

*Comparison.* Decompose Algorithm 1 into its parts:

- membership-oracle access to an arbitrary code — Duffy–Li–Médard;
- enumeration of candidates in shells of increasing noise weight — Duffy–Li–Médard (GRANDAB uses exactly the Hamming-weight shell order and the same `Σ binom(n,i)` count);
- an admissible upper bound on every not-yet-generated candidate, held against a fully scored incumbent, with strict comparison to close ties — the standard branch-and-bound / threshold-algorithm stopping rule, and specifically the guessing-decoder stopping criterion in the GCD line of work and the unqueried-mass bound in soft-output GRAND;
- complete rather than first-hit scoring of discovered codewords — GCD already scores candidate codewords rather than accepting the first hit.

What is genuinely specific here is the *instantiation*: the observation that the one-deletion inverse-alignment enumeration has discovery shell exactly `h_y(x) = min_j d_j(x,y)`, which makes `U_s = p_s^{s+1}(1−p_s)^{m−s−1}` a valid bound on the *aggregate* likelihood of an unseen word, and the resulting complete-tie-set certificate. I found no publication that assembles this for the one-deletion-plus-BSC channel, and the assembly is correct and non-obvious in the specific sense that the aggregation step (an average over `n` alignments) is what forces the certificate to be compared against a non-averaged bound.

That is a competent specialisation, not a new decoding principle. Scored `PARTIALLY_ANTICIPATED` rather than `DISTINCT` because every structural element, including the stopping certificate that the matrix treats as the distinguishing feature, has a primary antecedent in the guessing-decoder literature the paper already cites in part.

*Minor technical observation.* `U_s` is attained only by the constant words `0^n`, `1^n` (the only words whose alignment distances are all equal, by the sliding recurrence). Independent computation at `p_s = 0.05` gives a true-to-bound ratio of `0.37–0.64` for `s ∈ {1,2}`. A refined bound over admissible distance profiles would tighten the certificate — modestly, not by a factor `n`. Worth a sentence; not a correctness issue.

### C3 — Realization-dependent stopping theorem — `DISTINCT`

*Closest primary sources.* GRAND guesswork bounds (Duffy–Li–Médard 2019) bound the number of queries by the rank of the realized noise sequence in the guessing order; for hard-decision BSC guessing this is `≤ Vol(n, T)`. No source located gives an analogue with an additive certification margin.

*Comparison.* For first-hit GRAND the decoder halts at the shell containing the true noise; there is nothing to certify, because the ordering itself is the proof of optimality. Here the ordering is *not* a likelihood ordering, so the decoder must keep searching past the shell in which the transmitted word was found until the incumbent provably dominates everything unseen. The extra `L_n(p_s) − 1 = ⌊log_{(1−p_s)/p_s} n⌋` shells are precisely the price of the `1/n` alignment average. That mechanism, and the resulting code-independent bound, I did not find anticipated.

*Weight.* Honest scoring: this is `DISTINCT` but it is a two-line consequence of the certificate once the certificate is in place, and it is realization-dependent, so it is an analysis instrument rather than an implementable early exit. It is the one theorem in the paper I would defend as new, and it is not, by itself, a flagship ISIT result.

### C4 — High-probability query exponent `h_2(p_s)` — `KNOWN`

*Closest primary sources.* Duffy, Li and Médard, 2019, §III and the accompanying guesswork analysis; M. M. Christiansen and K. R. Duffy, "Guesswork, large deviations and Shannon entropy," *IEEE Trans. Inf. Theory*, 2013; E. Arıkan, 1996.

*Comparison.* This is the finding most adverse to the manuscript's positioning, and the matrix's status line ("provisional distinct but mathematically direct") understates it. The GRAND analysis establishes that guesswork concentrates, with high probability, at `2^{nH}` where `H` is the Shannon entropy rate of the noise, while the *mean* guesswork sits at the Rényi-`1/2` value `2^{nH_{1/2}}`; the published exposition of GRAND makes the typical-set picture explicit, with the layer at `2^{nH}` marked as the core of the Shannon typical set. For a binary symmetric channel with crossover `p_s` this is `2^{n h_2(p_s)}` — the manuscript's exponent, verbatim.

The manuscript's derivation is Hoeffding concentration on `T` plus the Hamming-ball volume bound, applied to `m = n−1` coordinates, with the deletion contributing a factor `n+1` that is absorbed into `2^{o(n)}`. So the operative content of Corollary 1 is: *a single deletion multiplies the query count by a polynomial factor and therefore does not change the classical exponent.* That is true, and it is worth one sentence, but it is not a new exponent and should not be presented as a headline contribution.

The genuinely useful and non-duplicative material in this section is the **finite-confidence cap** `(n+1)·Vol(m, min{m, τ_δ + L_n − 1})` and Table II, which is channel-specific, computable and not a restatement of anything I found. That is what to promote.

### C5 — `n+1` one-insertion supersequence generator — `KNOWN`

Insertion-ball cardinality `m+2` for a binary word of length `m` is Levenshtein's, from the 1960s. The manuscript and supplement both label it classical and explicitly decline to claim it. Correct handling; no change needed. The Phase-2C finding that this generator reduces attempts by `≈1.94×` yet fails its own wall-clock gate is reported honestly and should stay reported.

### C6 — Threshold principle — `KNOWN`

Fagin–Lotem–Naor is the right citation and the manuscript disclaims ownership. I would add that the closer-to-home antecedent is the stopping-criterion analysis in the guessing-decoder literature (C2), because a coding-theory reviewer will reach for that comparison before reaching for middleware aggregation.

### C7 — Membership-oracle interface — `KNOWN`

Duffy–Li–Médard. The manuscript uses it as contrast, not as property. Correct. The contrast is also sharper than the manuscript states: the GRAND ML guarantee is contingent on the channel being additive so that noise-effect order induces codeword-likelihood order. Naming that premise explicitly is the cleanest way to motivate the whole paper.

### C8 — Exact finite-length evidence — `DISTINCT`, with a caveat

The 996-trial frozen campaign, exact 512-bit integer scoring with no floating-point stopping comparison, three code families, and the four-way separation of generation, membership, scoring and wall-clock cost is original measurement, and the audit trail (immutable commit, build hash, source hash, preregistered gates, zero validation violations, zero censoring) is better than the norm for a four-page conference paper. The spot checks I ran against `11_PHASE2C_FROZEN_REPORT.json` reproduce every number quoted in the manuscript: median stop shell 1 in all five `n = 32` cells; `Q_mem` medians 954–972; `Q_score` medians 1.5–13.5; savings `6.99×10⁵`–`4.98×10⁶`; 10th-percentile savings `≥1.91×10⁵` for `k = 21` and `≥1.86×10⁶` for `k ≥ 24`; median exhaustive/decoder wall-clock ratio 465.6 over 16 `k = 21` calibrations; faster than branch-and-bound in four of five `n = 32` cells (ratios 0.99, 1.67, 1.20, 2.39, 2.18). The caveat is in §4.5 and concerns interpretation, not integrity.

### C9 — "First-hit noise guessing is not ML here" — `PARTIALLY_ANTICIPATED`

This is the paper's framing claim. It is correct, but it is a corollary of a premise already stated in the source it contrasts against: GRAND's optimality argument requires that the guessing order be a likelihood order over candidates, which holds for additive channels. That synchronization channels break this is the reason B. Ozaydin, M. Médard and K. R. Duffy (GLOBECOM 2022, arXiv:2210.16187) reach for a padding scheme to convert insertion/deletion effects into something a noise-guessing receiver can handle, rather than applying GRAND directly. The manuscript should say this explicitly — it strengthens the motivation and pre-empts the obvious reviewer objection that the observation is folklore.

### C10 — Discovery-shell characterization — `PARTIALLY_ANTICIPATED`

Proposition 2 says the inverse-alignment enumeration reaches `x` by shell `s` iff `min_j d_j(x,y) ≤ s`. That is a restatement of the standard characterization of the one-deletion-plus-`s`-substitution ball around `y`, in the direction that matters for enumeration. Correct, cleanly proved in both directions, and worth keeping as a lemma; not a novel object.

### C11 — Residual search gap — `UNRESOLVED`

I could not exhaustively clear the applied IDS/DNA-storage decoder literature, dissertations, and implementation-focused venues for an equivalent shell-certified exact aggregate decoder. The nanopore/DNA-storage community routinely builds exact and near-exact IDS decoders and does not always publish the search machinery as a theoretical contribution. Before submission I would run a targeted check of recent nanopore and DNA-storage decoder theses and of any 2026 guessing-decoder work that post-dates my search window. Scoring this `UNRESOLVED` rather than silently assuming clearance is the honest disposition, and it is the specific risk that could downgrade C2 and C3.

---

## 3. Adverse findings the authors asked to be told about

Per the instruction that anything anticipating the strict reversal family, the shell certificate, the stopping theorem or the query exponent be reported even if it weakens the paper:

1. **The aggregate objective is not new and its clearest statement is older and stronger than Theorem 1.** Bahl–Jelinek (1975) already decode IDS channels by summing over alignments; Sabary–Yaakobi–Yucovich (ISIT 2020) reduce deletion-channel ML to the embedding number, in which alignment multiplicity *is* the entire criterion. Theorem 1 is a weighted instance of that. **This weakens C1 and C9.**
2. **The query exponent is the classical GRAND/guesswork exponent.** `h_2(p_s)` for a BSC is the standard high-probability guesswork exponent from Duffy–Li–Médard and the guesswork large-deviations line. **This weakens C4 to `KNOWN`.**
3. **The certificate is the standard guessing-decoder stopping rule.** ML-preserving stopping criteria based on bounding unqueried candidates are established in the GCD/soft-output GRAND line. **This weakens C2.**
4. **`02_Proof_Supplement`, `03_CLAIM_NOVELTY_MATRIX` and the manuscript bibliography omit Bahl–Jelinek entirely.** For an information-theory audience this is the single most conspicuous gap: it is the canonical primary source for exact aggregate IDS decoding, and its absence will read as incomplete positioning rather than as an oversight.
5. **The reversal family's regime restriction is unstated** (`n p_s > 1 + 2 p_s²`; fails at `n = 16, p_s = 0.05`).

### 4.5 The headline empirical saving is largely predicted by a one-line calculation the paper does not make

This is not a novelty finding, but it materially affects how the evidence should be presented, and a referee will find it.

Let `G = (n+1)·Vol(m, S)` be the number of distinct words generated by the stopping shell. For a code of size `2^k` behaving like a uniform random subset of `{0,1}^n`,

  `E[Q_score] ≈ 1 + (G − 1)·2^{k−n}`,  and hence  `|C| / Q_score → 2^n / G` once `2^{k−n}G ≫ 1`.

At `n = 32`, `S = 1`: `G = 33 × 32 = 1056`, so `2^n/G = 4.07×10⁶` — **independent of the code and of the rate.** Against the frozen data:

| Cell | `k` | Predicted `Q_score` | Observed median | Predicted savings | Observed savings |
|---|---|---|---|---|---|
| CRC linear `R≈2/3` | 21 | 1.52 | 3.0 | 1.4×10⁶ | 6.99×10⁵ |
| Random linear `R≈2/3` | 21 | 1.52 | 1.5 | 1.4×10⁶ | 1.57×10⁶ |
| CRC linear `R≈3/4` | 24 | 5.12 | 4.0 | 3.3×10⁶ | 4.19×10⁶ |
| Random linear `R≈3/4` | 24 | 5.12 | 4.0 | 3.3×10⁶ | 4.19×10⁶ |
| Extended Hamming | 26 | 17.5 | 13.5 | 3.8×10⁶ | 4.98×10⁶ |

Every cell agrees within a factor of about two, and the predicted generated count `G = 1056` sits within 10 % of the measured `Q_mem` of 954–972. So the "1.5–13.5 codewords scored" and the "10⁵–10⁶ savings" are, to first order, consequences of `n`, the stopping shell, and code density — not of code structure and not of anything the search does beyond reaching shell one.

This cuts both ways, and the constructive reading is the stronger one: **add the prediction as a short proposition.** A decoder-complexity paper that predicts its own measurements to within a factor of two is far more persuasive than one that reports large ratios without a model, and it converts a table of impressive-looking numbers into a validated theory. Leaving it out invites a referee to supply the calculation themselves and conclude that the empirical section is thinner than it appears.

---

## 5. Bundle-hygiene items (non-scientific, but visible)

- `09_PHASE2D_REPORT.md` records the manuscript build as `NO_LATEXMK`, pages `None`, yet the bundle ships a compiled 4-page PDF built with pdfTeX. The automated build audit therefore did not verify the shipped artifact. Reconcile before sending to a venue.
- `12_PHASE2C_FROZEN_DECISION.json` reports `bestpath_selected_disagreements = 376` while `11_PHASE2C_FROZEN_REPORT.json` reports `420` in the campaign summary and `376` in the nested decision. `05_RESULTS_CLAIM_CHECKLIST.md` writes "376/420". Define the two populations explicitly, or drop one.
- `06_REVIEWER_HANDOFF.md` lists paths (`manuscript/…`, `audit/…`) that do not match the shipped layout (`01_…`, `03_…`), and offers a four-label decision vocabulary that differs from the one in `00_README_FOR_REVIEWER.md`. Harmonise.
- The supplement is dated 3 August 2026 and the frozen run is timestamped the same day; the reproducibility statement names an immutable commit but the bundle contains no source. That is a defensible choice for a review package, but state where the repository lives.

---

## 6. Answers to the five handoff questions

1. **Are all theorems correct?** No defect found. Every obligation I could check independently passed, including the boundary conventions at `p_s = 0`, `p_s = 1/2`, and the exact-logarithm case in `L_n`. The `n = 4` and equality-boundary cases in checklist item 3 pass.
2. **Is any contribution directly anticipated?** Yes — C4 in substance (`KNOWN`), and C1, C2, C9, C10 in principle (`PARTIALLY_ANTICIPATED`). C3 stands as `DISTINCT`. C11 is `UNRESOLVED`.
3. **Is the query result substantial enough for ISIT?** No. The exponent is the classical guesswork exponent transported across a polynomial factor; a symposium referee will say so. The finite-confidence caps and the stopping theorem are solid workshop-scale results.
4. **Are the empirical claims correctly separated?** Yes, and unusually carefully. The separation of `Q_gen`, `Q_mem`, `Q_score` and wall-clock is the paper's most defensible contribution. The missing piece is the predictive model in §4.5, not the separation.
5. **Which single change would most improve the paper without broadening the channel model?** Add the random-coding prediction of `Q_score` and the resulting savings law `2^n/((n+1)Vol(m,S))`, and demote Corollary 1 to a remark. That single move replaces a known exponent with an original, verified, quantitative model of the paper's own measurements, and it costs no new simulation.

---

## 7. Recommendation

# `ITW_READY_AFTER_REPAIR`

**Justification.** The theorem chain is correct — independently verified, not merely read — and the claim discipline is exemplary: the paper already disclaims universal latency superiority, reports a failed preregistered gate, reports the cells where it loses to the comparator, and refuses to read its own tie-set statistics as evidence of pathwise failure. That is the behaviour of a serious submission and it should not be diluted.

Against that, the novelty ledger does not support a symposium claim. Of the four advertised contributions, one is `KNOWN` in substance (the exponent), two are `PARTIALLY_ANTICIPATED` (the reversal family, the certified decoder), one is `DISTINCT` but is a short consequence of the certificate (the stopping theorem), and the empirical contribution — which is genuinely original as measurement — is currently presented without the model that explains it. A submission built on a specialisation plus a direct exponent transfer, with the canonical primary source for exact aggregate synchronization decoding uncited, would not survive ISIT review, and I do not recommend sending it there.

It is, however, a good fit for a workshop, where a narrow, exactly-scoped, fully audited result on a clearly delimited channel is welcome. The required repairs are bounded and need no new simulation:

1. Cite Bahl–Jelinek and position Theorem 1 explicitly as a *weighted, strict* instance of an established aggregate-versus-path distinction; cite the embedding-number ML characterization as the pure-deletion limit.
2. State the reversal regime `n p_s > 1 + 2 p_s²` and note it fails at `n = 16, p_s = 0.05`.
3. Demote Corollary 1 to a remark: state plainly that the exponent is the classical guesswork exponent and that the content is the polynomial cost of one deletion. Promote Table II and the finite-confidence cap in its place.
4. Position the shell certificate against the guessing-decoder stopping-criterion literature (GCD, soft-output GRAND unqueried-mass bounds), not only against threshold aggregation, and state what the one-deletion aggregation forces that additive stopping rules do not.
5. Add the `Q_score` prediction and the `2^n/((n+1)Vol(m,S))` savings law as a proposition, with the validation table.
6. Name GRAND's additivity premise explicitly in the introduction as the reason first-hit does not transfer.

With those six changes the paper is, in my judgement, a defensible workshop contribution: a correct, certified, fully audited exact decoder for a precisely delimited synchronization model, with one new stopping theorem and an original quantitative account of its own finite-length behaviour. Without them — in particular without (1) and (3) — it will draw the objection that its headline theorem is a known exponent and its motivating example a known phenomenon, and I would then expect `MAJOR_REVISION` from most referees.

One closing note on scope, offered as a reviewer and not as a gate: the residual `UNRESOLVED` item (C11) is the one thing that could move the verdict downward, and it is cheap to close. Run it before submitting.
