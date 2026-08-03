# Exact next step after the Phase 2C run

Do not launch more simulations automatically.

- If the decision is `GO_PAPER_I_BASELINE_EXACT_DECODER`, the next phase is manuscript integration: independently review the proof source, refresh the novelty matrix, and write the narrow ISIT/ITW manuscript from the frozen Phase 0 scope and Phase 2C evidence.
- If the decision is `NARROW_TO_THEOREM_AND_QUERY_COMPLEXITY`, write an ITW-style theorem/query-complexity paper and do not claim practical latency superiority.
- If the decision is `NARROW_COMPLEXITY_TAIL_UNRESOLVED`, inspect only the censored natural cases and authorize at most one cap/diagnostic repair.
- If the decision begins with `STOP`, return the smallest counterexample or failed preregistered metric and stop the current Paper-I algorithmic route.

The next assistant review must use the pushed commit and result directory. It should then provide the theoretical/manuscript artifact and a new one-ZIP/one-wrapper package only if another WSL computation is scientifically necessary.
