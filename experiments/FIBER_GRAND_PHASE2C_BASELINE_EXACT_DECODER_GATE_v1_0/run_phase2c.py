#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from fiber_phase2c import __version__
from fiber_phase2c.campaign import run_campaign
from fiber_phase2c.compiler import build_cpp
from fiber_phase2c.report import make_report
from fiber_phase2c.theory_checks import run_theory_checks
from fiber_phase2c.util import (
    copytree_clean,
    environment_record,
    make_manifest,
    read_json,
    sha256_file,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bounded FIBER-GRAND Paper-I Phase-2C gate.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=PACKAGE_ROOT / "config" / "phase2c_default.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    return parser.parse_args()


def verify_repository(repo: Path, required_base: str) -> dict[str, object]:
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    ancestor = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", required_base, head], check=False)
    if ancestor.returncode != 0:
        raise RuntimeError(f"required Phase-2B-R1 commit {required_base} is not an ancestor of HEAD {head}")
    return {"head": head, "required_base_commit": required_base, "base_is_ancestor": True}


def create_return_zip(output: Path) -> tuple[Path, str]:
    zip_path = output / f"FIBER_GRAND_PHASE2C_RETURN_{output.name}.zip"
    hash_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    zip_path.unlink(missing_ok=True)
    hash_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in output.rglob("*") if p.is_file()):
            if path in {zip_path, hash_path}:
                continue
            archive.write(path, path.relative_to(output).as_posix())
    digest = sha256_file(zip_path)
    hash_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8", newline="\n")
    return zip_path, digest


def main() -> int:
    args = parse_args()
    repo = args.repo_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = read_json(args.config.resolve())

    write_json(
        output / "RUN_METADATA.json",
        {
            "created_utc": utc_now_iso(),
            "package_version": __version__,
            "package_root": str(PACKAGE_ROOT),
            "config": str(args.config.resolve()),
            "output": str(output),
            "argv": sys.argv,
            "environment": environment_record(),
        },
    )
    shutil.copy2(args.config.resolve(), output / "CONFIG_USED.json")
    copytree_clean(PACKAGE_ROOT / "docs", output / "docs")
    copytree_clean(PACKAGE_ROOT / "theory", output / "theory")

    status = "FAIL"
    decision_label = "NOT_AVAILABLE"
    try:
        context = verify_repository(repo, str(config["required_base_commit"]))
        write_json(output / "GIT_CONTEXT.json", context)

        theory = run_theory_checks(output / "theory", int(config["master_seed"]))
        if theory["status"] != "PASS":
            raise RuntimeError("Phase-2C theorem-support checks failed")

        binary, build = build_cpp(PACKAGE_ROOT / "cpp" / "fiber_grand_phase2c.cpp", args.cache_root.resolve(), output / "build")
        campaign = run_campaign(binary, config, output / "campaign")
        report = make_report(output, config, theory, build, campaign)
        decision_label = str(report["decision"]["label"])
        if report["status"] != "PASS":
            raise RuntimeError("Phase-2C exactness/execution report failed")
        status = "PASS"
        return_code = 0
    except Exception as exc:
        return_code = 1
        (output / "FAILURE_TRACEBACK.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        write_json(output / "FAILURE.json", {"created_utc": utc_now_iso(), "exception": repr(exc)})
        print(f"[phase2c] ERROR: {exc!r}", file=sys.stderr, flush=True)
    finally:
        write_json(output / "RUN_STATUS.json", {"created_utc": utc_now_iso(), "status": status, "decision": decision_label})
        (output / "PACKAGE_MANIFEST_SCOPE.md").write_text(
            "# Package-generated manifest scope\n\n"
            "`MANIFEST.sha256` covers the package-created result artifacts except the local return ZIP, "
            "its sidecar, and `PACKAGE_CONSOLE.log`. The console log is a live stream owned by the parent "
            "WSL wrapper and receives final status lines after this child creates its manifest. The wrapper's "
            "later `COMMIT_READY_MANIFEST.sha256` covers the exact committed console log and sidecar.\n",
            encoding="utf-8", newline="\n",
        )
        zip_path = output / f"FIBER_GRAND_PHASE2C_RETURN_{output.name}.zip"
        hash_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
        make_manifest(
            output, output / "MANIFEST.sha256",
            exclude=[zip_path, hash_path, output / "PACKAGE_CONSOLE.log"],
        )
        zip_path, digest = create_return_zip(output)
        print(f"[phase2c] status={status}", flush=True)
        print(f"[phase2c] decision={decision_label}", flush=True)
        print(f"[phase2c] output={output}", flush=True)
        print(f"[phase2c] return_zip={zip_path}", flush=True)
        print(f"[phase2c] return_zip_sha256={digest}", flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
