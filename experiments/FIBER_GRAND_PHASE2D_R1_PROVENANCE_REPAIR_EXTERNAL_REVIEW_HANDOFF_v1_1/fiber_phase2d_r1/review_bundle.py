from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import copy_blob, create_zip_from_directory, sha256_file, utc_now_iso, write_json, write_tree_manifest


REVIEW_FILES: tuple[tuple[str, str], ...] = (
    ("manuscript/FIBER_GRAND_Paper_I_Conference_Candidate.pdf", "01_Conference_Manuscript.pdf"),
    ("manuscript/FIBER_GRAND_Paper_I_Conference_Candidate.tex", "01_Conference_Manuscript.tex"),
    ("supplement/FIBER_GRAND_Paper_I_Proof_Supplement.pdf", "02_Proof_Supplement.pdf"),
    ("supplement/FIBER_GRAND_Paper_I_Proof_Supplement.tex", "02_Proof_Supplement.tex"),
    ("audit/CLAIM_NOVELTY_MATRIX.md", "03_CLAIM_NOVELTY_MATRIX.md"),
    ("audit/EXTERNAL_PROOF_REVIEW_CHECKLIST.md", "04_EXTERNAL_PROOF_REVIEW_CHECKLIST.md"),
    ("audit/RESULTS_CLAIM_CHECKLIST.md", "05_RESULTS_CLAIM_CHECKLIST.md"),
    ("audit/REVIEWER_HANDOFF.md", "06_REVIEWER_HANDOFF.md"),
    ("docs/KNOWN_LIMITATIONS.md", "07_KNOWN_LIMITATIONS.md"),
    ("docs/SCIENTIFIC_SCOPE.md", "08_SCIENTIFIC_SCOPE.md"),
    ("PHASE2D_REPORT.md", "09_PHASE2D_REPORT.md"),
    ("SCIENTIFIC_DECISION.json", "10_PHASE2D_SCIENTIFIC_DECISION.json"),
    ("frozen_evidence/PHASE2C_REPORT.json", "11_PHASE2C_FROZEN_REPORT.json"),
    ("frozen_evidence/SCIENTIFIC_DECISION.json", "12_PHASE2C_FROZEN_DECISION.json"),
)


def _readme() -> str:
    return """# Independent review request: FIBER-GRAND Paper I

This bundle contains a narrow conference manuscript, its complete proof supplement,
claim/novelty matrix, results checklist, and frozen Phase-2C/2D evidence summaries.

Please conduct two logically separate reviews.

1. **Proof review.** Check every theorem and boundary convention independently. For each
   obligation in `04_EXTERNAL_PROOF_REVIEW_CHECKLIST.md`, return PASS or the smallest
   counterexample/repair. Numerical checks support but do not replace proof.
2. **Novelty review.** Identify the closest primary source for each claim in
   `03_CLAIM_NOVELTY_MATRIX.md`; classify it as distinct, partially overlapping, known,
   or unresolved. Pay particular attention to GRAND complexity theory, exact deletion-
   channel search, weighted path-versus-string inference, and threshold aggregation.

Please also verify that the manuscript distinguishes oracle/query complexity from
wall-clock complexity and does not claim universal decoder optimality.

Requested final recommendation: `ISIT_READY`, `ITW_READY_AFTER_REPAIR`,
`MAJOR_REVISION`, or `REJECT`, with a concise scientific justification.
"""


def _email() -> str:
    return """Subject: Independent proof and novelty review request — FIBER-GRAND Paper I

Dear Professor [Name],

I would appreciate an independent review of the attached FIBER-GRAND Paper I bundle.
The work studies exact ML decoding for an arbitrary binary membership-testable code over
a channel with exactly one uniformly located deletion and independent substitutions.

Please assess two issues separately: (1) correctness of the theorem chain and proof
supplement, returning a smallest counterexample or precise repair for any failed item;
and (2) novelty of each candidate contribution relative to the closest primary prior
work, especially GRAND complexity, exact synchronization-error search, weighted
path-versus-string inference, and threshold aggregation.

The bundle contains a checklist and frozen evidence summaries. A brief final verdict of
ISIT-ready, ITW-ready after repair, major revision, or reject would be especially useful.

Sincerely,
Ali Fazeli
"""


def build_review_bundle(repo: Path, commit: str, config: dict[str, Any], output: Path) -> dict[str, Any]:
    source_root = config["phase2d_run_relative"]
    bundle = output / "FIBER_GRAND_Paper_I_External_Review_Bundle"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "00_README_FOR_REVIEWER.md").write_text(_readme(), encoding="utf-8", newline="\n")
    (bundle / "REVIEW_REQUEST_EMAIL.txt").write_text(_email(), encoding="utf-8", newline="\n")
    exported: list[dict[str, str]] = []
    for source_suffix, destination_name in REVIEW_FILES:
        source = f"{source_root}/{source_suffix}"
        destination = bundle / destination_name
        copy_blob(repo, commit, source, destination)
        exported.append({"source": source, "destination": destination_name, "sha256": sha256_file(destination)})
    manifest = bundle / "BUNDLE_MANIFEST.sha256"
    write_tree_manifest(bundle, manifest, exclude=[manifest])
    zip_path = output / "FIBER_GRAND_Paper_I_External_Review_Bundle_Phase2D_R1.zip"
    zip_hash = create_zip_from_directory(bundle, zip_path)
    sidecar = zip_path.with_suffix(zip_path.suffix + ".sha256")
    sidecar.write_text(f"{zip_hash}  {zip_path.name}\n", encoding="utf-8", newline="\n")
    report = {
        "created_utc": utc_now_iso(),
        "status": "PASS",
        "phase2d_commit": commit,
        "bundle_directory": bundle.name,
        "bundle_zip": zip_path.name,
        "bundle_zip_sha256": zip_hash,
        "exported_files": exported,
        "review_tasks": ["independent proof review", "claim-by-claim primary-source novelty review"],
        "new_simulations_run": False,
    }
    write_json(output / "EXTERNAL_REVIEW_BUNDLE.json", report)
    return report
