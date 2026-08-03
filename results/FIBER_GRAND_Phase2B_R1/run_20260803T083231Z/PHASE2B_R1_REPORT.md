# FIBER-GRAND Paper I — Phase 2B-R1 manifest repair and replay gate

Generated: 2026-08-03T08:32:54+00:00

## Scientific decision

**NARROW_UAC_TO_MATHEMATICAL_RESULT**

The exact shell-consistent bound remains correct, but the compiled replay did not meet the preregistered acceleration gate.

This is not a paper-level acceptance decision. Independent mathematical and novelty review remain mandatory.

## Phase 2A canonical artifact repair

- Status: **PASS**
- Original manifest entries: 26
- CSV CRLF-to-LF normalizations established exactly: 5
- Verified post-manifest console appends: 1
- Unexplained mismatches: 0
- Phase 2A was not rerun or altered.

The console discrepancy is accepted only because the old manifest hash equals a strict newline-boundary prefix and the exact four-line suffix agrees independently with `RUN_STATUS.json` and the return-ZIP SHA-256 sidecar.

## Proof and exact arithmetic

- Status: **PASS**
- Exact proof-support checks: 858
- The proof source distinguishes arithmetic-operation complexity from bit complexity and handles the boundary cases explicitly.

## Compiled implementation

- Compiler: `g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`
- Source SHA-256: `2521275368a6403e728abceae6283c5f5eabaa5c7bc5bc1db65c55e8e911d074`
- Binary SHA-256: `ed19d9cdc5bb56bccf74a3a3959ab4a949e48f61014013c06d5d9c18c5c9008a`
- Exact integer arithmetic: fixed-capacity 512-bit multiword unsigned integers with overflow detection; this capacity covers the frozen Phase-2B range and no stopping comparison uses floating point.

## Frozen Phase 2A replay

- Synthetic nonuniform/zero-weight compiled-bound cross-checks: 198 (mismatches: 0)
- Frozen bound cases: 3360
- Decoder trials: 214
- Bound mismatches: 0
- Decoder mismatches: 0
- U_AC kernel speedup over the Python reference: 25.2x
- Hard cases: 15
- Median cost-aware compiled-mode/independent time on hard cases: 14.213690778278652
- Targeted pilot authorized by replay gate: **False**

## Targeted pilot

Not run: replay gate did not authorize new trials.

## Interpretation

1. A replay mismatch is a correctness failure, regardless of speed.
2. Kernel acceleration alone is insufficient; the exact certificate must improve end-to-end decoding on the hard observations where it saves search.
3. If the targeted gate does not pass, no broad Monte Carlo sweep is justified. The alignment-consistent result remains usable as a theorem or optional certificate.
4. The baseline independent-certificate decoder, its exact codeword-likelihood-evaluation savings, and fair exact baselines remain separate Paper-I evidence obligations.

## Files for review

- `phase2a_artifact_repair/MANIFEST_REPAIR_REPORT.json`
- `phase2a_artifact_repair/MANIFEST_REPAIR_NOTE.md`
- `proof/PROOF_CHECKS.json`
- `build/CPP_BUILD.json`
- `replay/REPLAY_REPORT.json`
- `replay/REPLAY_MISMATCHES.json`
- `replay/REPLAY_COMPARISON.csv`
- `targeted/TARGETED_REPORT.json` (only if authorized)
- `targeted/TARGETED_CELL_SUMMARY.csv` (only if authorized)
- `theory/FIBER_GRAND_Phase2B_Proof_Closure_v1.tex`
- `theory/PHASE2B_R1_MANIFEST_REPAIR_ARGUMENT.md`
- `SCIENTIFIC_DECISION.json`
