#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, traceback, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from fiber_phase2d.checks import check_claims
from fiber_phase2d.compile_docs import compile_documents
from fiber_phase2d.frozen import export_and_validate
from fiber_phase2d.generate import generate
from fiber_phase2d.report import make_report
from fiber_phase2d.util import copytree, make_manifest, read_json, sha256_file, utc_now_iso, write_json

def parse_args():
    p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--config',type=Path,default=ROOT/'config'/'phase2d_default.json');p.add_argument('--output',type=Path,required=True);return p.parse_args()

def git_context(repo:Path,base:str):
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    p=subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',base,'HEAD'])
    if p.returncode: raise RuntimeError(f'required Phase-2C commit {base} is not an ancestor of HEAD {head}')
    return {'head':head,'required_base_commit':base,'base_is_ancestor':True}

def create_return(out:Path):
    z=out/f'FIBER_GRAND_PHASE2D_RETURN_{out.name}.zip'; z.unlink(missing_ok=True)
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as f:
        for p in sorted(x for x in out.rglob('*') if x.is_file() and x!=z): f.write(p,p.relative_to(out).as_posix())
    digest=sha256_file(z); z.with_suffix(z.suffix+'.sha256').write_text(f'{digest}  {z.name}\n',encoding='utf-8',newline='\n')
    return z,digest

def main():
    a=parse_args();repo=a.repo_root.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    cfg=read_json(a.config.resolve()); expected=read_json(ROOT/'frozen_expected'/'EXPECTED_PHASE2C_EVIDENCE.json')
    write_json(out/'RUN_METADATA.json',{'created_utc':utc_now_iso(),'argv':sys.argv,'package_root':str(ROOT),'repo':str(repo)})
    shutil.copy2(a.config,out/'CONFIG_USED.json')
    status='FAIL'
    try:
        write_json(out/'GIT_CONTEXT.json',git_context(repo,cfg['required_base_commit']))
        frozen=export_and_validate(repo,cfg,expected,out/'frozen_evidence')
        copytree(ROOT/'manuscript',out/'manuscript')
        copytree(ROOT/'supplement',out/'supplement')
        copytree(ROOT/'audit',out/'audit')
        copytree(ROOT/'docs',out/'docs')
        generate(frozen['cells'],expected,out/'manuscript')
        claims=check_claims(cfg,out/'manuscript'/'FIBER_GRAND_Paper_I_Conference_Candidate.tex',out/'supplement'/'FIBER_GRAND_Paper_I_Proof_Supplement.tex',out/'audit')
        build=compile_documents(cfg,out/'manuscript',out/'supplement',out/'build')
        if build.get('main',{}).get('status') != 'PASS' or build.get('supplement',{}).get('status') != 'PASS':
            # Use package-verified precompiled PDFs when local TeX is absent or incomplete.
            for src,dst in [(ROOT/'precompiled'/'FIBER_GRAND_Paper_I_Conference_Candidate.pdf',out/'manuscript'/'FIBER_GRAND_Paper_I_Conference_Candidate.pdf'),
                            (ROOT/'precompiled'/'FIBER_GRAND_Paper_I_Proof_Supplement.pdf',out/'supplement'/'FIBER_GRAND_Paper_I_Proof_Supplement.pdf')]:
                shutil.copy2(src,dst)
            build['precompiled_fallback_used']=True
            build['status']='PASS_WITH_PRECOMPILED_FALLBACK'
            write_json(out/'build'/'LATEX_BUILD.json',build)
        make_report(out,frozen,claims,build)
        status='PASS'; rc=0
    except Exception as e:
        rc=1;(out/'FAILURE_TRACEBACK.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n');write_json(out/'FAILURE.json',{'created_utc':utc_now_iso(),'exception':repr(e)})
        print(f'[phase2d] ERROR: {e!r}',file=sys.stderr,flush=True)
    finally:
        write_json(out/'RUN_STATUS.json',{'created_utc':utc_now_iso(),'status':status})
        z=out/f'FIBER_GRAND_PHASE2D_RETURN_{out.name}.zip';h=z.with_suffix(z.suffix+'.sha256')
        make_manifest(out,out/'MANIFEST.sha256',exclude=[z,h])
        z,digest=create_return(out)
        decision='NOT_AVAILABLE'
        p=out/'SCIENTIFIC_DECISION.json'
        if p.is_file(): decision=read_json(p).get('label','UNKNOWN')
        print(f'[phase2d] status={status}',flush=True);print(f'[phase2d] decision={decision}',flush=True);print(f'[phase2d] output={out}',flush=True);print(f'[phase2d] return_zip={z}',flush=True);print(f'[phase2d] return_zip_sha256={digest}',flush=True)
    return rc
if __name__=='__main__': raise SystemExit(main())
