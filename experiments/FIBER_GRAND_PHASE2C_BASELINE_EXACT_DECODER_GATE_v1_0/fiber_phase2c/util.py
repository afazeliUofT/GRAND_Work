from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_seed(*parts: object) -> int:
    payload = "\x1f".join(str(x) for x in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            path.write_text("", encoding="utf-8", newline="\n")
            return
        seen: list[str] = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.append(key)
        fieldnames = seen
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("median requires nonempty input")
    ordered = sorted(float(v) for v in values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return 0.5 * (ordered[n // 2 - 1] + ordered[n // 2])


def percentile_nearest_rank(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires nonempty input")
    if not 0 <= q <= 1:
        raise ValueError("q outside [0,1]")
    ordered = sorted(float(v) for v in values)
    if q == 0:
        return ordered[0]
    import math
    return ordered[max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))]


def environment_record() -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "cwd": os.getcwd(),
    }


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def make_manifest(root: Path, output: Path, exclude: Iterable[Path] = ()) -> None:
    excluded = {p.resolve() for p in exclude}
    files = [p for p in root.rglob("*") if p.is_file() and p.resolve() not in excluded and p.resolve() != output.resolve()]
    lines = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in sorted(files)]
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")


def run_capture(command: Sequence[str], *, cwd: Path | None = None, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(x) for x in command],
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
