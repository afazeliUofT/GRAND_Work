from __future__ import annotations
import os, re, shutil, subprocess
from pathlib import Path
from typing import Any
from .util import run_capture, sha256_file, write_json

def _pages(pdf: Path) -> int | None:
    tool=shutil.which('pdfinfo')
    if not tool:return None
    p=subprocess.run([tool,str(pdf)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    m=re.search(r'^Pages:\s+(\d+)',p.stdout,re.M)
    return int(m.group(1)) if m else None

def _compile_one(tex: Path, log: Path) -> dict[str,Any]:
    latexmk=shutil.which('latexmk')
    if not latexmk:return {'status':'NO_LATEXMK','returncode':None,'output':''}
    p=subprocess.run([latexmk,'-pdf','-interaction=nonstopmode','-halt-on-error','-file-line-error',tex.name],
                     cwd=str(tex.parent),text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_text(p.stdout,encoding='utf-8',newline='\n')
    pdf=tex.with_suffix('.pdf')
    return {'status':'PASS' if p.returncode==0 and pdf.is_file() else 'FAIL','returncode':p.returncode,
            'output':p.stdout[-4000:],'pdf':str(pdf) if pdf.is_file() else None,'pages':_pages(pdf) if pdf.is_file() else None,
            'sha256':sha256_file(pdf) if pdf.is_file() else None}

def compile_documents(cfg: dict[str,Any], manuscript_dir: Path, supplement_dir: Path, out: Path) -> dict[str,Any]:
    out.mkdir(parents=True,exist_ok=True)
    main_tex=manuscript_dir/'FIBER_GRAND_Paper_I_Conference_Candidate.tex'
    supp_tex=supplement_dir/'FIBER_GRAND_Paper_I_Proof_Supplement.tex'
    main=_compile_one(main_tex,out/'MAIN_LATEX.log')
    supp=_compile_one(supp_tex,out/'SUPPLEMENT_LATEX.log')
    failures=[]
    if main['status']=='PASS':
        if main['pages'] is not None and not (cfg['minimum_main_pdf_pages']<=main['pages']<=cfg['maximum_main_pdf_pages']):
            failures.append(f"main page count {main['pages']} outside contract")
    elif main['status']!='NO_LATEXMK': failures.append('main LaTeX compilation failed')
    if supp['status']=='PASS':
        if supp['pages'] is not None and supp['pages']>cfg['maximum_supplement_pdf_pages']:
            failures.append(f"supplement page count {supp['pages']} exceeds contract")
    elif supp['status']!='NO_LATEXMK': failures.append('supplement LaTeX compilation failed')
    result={'status':'PASS' if not failures else 'FAIL','main':main,'supplement':supp,'failures':failures,
            'latexmk_available':bool(shutil.which('latexmk'))}
    write_json(out/'LATEX_BUILD.json',result)
    return result
