from __future__ import annotations
import csv, hashlib, io, json
from pathlib import Path
from typing import Any
from .util import git_blob, read_json, sha256_file, write_json

REQUIRED_FILES = {
    'decision': 'SCIENTIFIC_DECISION.json',
    'report': 'PHASE2C_REPORT.json',
    'campaign': 'campaign/CAMPAIGN_REPORT.json',
    'cells': 'campaign/CELL_SUMMARY.csv',
    'theory_checks': 'theory/THEORY_CHECKS.json',
    'theory_source': 'theory/FIBER_GRAND_Phase2C_Baseline_Exact_Decoder_Theorems.tex',
}

def export_and_validate(repo: Path, cfg: dict[str, Any], expected: dict[str, Any], out: Path) -> dict[str, Any]:
    commit=cfg['required_base_commit']; run_rel=cfg['phase2c_run_relative']
    out.mkdir(parents=True,exist_ok=True)
    hashes={}
    for key, suffix in REQUIRED_FILES.items():
        rel=f'{run_rel}/{suffix}'
        data=git_blob(repo,commit,rel)
        dest=out/suffix
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(data)
        hashes[key]={'repository_path':rel,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

    decision=json.loads((out/REQUIRED_FILES['decision']).read_text(encoding='utf-8'))
    report=json.loads((out/REQUIRED_FILES['report']).read_text(encoding='utf-8'))
    campaign=json.loads((out/REQUIRED_FILES['campaign']).read_text(encoding='utf-8'))
    theory=json.loads((out/REQUIRED_FILES['theory_checks']).read_text(encoding='utf-8'))
    cells=list(csv.DictReader((out/REQUIRED_FILES['cells']).open(encoding='utf-8',newline='')))

    failures=[]
    if decision.get('label') != expected['required_decision']:
        failures.append(f"decision label {decision.get('label')!r}")
    if not decision.get('execution_correctness_pass') or not decision.get('query_complexity_gate_pass'):
        failures.append('execution/query gate did not pass')
    if int(campaign.get('trial_count',-1)) != expected['trial_count']:
        failures.append('trial count mismatch')
    if int(campaign.get('natural_trials',-1)) != expected['natural_trials']:
        failures.append('natural trial count mismatch')
    if int(campaign.get('stress_trials',-1)) != expected['stress_trials']:
        failures.append('stress trial count mismatch')
    if int(campaign.get('validation_violation_count',-1)) != 0:
        failures.append('validation violations are nonzero')
    if theory.get('status') != 'PASS' or int(theory.get('exact_cases',-1)) != expected['theory_exact_cases']:
        failures.append('theory checks mismatch')

    by_id={r['cell_id']:r for r in cells}
    numeric_fields=['qmem','qscore','score_savings','p10_score_savings','membership_ratio','branch_ratio','stop_shell','p90_stop_shell']
    mapping={'qmem':'median_q_membership','qscore':'median_q_score','score_savings':'median_codeword_score_savings',
             'p10_score_savings':'p10_codeword_score_savings','membership_ratio':'median_codebook_membership_ratio',
             'branch_ratio':'median_branch_over_dedup_walltime','stop_shell':'median_stop_shell','p90_stop_shell':'p90_stop_shell'}
    verified=[]
    for e in expected['n32_cells']:
        r=by_id.get(e['cell_id'])
        if r is None:
            failures.append(f"missing cell {e['cell_id']}"); continue
        for k in numeric_fields:
            got=float(r[mapping[k]])
            target=float(e[k])
            if abs(got-target) > max(1e-10,1e-9*max(1.0,abs(target))):
                failures.append(f"{e['cell_id']} {k}: got {got}, expected {target}")
        if e['exhaustive_speedup'] is not None:
            got=float(r['median_exhaustive_over_dedup_walltime'])
            target=float(e['exhaustive_speedup'])
            if abs(got-target) > 1e-7*max(1.0,abs(target)):
                failures.append(f"{e['cell_id']} exhaustive speedup mismatch")
        if int(r['bestpath_strict_disjoint_count']) != 0:
            failures.append(f"{e['cell_id']} unexpected strict-disjoint empirical case")
        verified.append(e['cell_id'])

    result={'status':'PASS' if not failures else 'FAIL','commit':commit,'run_relative':run_rel,
            'hashes':hashes,'verified_n32_cells':verified,'failures':failures,
            'decision_label':decision.get('label'),'trial_count':campaign.get('trial_count'),
            'theory_exact_cases':theory.get('exact_cases')}
    write_json(out/'FROZEN_EVIDENCE_VALIDATION.json',result)
    if failures: raise RuntimeError('frozen evidence validation failed: '+ '; '.join(failures))
    return {'validation':result,'decision':decision,'report':report,'campaign':campaign,'theory':theory,'cells':cells}
