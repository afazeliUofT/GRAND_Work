#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fiber_phase2b import __version__
from fiber_phase2b.artifact_repair import repair_phase2a_manifest
from fiber_phase2b.compiler import build_cpp
from fiber_phase2b.proof_checks import run_proof_checks
from fiber_phase2b.replay import run_replay
from fiber_phase2b.report import make_report
from fiber_phase2b.targeted import run_targeted
from fiber_phase2b.util import (
    copytree,
    environment,
    make_manifest,
    read_json,
    sha256_file,
    utc_now_iso,
    write_json,
)

_RETURN_PREFIX = "FIBER_GRAND_PHASE2B_R1_RETURN_"
_LIVE_CONSOLE = "PACKAGE_CONSOLE.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the FIBER-GRAND Phase-2B-R1 manifest-repair and replay gate."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "phase2b_r1_default.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    return parser.parse_args()


def _require_ancestor(repo: Path, commit: str, label: str) -> None:
    process = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        head = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"required {label} commit {commit} is not an ancestor of HEAD {head}; {detail}"
        )


def git_context(repo: Path, config: dict[str, Any]) -> dict[str, Any]:
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    base = str(config["base_commit"])
    prior = str(config["required_prior_phase2b_commit"])
    _require_ancestor(repo, base, "frozen Phase-2A")
    _require_ancestor(repo, prior, "Phase-2B failed-run record")
    return {
        "head": head,
        "base_commit": base,
        "base_is_ancestor": True,
        "required_prior_phase2b_commit": prior,
        "prior_phase2b_is_ancestor": True,
    }


def _return_paths(output: Path) -> tuple[Path, Path]:
    archive = output / f"{_RETURN_PREFIX}{output.name}.zip"
    return archive, archive.with_suffix(archive.suffix + ".sha256")


def create_return(output: Path) -> tuple[Path, str]:
    archive, sidecar = _return_paths(output)
    archive.unlink(missing_ok=True)
    sidecar.unlink(missing_ok=True)
    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as handle:
        for path in sorted(candidate for candidate in output.rglob("*") if candidate.is_file()):
            if path in {archive, sidecar} or path.name == _LIVE_CONSOLE:
                continue
            handle.write(path, path.relative_to(output).as_posix())
    digest = sha256_file(archive)
    sidecar.write_text(
        f"{digest}  {archive.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    return archive, digest


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
            "version": __version__,
            "phase": "Phase 2B-R1 manifest repair and full replay gate",
            "argv": sys.argv,
            "environment": environment(),
            "repo": str(repo),
        },
    )
    shutil.copy2(args.config.resolve(), output / "CONFIG_USED.json")
    copytree(ROOT / "docs", output / "docs")
    copytree(ROOT / "theory", output / "theory")

    status = "FAIL"
    return_code = 1
    try:
        context = git_context(repo, config)
        write_json(output / "GIT_CONTEXT.json", context)

        repair_config = dict(config.get("artifact_repair", {}))
        repair = repair_phase2a_manifest(
            repo,
            str(config["base_commit"]),
            str(config["phase2a_run_relative"]),
            output / "phase2a_artifact_repair",
            repair_config,
        )
        if repair["status"] != "PASS":
            raise RuntimeError("Phase-2A R1 canonical artifact repair found a non-authorized mismatch")

        proof = run_proof_checks(output / "proof")
        if proof["status"] != "PASS":
            raise RuntimeError("exact proof-support checks did not pass")

        binary, build = build_cpp(
            ROOT / "cpp" / "fiber_grand_phase2b.cpp",
            args.cache_root.resolve(),
            output / "build",
        )
        replay = run_replay(
            repo,
            binary,
            config,
            output / "replay",
            phase2a_pilot=(
                output
                / "phase2a_artifact_repair"
                / "FROZEN_REPLAY_INPUTS"
                / "pilot"
            ),
        )
        if replay["status"] != "PASS":
            raise RuntimeError("compiled replay disagrees with frozen Phase-2A evidence")

        targeted = None
        if config["targeted_pilot"].get("enabled", True) and replay["targeted_pilot_authorized"]:
            targeted = run_targeted(binary, config, output / "targeted")
            if targeted["status"] != "PASS":
                raise RuntimeError("targeted pilot had an exact disagreement or censoring")

        make_report(output, repair, proof, build, replay, targeted)
        status = "PASS"
        return_code = 0
    except Exception as exc:
        (output / "FAILURE_TRACEBACK.txt").write_text(
            traceback.format_exc(),
            encoding="utf-8",
            newline="\n",
        )
        write_json(
            output / "FAILURE.json",
            {"created_utc": utc_now_iso(), "exception": repr(exc)},
        )
        print(f"[phase2b-r1] ERROR: {exc!r}", file=sys.stderr, flush=True)
    finally:
        write_json(
            output / "RUN_STATUS.json",
            {"created_utc": utc_now_iso(), "status": status},
        )
        (output / "PACKAGE_MANIFEST_SCOPE.md").write_text(
            "# Package-generated result manifest scope\n\n"
            "`MANIFEST.sha256` and the local return ZIP exclude `PACKAGE_CONSOLE.log` "
            "because the WSL wrapper is still writing that live log while the package "
            "finalizes. The wrapper later creates `COMMIT_READY_MANIFEST.sha256`, which "
            "covers the final committed console log and every other committed result "
            "artifact except the uncommitted return ZIP itself.\n",
            encoding="utf-8",
            newline="\n",
        )
        archive, sidecar = _return_paths(output)
        make_manifest(
            output,
            output / "MANIFEST.sha256",
            exclude=[archive, sidecar, output / _LIVE_CONSOLE],
        )
        archive, digest = create_return(output)
        print(f"[phase2b-r1] status={status}", flush=True)
        print(f"[phase2b-r1] output={output}", flush=True)
        print(f"[phase2b-r1] return_zip={archive}", flush=True)
        print(f"[phase2b-r1] return_zip_sha256={digest}", flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
