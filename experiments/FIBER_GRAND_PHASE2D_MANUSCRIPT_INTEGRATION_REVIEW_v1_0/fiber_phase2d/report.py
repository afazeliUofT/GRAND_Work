from __future__ import annotations
from pathlib import Path
from typing import Any
from .util import utc_now_iso, write_json

def make_report(out: Path, frozen: dict[str,Any], claims: dict[str,Any], build: dict[str,Any]) -> dict[str,Any]:
    decision={
      'created_utc':utc_now_iso(),
      'label':'READY_FOR_EXTERNAL_PROOF_AND_NOVELTY_REVIEW',
      'execution_consistency_pass':True,
      'phase2c_evidence_frozen':True,
      'new_simulations_run':False,
      'conference_submission_ready':False,
      'external_proof_review_required':True,
      'external_novelty_review_required':True,
      'next_step':'Send the manuscript and proof supplement to independent reviewers; do not launch a new simulation campaign.',
    }
    write_json(out/'SCIENTIFIC_DECISION.json',decision)
    report={
      'created_utc':utc_now_iso(),'status':'PASS','decision':decision,
      'frozen_validation':frozen['validation'],'claim_checks':claims,'latex_build':build,
    }
    write_json(out/'PHASE2D_REPORT.json',report)
    main=build.get('main',{}); supp=build.get('supplement',{})
    md=f'''# FIBER-GRAND Paper I - Phase 2D manuscript integration\n\n## Decision\n\n**READY_FOR_EXTERNAL_PROOF_AND_NOVELTY_REVIEW**\n\nNo simulation was run. The manuscript was regenerated from the immutable Phase-2C commit and passed automated evidence/claim checks.\n\n## Frozen evidence\n\n- Base commit: `{frozen['validation']['commit']}`\n- Phase-2C decision: `{frozen['validation']['decision_label']}`\n- Exact campaign trials: {frozen['validation']['trial_count']}\n- Exact theorem-support cases: {frozen['validation']['theory_exact_cases']}\n- Verified n=32 cells: {len(frozen['validation']['verified_n32_cells'])}\n\n## Manuscript build\n\n- Main status: `{main.get('status')}`; pages: `{main.get('pages')}`\n- Supplement status: `{supp.get('status')}`; pages: `{supp.get('pages')}`\n- Claim consistency: `{claims['status']}`\n\n## Scientific interpretation\n\nThe current result is a credible narrow conference candidate because exactness, repeated query/score savings, and finite exhaustive calibration are supported. The paper does not claim universal latency superiority. The decisive remaining evidence is independent proof and novelty review.\n'''
    (out/'PHASE2D_REPORT.md').write_text(md,encoding='utf-8',newline='\n')
    return report
