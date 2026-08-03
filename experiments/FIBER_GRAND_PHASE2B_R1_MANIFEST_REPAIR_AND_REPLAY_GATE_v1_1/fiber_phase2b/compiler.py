from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from .util import run, sha256_file, utc_now_iso, write_json


def build_cpp(source: Path, cache_root: Path, output: Path) -> tuple[Path, dict[str, Any]]:
    compiler = shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("No C++17 compiler was found. Install it in WSL with: sudo apt update && sudo apt install -y build-essential")
    version = run([compiler, "--version"], check=True).stdout.splitlines()[0]
    key = hashlib.sha256((sha256_file(source) + "\n" + version + "\n-O3 -DNDEBUG -std=c++17").encode()).hexdigest()[:20]
    build_dir = cache_root / key
    binary = build_dir / "fiber_grand_phase2b"
    build_dir.mkdir(parents=True, exist_ok=True)
    log = output / "CPP_BUILD.log"
    if not binary.is_file():
        run([compiler, "-O3", "-DNDEBUG", "-std=c++17", "-Wall", "-Wextra", "-pedantic", str(source), "-o", str(binary)], log=log)
    else:
        log.write_text(f"reused cached binary {binary}\n", encoding="utf-8", newline="\n")
    self_test = run([binary, "self-test"], log=output / "CPP_SELF_TEST.log")
    if "SELF_TEST=PASS" not in self_test.stdout:
        raise RuntimeError("compiled self-test did not report PASS")
    record = {"created_utc": utc_now_iso(), "compiler": compiler, "compiler_version": version, "source_sha256": sha256_file(source), "binary_sha256": sha256_file(binary), "cache_key": key, "flags": ["-O3","-DNDEBUG","-std=c++17"], "status": "PASS"}
    write_json(output / "CPP_BUILD.json", record)
    return binary, record
