from __future__ import annotations
import csv, hashlib, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, path)

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20), b''): h.update(chunk)
    return h.hexdigest()

def copytree(src: Path, dst: Path) -> None:
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src, dst)

def git_blob(repo: Path, commit: str, rel: str) -> bytes:
    p=subprocess.run(['git','-C',str(repo),'show',f'{commit}:{rel}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f'cannot read {commit}:{rel}: {p.stderr.decode(errors="replace")}')
    return p.stdout

def run_capture(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    p=subprocess.run(cmd,cwd=str(cwd) if cwd else None,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return {'command':cmd,'returncode':p.returncode,'output':p.stdout}

def make_manifest(root: Path, out: Path, exclude: Iterable[Path] = ()) -> None:
    ex={p.resolve() for p in exclude}
    lines=[]
    for p in sorted(x for x in root.rglob('*') if x.is_file() and x.resolve() not in ex and x != out):
        lines.append(f'{sha256_file(p)}  {p.relative_to(root).as_posix()}')
    out.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
