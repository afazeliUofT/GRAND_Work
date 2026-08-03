from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from .util import write_json

def check_claims(cfg: dict[str,Any], main_tex: Path, supplement_tex: Path, out: Path) -> dict[str,Any]:
    main=main_tex.read_text(encoding='utf-8')
    supp=supplement_tex.read_text(encoding='utf-8')
    normalize=lambda x:re.sub(r'\s+',' ',x.lower()).strip()
    low=normalize(main)
    failures=[]
    for phrase in cfg['forbidden_main_claim_phrases']:
        if normalize(phrase) in low: failures.append(f'forbidden phrase in main: {phrase}')
    for phrase in cfg['required_main_phrases']:
        if normalize(phrase) not in low: failures.append(f'missing required phrase: {phrase}')
    required_equations=['np_s>1+2p_s^2','Q_{\\rm gen},Q_{\\rm mem}','h_2(p_s)+o(1)']
    compact=lambda s:re.sub(r'\\s+','',s)
    cm=compact(main); cs=compact(supp)
    for eq in required_equations:
        ce=compact(eq)
        if ce not in cm: failures.append(f'main missing equation token {eq}')
        if ce not in cs: failures.append(f'supplement missing equation token {eq}')
    if normalize('no case where the first-shell codeword tie set was disjoint') not in low:
        failures.append('main does not disclose zero strict-disjoint empirical cases')
    if normalize('do not claim universal wall-clock optimality') not in low:
        failures.append('main lacks wall-clock limitation')
    result={'status':'PASS' if not failures else 'FAIL','failures':failures,
            'main_bytes':len(main.encode()),'supplement_bytes':len(supp.encode())}
    write_json(out/'CLAIM_CONSISTENCY_CHECK.json',result)
    if failures: raise RuntimeError('claim consistency check failed: '+'; '.join(failures))
    return result
