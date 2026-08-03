#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from fiber_phase2b import __version__
from fiber_phase2b.artifact_repair import repair_phase2a_manifest
from fiber_phase2b.compiler import build_cpp
from fiber_phase2b.proof_checks import run_proof_checks
from fiber_phase2b.replay import run_replay
from fiber_phase2b.report import make_report
from fiber_phase2b.targeted import run_targeted
from fiber_phase2b.util import copytree, environment, make_manifest, read_json, sha256_file, utc_now_iso, write_json


def args()->argparse.Namespace:
    p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,required=True);p.add_argument("--config",type=Path,default=ROOT/"config"/"phase2b_default.json");p.add_argument("--output",type=Path,required=True);p.add_argument("--cache-root",type=Path,required=True);return p.parse_args()

def git_ok(repo:Path,base:str)->dict:
    head=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
    p=subprocess.run(["git","-C",str(repo),"merge-base","--is-ancestor",base,"HEAD"])
    if p.returncode:raise RuntimeError(f"required Phase 2A commit {base} is not an ancestor of HEAD {head}")
    return {"head":head,"base_commit":base,"base_is_ancestor":True}

def create_return(output:Path)->tuple[Path,str]:
    z=output/f"FIBER_GRAND_PHASE2B_RETURN_{output.name}.zip";z.unlink(missing_ok=True)
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as f:
        for p in sorted(x for x in output.rglob("*") if x.is_file() and x!=z):f.write(p,p.relative_to(output).as_posix())
    digest=sha256_file(z);z.with_suffix(z.suffix+".sha256").write_text(f"{digest}  {z.name}\n",encoding="utf-8",newline="\n");return z,digest

def main()->int:
    a=args();repo=a.repo_root.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);cfg=read_json(a.config.resolve())
    write_json(out/"RUN_METADATA.json",{"created_utc":utc_now_iso(),"version":__version__,"argv":sys.argv,"environment":environment(),"repo":str(repo)})
    shutil.copy2(a.config,out/"CONFIG_USED.json");copytree(ROOT/"docs",out/"docs");copytree(ROOT/"theory",out/"theory")
    status="FAIL"
    try:
        context=git_ok(repo,cfg["base_commit"]);write_json(out/"GIT_CONTEXT.json",context)
        repair=repair_phase2a_manifest(repo,cfg["base_commit"],cfg["phase2a_run_relative"],out/"phase2a_artifact_repair")
        if repair["status"]!="PASS":raise RuntimeError("Phase 2A artifact repair found unexplained mismatches")
        proof=run_proof_checks(out/"proof")
        binary,build=build_cpp(ROOT/"cpp"/"fiber_grand_phase2b.cpp",a.cache_root.resolve(),out/"build")
        replay=run_replay(repo,binary,cfg,out/"replay")
        if replay["status"]!="PASS":raise RuntimeError("compiled replay disagrees with frozen Phase 2A evidence")
        targeted=None
        if cfg["targeted_pilot"].get("enabled",True) and replay["targeted_pilot_authorized"]:
            targeted=run_targeted(binary,cfg,out/"targeted")
            if targeted["status"]!="PASS":raise RuntimeError("targeted pilot had an exact disagreement or censoring")
        make_report(out,repair,proof,build,replay,targeted)
        status="PASS";rc=0
    except Exception as e:
        rc=1;(out/"FAILURE_TRACEBACK.txt").write_text(traceback.format_exc(),encoding="utf-8",newline="\n");write_json(out/"FAILURE.json",{"created_utc":utc_now_iso(),"exception":repr(e)})
        print(f"[phase2b] ERROR: {e!r}",file=sys.stderr,flush=True)
    finally:
        write_json(out/"RUN_STATUS.json",{"created_utc":utc_now_iso(),"status":status})
        z=out/f"FIBER_GRAND_PHASE2B_RETURN_{out.name}.zip";h=z.with_suffix(z.suffix+".sha256")
        make_manifest(out,out/"MANIFEST.sha256",exclude=[z,h])
        z,digest=create_return(out)
        print(f"[phase2b] status={status}",flush=True);print(f"[phase2b] output={out}",flush=True);print(f"[phase2b] return_zip={z}",flush=True);print(f"[phase2b] return_zip_sha256={digest}",flush=True)
    return rc

if __name__=="__main__":raise SystemExit(main())
