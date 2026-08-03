from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import utc_now_iso, write_json


def decide(
    repair: dict[str, Any],
    proof: dict[str, Any],
    replay: dict[str, Any],
    targeted: dict[str, Any] | None,
) -> dict[str, Any]:
    correctness = (
        repair["status"] == "PASS"
        and proof["status"] == "PASS"
        and replay["status"] == "PASS"
    )
    specialization_gate = bool(
        targeted is not None and targeted.get("conference_specialization_candidate")
    )
    if not correctness:
        label = "BLOCKED_CORRECTNESS_OR_ARTIFACT_FAILURE"
        reason = "At least one artifact-integrity, proof-check, compiled-kernel, or exact replay check failed."
    elif specialization_gate:
        label = "BOUNDED_GO_TO_PHASE2C_CONFERENCE_EVIDENCE"
        reason = "The compiled exact certificate passed replay and produced repeated work plus end-to-end gains in the preregistered targeted cells."
    elif replay.get("targeted_pilot_authorized"):
        label = "NARROW_TARGETED_PILOT_DID_NOT_PASS_CONFERENCE_GATE"
        reason = "The compiled implementation passed the replay gate, but the targeted pilot did not establish repeated conference-level net gains."
    elif replay.get("exact_pass") and replay.get("kernel_speed_pass"):
        label = "NARROW_THEOREM_OR_ONE_TRIGGER_OPTIMIZATION"
        reason = "The exact compiled kernel is fast, but its current invocation policy does not make hard-case end-to-end decoding competitive enough to authorize new simulations."
    elif replay.get("exact_pass"):
        label = "NARROW_UAC_TO_MATHEMATICAL_RESULT"
        reason = "The exact shell-consistent bound remains correct, but the compiled replay did not meet the preregistered acceleration gate."
    else:
        label = "STOP_AND_REPAIR_SMALLEST_REPLAY_COUNTEREXAMPLE"
        reason = "The compiled implementation did not reproduce the frozen Phase 2A evidence exactly."
    return {
        "created_utc": utc_now_iso(),
        "label": label,
        "reason": reason,
        "execution_correctness_pass": correctness,
        "conference_specialization_gate_passed": specialization_gate,
        "conference_submission_ready": False,
        "external_proof_review_required": True,
        "external_novelty_review_required": True,
        "large_campaign_authorized": False,
        "note": "Even a bounded GO authorizes only the next defined evidence phase, not a paper-level novelty claim or Transactions extension.",
    }


def make_report(
    output: Path,
    repair: dict[str, Any],
    proof: dict[str, Any],
    build: dict[str, Any],
    replay: dict[str, Any],
    targeted: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = decide(repair, proof, replay, targeted)
    write_json(output / "SCIENTIFIC_DECISION.json", decision)
    target_text = (
        "Not run: replay gate did not authorize new trials."
        if targeted is None
        else (
            f"Ran {targeted['trials']} trials in {targeted['cells']} cells; "
            f"standard-gate cells={targeted['standard_gate_cells']}, "
            f"tail-gate cells={targeted['tail_gate_cells']}, "
            f"specialization candidate={targeted['conference_specialization_candidate']}."
        )
    )
    markdown = f"""# FIBER-GRAND Paper I — Phase 2B-R1 manifest repair and replay gate

Generated: {utc_now_iso()}

## Scientific decision

**{decision['label']}**

{decision['reason']}

This is not a paper-level acceptance decision. Independent mathematical and novelty review remain mandatory.

## Phase 2A canonical artifact repair

- Status: **{repair['status']}**
- Original manifest entries: {repair['original_entries']}
- CSV CRLF-to-LF normalizations established exactly: {repair['crlf_normalization_count']}
- Verified post-manifest console appends: {repair['expected_post_manifest_console_append_count']}
- Unexplained mismatches: {repair['unexplained_mismatch_count']}
- Phase 2A was not rerun or altered.

The console discrepancy is accepted only because the old manifest hash equals a strict newline-boundary prefix and the exact four-line suffix agrees independently with `RUN_STATUS.json` and the return-ZIP SHA-256 sidecar.

## Proof and exact arithmetic

- Status: **{proof['status']}**
- Exact proof-support checks: {proof['exact_cases']}
- The proof source distinguishes arithmetic-operation complexity from bit complexity and handles the boundary cases explicitly.

## Compiled implementation

- Compiler: `{build['compiler_version']}`
- Source SHA-256: `{build['source_sha256']}`
- Binary SHA-256: `{build['binary_sha256']}`
- Exact integer arithmetic: fixed-capacity 512-bit multiword unsigned integers with overflow detection; this capacity covers the frozen Phase-2B range and no stopping comparison uses floating point.

## Frozen Phase 2A replay

- Synthetic nonuniform/zero-weight compiled-bound cross-checks: {replay['synthetic_bound_cases']} (mismatches: {replay['synthetic_bound_mismatches']})
- Frozen bound cases: {replay['bound_cases']}
- Decoder trials: {replay['trial_cases']}
- Bound mismatches: {replay['bound_mismatches']}
- Decoder mismatches: {replay['decode_mismatches']}
- U_AC kernel speedup over the Python reference: {replay['kernel_speedup']:.3g}x
- Hard cases: {replay['hard_case_count']}
- Median cost-aware compiled-mode/independent time on hard cases: {replay['hard_case_median_fast_over_ind_time']}
- Targeted pilot authorized by replay gate: **{replay['targeted_pilot_authorized']}**

## Targeted pilot

{target_text}

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
"""
    (output / "PHASE2B_R1_REPORT.md").write_text(
        markdown,
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "created_utc": utc_now_iso(),
        "artifact_repair": repair,
        "proof": proof,
        "build": build,
        "replay": replay,
        "targeted": targeted,
        "decision": decision,
    }
    write_json(output / "PHASE2B_R1_REPORT.json", report)
    return report
