from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from .reference import chain_bound, independent_bound, mismatch_vector, scaled_score, uac_bound
from .util import utc_now_iso, write_json


def run_proof_checks(output: Path) -> dict[str, Any]:
    cases=0
    # Strict reversal and factorization over an exact rational grid.
    for a in (3,4,9,19,49,99):
        p=Fraction(1,a+1)
        for n in range(4,129):
            # Build in coordinate-0-first convention.
            def bits(s:str)->int:return sum((ch=="1")<<i for i,ch in enumerate(s))
            yy=bits("0"*(n-3)+"10");xa=bits("0"*(n-3)+"101");xb=0
            da=mismatch_vector(xa,yy,n);db=mismatch_vector(xb,yy,n)
            if da != (3,)*(n-3)+(2,1,0) or db != (1,)*n: raise AssertionError("reversal multiplicity")
            cond=n*p>1+2*p*p
            if (scaled_score(xb,yy,n,a)>scaled_score(xa,yy,n,a))!=cond:raise AssertionError("reversal condition")
            cases+=1
    # Bound hierarchy including exhausted streams and zero deletion weights.
    for n in range(2,11):
        for y in (0,(1<<(n-1))-1,((1<<(n-1))//3)):
            for r in ((0,)*n,(1,)*n,tuple(i%3 for i in range(n)),(n,)*n):
                weights=tuple(0 if i%4==0 else i+1 for i in range(n))
                ac=uac_bound(y,r,n,4,weights);cr=chain_bound(y,r,n,4,weights);ind=independent_bound(r,n,4,weights)
                if not ac<=cr<=ind:raise AssertionError((n,y,r,ac,cr,ind))
                cases+=1
    # Boundary statements: p=0 and p=1/2 are checked algebraically in the proof source.
    report={"created_utc":utc_now_iso(),"status":"PASS","exact_cases":cases,"boundary_review":{"p_s=0":"certificate remains valid; strict-gain results collapse to equality","p_s=1/2":"likelihood components are shell-independent; no strict shell-order gain","zero_q_j":"zero-weight streams may be omitted or retained with zero contribution","arithmetic_complexity":"O(n^3) arithmetic operations, not unit-cost bit complexity"}}
    output.mkdir(parents=True,exist_ok=True);write_json(output/"PROOF_CHECKS.json",report)
    return report
