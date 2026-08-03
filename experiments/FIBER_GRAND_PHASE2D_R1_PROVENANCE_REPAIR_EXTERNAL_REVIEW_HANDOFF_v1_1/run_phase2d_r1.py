#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fiber_phase2d_r1.provenance import run_provenance_repair
from fiber_phase2d_r1.report import make_report
from fiber_phase2d_r1.review_bundle import build_review_bundle
from fiber_phase2d_r1.util import (
    create_zip_from_directory,
    read_json,
    sha256_file,
    utc_now_iso,
    write_json,
    write_tree_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair Phase 2D provenance and build the external-review handoff.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "phase2d_r1_default.json")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = read_json(args.config.resolve())
    shutil.copy2(args.config.resolve(), output / "CONFIG_USED.json")
    write_json(output / "RUN_METADATA.json", {
        "created_utc": utc_now_iso(),
        "argv": sys.argv,
        "package_root": str(ROOT),
        "repository_root": str(repo),
        "new_simulations_authorized": False,
    })
    for document in (ROOT / "docs").glob("*"):
        if document.is_file():
            (output / "docs").mkdir(parents=True, exist_ok=True)
            shutil.copy2(document, output / "docs" / document.name)

    status = "FAIL"
    try:
        provenance = run_provenance_repair(repo, config, output / "phase2d_artifact_repair")
        bundle = build_review_bundle(repo, provenance["phase2d_commit"], config, output / "external_review")
        make_report(output, provenance, bundle)
        status = "PASS"
        return_code = 0
    except Exception as exc:
        return_code = 1
        (output / "FAILURE_TRACEBACK.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        write_json(output / "FAILURE.json", {"created_utc": utc_now_iso(), "exception": repr(exc)})
        print(f"[phase2d-r1] ERROR: {exc!r}", file=sys.stderr, flush=True)
    finally:
        write_json(output / "RUN_STATUS.json", {"created_utc": utc_now_iso(), "status": status})
        # This scientific-output manifest deliberately excludes wrapper-owned live logs.
        scientific_paths = [
            p for p in output.rglob("*")
            if p.is_file()
            and p.name not in {"SCIENTIFIC_OUTPUT_MANIFEST.sha256"}
            and not p.name.startswith("FIBER_GRAND_PHASE2D_R1_RETURN_")
            and p.name not in {"PACKAGE_CONSOLE.log", "UNIT_TESTS.log", "WRAPPER_EXECUTION.log", "WRAPPER_STATUS.json", "WRAPPER_METADATA.json", "RESULT_READY.txt", "GITHUB_REVIEW_POINTER.json"}
        ]
        write_tree_manifest(output, output / "SCIENTIFIC_OUTPUT_MANIFEST.sha256", exclude=[])
        # Rewrite to the frozen scientific scope only.
        from fiber_phase2d_r1.util import write_manifest_for_files
        write_manifest_for_files(output, scientific_paths, output / "SCIENTIFIC_OUTPUT_MANIFEST.sha256")
        return_zip = output / f"FIBER_GRAND_PHASE2D_R1_RETURN_{output.name}.zip"
        return_hash = create_zip_from_directory(output, return_zip)
        sidecar = return_zip.with_suffix(return_zip.suffix + ".sha256")
        sidecar.write_text(f"{return_hash}  {return_zip.name}\n", encoding="utf-8", newline="\n")
        decision = "NOT_AVAILABLE"
        decision_path = output / "SCIENTIFIC_DECISION.json"
        if decision_path.is_file():
            decision = read_json(decision_path).get("label", "UNKNOWN")
        print(f"[phase2d-r1] status={status}", flush=True)
        print(f"[phase2d-r1] decision={decision}", flush=True)
        print(f"[phase2d-r1] output={output}", flush=True)
        print(f"[phase2d-r1] return_zip={return_zip}", flush=True)
        print(f"[phase2d-r1] return_zip_sha256={return_hash}", flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
