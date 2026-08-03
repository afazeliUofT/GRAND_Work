#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from fiber_phase2a import __version__
from fiber_phase2a.pilot import run_pilot
from fiber_phase2a.report import make_report
from fiber_phase2a.util import (
    copytree_clean,
    environment_record,
    make_manifest,
    read_json,
    sha256_file,
    utc_now_iso,
    write_json,
)
from fiber_phase2a.validation import run_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bounded FIBER-GRAND Phase-2A scientific gate.")
    parser.add_argument("--config", type=Path, default=PACKAGE_ROOT / "config" / "phase2a_default.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validation-only", action="store_true")
    return parser.parse_args()


def return_zip_paths(output: Path) -> tuple[Path, Path]:
    run_id = output.name
    zip_path = output / f"FIBER_GRAND_PHASE2A_RETURN_{run_id}.zip"
    return zip_path, zip_path.with_suffix(zip_path.suffix + ".sha256")


def create_return_zip(output: Path, zip_path: Path, hash_path: Path) -> tuple[Path, Path]:
    zip_path.unlink(missing_ok=True)
    hash_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in output.rglob("*") if p.is_file()):
            if path in {zip_path, hash_path}:
                continue
            zf.write(path, arcname=path.relative_to(output).as_posix())
    digest = sha256_file(zip_path)
    hash_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    return zip_path, hash_path


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = read_json(args.config.resolve())
    write_json(output / "RUN_METADATA.json", {
        "package_version": __version__,
        "created_utc": utc_now_iso(),
        "package_root": str(PACKAGE_ROOT),
        "config_path": str(args.config.resolve()),
        "output": str(output),
        "argv": sys.argv,
        "environment": environment_record(),
    })
    shutil.copy2(args.config.resolve(), output / "CONFIG_USED.json")
    theory_out = output / "theory"
    copytree_clean(PACKAGE_ROOT / "theory", theory_out)
    docs_out = output / "docs"
    copytree_clean(PACKAGE_ROOT / "docs", docs_out)

    status = "FAIL"
    try:
        validation = run_validation(output / "validation", int(config["master_seed"]))
        if validation["status"] != "PASS":
            raise RuntimeError("Exact validation failed; pilot is scientifically unauthorized.")
        if args.validation_only:
            report = {"validation_only": True, "validation_status": validation["status"]}
            write_json(output / "PHASE2A_REPORT.json", report)
        else:
            pilot = run_pilot(config, output / "pilot")
            report = make_report(output, validation, pilot, config)
        status = "PASS"
        return_code = 0
    except Exception as exc:
        return_code = 1
        (output / "FAILURE_TRACEBACK.txt").write_text(traceback.format_exc(), encoding="utf-8")
        write_json(output / "FAILURE.json", {"status": "FAIL", "exception": repr(exc), "created_utc": utc_now_iso()})
        print(f"[phase2a] ERROR: {exc!r}", file=sys.stderr, flush=True)
    finally:
        write_json(output / "RUN_STATUS.json", {"status": status, "created_utc": utc_now_iso()})
        zip_path, hash_path = return_zip_paths(output)
        make_manifest(output, output / "MANIFEST.sha256", exclude=[zip_path, hash_path])
        zip_path, hash_path = create_return_zip(output, zip_path, hash_path)
        print(f"[phase2a] status={status}", flush=True)
        print(f"[phase2a] output={output}", flush=True)
        print(f"[phase2a] return_zip={zip_path}", flush=True)
        print(f"[phase2a] return_zip_sha256={sha256_file(zip_path)}", flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
