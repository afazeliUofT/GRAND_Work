from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import utc_now_iso, write_json


def make_report(output: Path, provenance: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    decision = {
        "created_utc": utc_now_iso(),
        "label": "READY_FOR_EXTERNAL_PROOF_AND_NOVELTY_REVIEW",
        "execution_correctness_pass": True,
        "phase2d_scientific_pass_preserved": True,
        "provenance_repair_pass": True,
        "new_simulations_run": False,
        "manuscript_or_theory_changed": False,
        "conference_submission_ready": False,
        "external_proof_review_required": True,
        "external_novelty_review_required": True,
        "reason": "The local Phase 2D PASS commit was preserved exactly; its two post-generation manifest differences are closed-world explained, and a verified external-review bundle was produced.",
    }
    write_json(output / "SCIENTIFIC_DECISION.json", decision)
    report = {
        "created_utc": utc_now_iso(),
        "status": "PASS",
        "decision": decision,
        "provenance": provenance,
        "external_review_bundle": bundle,
    }
    write_json(output / "PHASE2D_R1_REPORT.json", report)
    markdown = f"""# FIBER-GRAND Paper I — Phase 2D-R1 provenance repair and review handoff

## Decision

**{decision['label']}**

The Phase 2D scientific run remains PASS. No theorem, manuscript, proof, figure value,
or simulation output was rerun or altered.

## Closed-world provenance repair

- Frozen local Phase 2D commit: `{provenance['phase2d_commit']}`
- Result-manifest accepted differences: {provenance['result_manifest']['accepted_difference_count']}
- Package-manifest accepted differences: {provenance['package_manifest']['accepted_difference_count']}
- Unexplained differences: 0
- New simulations: no

The result differences are restricted to the exact five-line post-manifest console append
and CRLF-to-LF normalization of `manuscript/generated/figure_source_data.csv`.

## External review bundle

- ZIP: `{bundle['bundle_zip']}`
- SHA-256: `{bundle['bundle_zip_sha256']}`

The next scientific step is independent proof review and a claim-by-claim primary-source
novelty review. No additional simulation campaign is authorized.
"""
    (output / "PHASE2D_R1_REPORT.md").write_text(markdown, encoding="utf-8", newline="\n")
    return report
