from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts: object, bits: int = 64) -> int:
    payload = "\x1f".join(str(x) for x in parts).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[: bits // 8], "big")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)


def median(values: Sequence[float | int]) -> float:
    v = sorted(float(x) for x in values)
    if not v: raise ValueError("empty median")
    q = len(v)//2
    return v[q] if len(v)%2 else (v[q-1]+v[q])/2


def percentile(values: Sequence[float | int], q: float) -> float:
    v=sorted(float(x) for x in values)
    if not v: raise ValueError("empty percentile")
    rank=max(1, int(__import__('math').ceil(q*len(v))))
    return v[min(rank-1,len(v)-1)]


def run(args: Sequence[str], *, cwd: Path | None = None, log: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    t=time.perf_counter_ns()
    p=subprocess.run(list(map(str,args)), cwd=str(cwd) if cwd else None, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True); log.write_text(p.stdout, encoding="utf-8", newline="\n")
    p.elapsed_ns=time.perf_counter_ns()-t  # type: ignore[attr-defined]
    if check and p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str,args))}\n{p.stdout[-4000:]}")
    return p


def environment() -> dict[str, Any]:
    return {"created_utc":utc_now_iso(),"python":sys.version,"executable":sys.executable,"platform":platform.platform(),"machine":platform.machine(),"cpu_count":os.cpu_count()}


def make_manifest(root: Path, output: Path, exclude: Iterable[Path] = ()) -> None:
    ex={p.resolve() for p in exclude}; lines=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        if p.resolve()==output.resolve() or p.resolve() in ex: continue
        lines.append(f"{sha256_file(p)}  {p.relative_to(root).as_posix()}")
    output.write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")


def copytree(src: Path, dst: Path) -> None:
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src,dst,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
