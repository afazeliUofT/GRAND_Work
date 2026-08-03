# Results and claim-discipline checklist

- [ ] State that `|C|/Q_score` measures avoided complete codeword-likelihood evaluations, not universal latency.
- [ ] State that `|C|/Q_mem` is separate from scoring and depends on membership-test cost.
- [ ] State that exhaustive `n=32` speed calibration contains 16 cases, limited to `k=21`.
- [ ] State that branch-and-bound completed on a selected capped subset and is not an instance-optimal benchmark.
- [ ] Report that FIBER was faster in four of five `n=32` branch-calibration cells but not universally.
- [ ] Report that the distinct insertion generator failed its own wall-clock gate despite reducing attempts.
- [ ] Do not report the 376/420 selected-representative differences as strict pathwise ML errors.
- [ ] Report zero strict disjoint empirical tie-set cases if best-path finite results are mentioned.
- [ ] Do not interpret high ML block-error rates as decoder incorrectness; exact decoders agree on ML.
- [ ] Keep the channel fixed to one uniform deletion and hard BSC substitutions.
- [ ] Do not extend results to insertions, multiple deletions, soft information, transducers, or hardware.
- [ ] Keep `U_AC` out of the practical main claim; it is a mathematical/optional certificate only.
