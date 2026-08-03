from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from .util import run_capture, sha256_file, utc_now_iso, write_json


def build_cpp(source: Path, cache_root: Path, output_dir: Path) -> tuple[Path, dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which("g++") or shutil.which("clang++")
    if compiler is None:
        raise RuntimeError("No C++17 compiler found. Install build-essential and rerun.")
    version = run_capture([compiler, "--version"])
    source_hash = sha256_file(source)
    key_material = f"{source_hash}|{compiler}|{version.stdout.splitlines()[0] if version.stdout else ''}|-O3|-DNDEBUG|-std=c++17"
    cache_key = hashlib.sha256(key_material.encode()).hexdigest()[:20]
    cache_dir = cache_root / cache_key
    cache_dir.mkdir(parents=True, exist_ok=True)
    binary = cache_dir / "fiber_grand_phase2c"
    build_log = output_dir / "CPP_BUILD.log"
    command = [compiler, "-O3", "-DNDEBUG", "-std=c++17", "-Wall", "-Wextra", "-pedantic", str(source), "-o", str(binary)]
    result = run_capture(command)
    build_log.write_text("$ " + " ".join(command) + "\n" + result.stdout, encoding="utf-8", newline="\n")
    if result.returncode != 0:
        raise RuntimeError(f"C++ build failed; see {build_log}")
    self_test = run_capture([str(binary), "self-test"], timeout=120)
    (output_dir / "CPP_SELF_TEST.log").write_text(self_test.stdout, encoding="utf-8", newline="\n")
    if self_test.returncode != 0 or "SELF_TEST=PASS" not in self_test.stdout:
        raise RuntimeError("compiled self-test failed")
    report = {
        "created_utc": utc_now_iso(),
        "status": "PASS",
        "compiler": compiler,
        "compiler_version": version.stdout.splitlines()[0] if version.stdout else "unknown",
        "flags": ["-O3", "-DNDEBUG", "-std=c++17", "-Wall", "-Wextra", "-pedantic"],
        "source_sha256": source_hash,
        "binary_sha256": sha256_file(binary),
        "cache_key": cache_key,
        "binary_path": str(binary),
    }
    write_json(output_dir / "CPP_BUILD.json", report)
    return binary, report
