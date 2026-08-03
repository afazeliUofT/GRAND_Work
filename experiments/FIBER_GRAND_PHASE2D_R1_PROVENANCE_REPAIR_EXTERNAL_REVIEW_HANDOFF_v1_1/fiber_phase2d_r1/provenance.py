from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from .util import (
    git_blob,
    git_files,
    git_text,
    parse_manifest_bytes,
    sha256_bytes,
    utc_now_iso,
    write_json,
)


def _capture_text(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def discover_phase2d_commit(repo: Path, config: dict[str, Any]) -> str:
    marker = f"{config['phase2d_run_relative']}/RUN_STATUS.json"
    probe = _capture_text([
        "git", "-C", str(repo), "log", "--all", "--format=%H%x09%s", "--", marker
    ])
    if probe.returncode != 0:
        raise RuntimeError(f"cannot search Phase 2D commit: {probe.stderr.strip()}")
    matches: list[str] = []
    for line in probe.stdout.splitlines():
        if "\t" not in line:
            continue
        commit, subject = line.split("\t", 1)
        if subject == config["phase2d_expected_subject"]:
            matches.append(commit)
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one local Phase 2D commit with subject "
            f"{config['phase2d_expected_subject']!r}; found {matches}"
        )
    commit = matches[0]
    ancestor = subprocess.run([
        "git", "-C", str(repo), "merge-base", "--is-ancestor",
        config["required_phase2c_commit"], commit,
    ], check=False)
    if ancestor.returncode != 0:
        raise RuntimeError("Phase 2D commit is not descended from the frozen Phase 2C GO commit")
    return commit


def _assert_paths_unchanged(repo: Path, commit: str, config: dict[str, Any]) -> None:
    relevant = [
        config["phase2d_run_relative"],
        config["phase2d_package_relative"],
        config["phase2d_wrapper_relative"],
        "results/FIBER_GRAND_Phase2D/LATEST.json",
    ]
    probe = _capture_text([
        "git", "-C", str(repo), "diff", "--name-only", f"{commit}..HEAD", "--", *relevant
    ])
    changed = [line for line in probe.stdout.splitlines() if line.strip()]
    if probe.returncode != 0 or changed:
        raise RuntimeError(f"Phase 2D paths changed after the frozen local commit: {changed}")
    unstaged = _capture_text(["git", "-C", str(repo), "diff", "--name-only", "--", *relevant])
    staged = _capture_text(["git", "-C", str(repo), "diff", "--cached", "--name-only", "--", *relevant])
    dirty = [line for line in (unstaged.stdout + staged.stdout).splitlines() if line.strip()]
    if unstaged.returncode != 0 or staged.returncode != 0 or dirty:
        raise RuntimeError(f"Phase 2D paths have uncommitted changes: {dirty}")


def _find_manifest_prefix(committed: bytes, expected_hash: str) -> int:
    boundaries = [0] + [index + 1 for index, value in enumerate(committed) if value == 0x0A]
    matches = [boundary for boundary in boundaries if sha256_bytes(committed[:boundary]) == expected_hash]
    if len(matches) != 1:
        raise RuntimeError(f"manifest-prefix match is not unique: {matches}")
    boundary = matches[0]
    if boundary >= len(committed):
        raise RuntimeError("manifest hash does not identify a strict prefix")
    return boundary


def _parse_sidecar(sidecar: bytes) -> tuple[str, str]:
    lines = sidecar.decode("utf-8").splitlines()
    if len(lines) != 1 or "  " not in lines[0]:
        raise RuntimeError("malformed Phase 2D return-ZIP sidecar")
    digest, filename = lines[0].split("  ", 1)
    if len(digest) != 64:
        raise RuntimeError("malformed Phase 2D return-ZIP digest")
    return digest, filename


def classify_console_append(
    *,
    committed: bytes,
    old_hash: str,
    repo: Path,
    commit: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    boundary = _find_manifest_prefix(committed, old_hash)
    suffix = committed[boundary:]
    if not suffix.endswith(b"\n"):
        raise RuntimeError("Phase 2D console append is not newline terminated")
    lines = suffix.decode("utf-8").splitlines()

    run_status = json.loads(git_text(repo, commit, f"{config['phase2d_run_relative']}/RUN_STATUS.json"))["status"]
    decision = json.loads(git_text(repo, commit, f"{config['phase2d_run_relative']}/SCIENTIFIC_DECISION.json"))["label"]
    sidecar_path = (
        f"{config['phase2d_run_relative']}/"
        f"FIBER_GRAND_PHASE2D_RETURN_{Path(config['phase2d_run_relative']).name}.zip.sha256"
    )
    sidecar_digest, zip_name = _parse_sidecar(git_blob(repo, commit, sidecar_path))
    absolute_run = (repo / config["phase2d_run_relative"]).resolve()
    expected_lines = [
        f"[phase2d] status={run_status}",
        f"[phase2d] decision={decision}",
        f"[phase2d] output={absolute_run}",
        f"[phase2d] return_zip={absolute_run / zip_name}",
        f"[phase2d] return_zip_sha256={sidecar_digest}",
    ]
    if lines != expected_lines:
        raise RuntimeError(f"unexpected Phase 2D console suffix: {lines!r}")
    if run_status != config["expected_status"] or decision != config["expected_decision"]:
        raise RuntimeError(f"unexpected Phase 2D semantics: status={run_status}, decision={decision}")

    local_zip = repo / config["phase2d_run_relative"] / zip_name
    local_zip_status = "NOT_PRESENT_ACCEPTABLE"
    local_zip_hash: str | None = None
    if local_zip.is_file():
        digest = hashlib.sha256(local_zip.read_bytes()).hexdigest()
        local_zip_hash = digest
        if digest != sidecar_digest:
            raise RuntimeError("local Phase 2D return ZIP disagrees with committed sidecar")
        local_zip_status = "MATCHES_COMMITTED_SIDECAR"

    prefix_terminal = committed[:boundary].decode("utf-8").splitlines()
    return {
        "diagnosis": "EXPECTED_POST_MANIFEST_CONSOLE_APPEND",
        "manifest_prefix_bytes": boundary,
        "manifest_prefix_sha256": old_hash,
        "committed_log_bytes": len(committed),
        "committed_sha256": sha256_bytes(committed),
        "appended_bytes": len(suffix),
        "appended_line_count": len(lines),
        "appended_lines": lines,
        "prefix_terminal_line": prefix_terminal[-1] if prefix_terminal else "<EMPTY_PREFIX>",
        "run_status_json": run_status,
        "scientific_decision_json": decision,
        "return_zip_sidecar": PurePosixPath(sidecar_path).name,
        "return_zip_sidecar_sha256": sidecar_digest,
        "local_return_zip_status": local_zip_status,
        "local_return_zip_sha256": local_zip_hash,
        "scientific_effect": "five deterministic status lines were appended after scientific-manifest creation; no manuscript, proof, audit, or numerical evidence changed",
    }


def classify_crlf_normalization(committed: bytes, old_hash: str, path: str) -> dict[str, Any]:
    if b"\r\n" in committed:
        raise RuntimeError(f"committed CSV is not canonical LF text: {path}")
    reconstructed = committed.replace(b"\n", b"\r\n")
    reconstructed_hash = sha256_bytes(reconstructed)
    if reconstructed_hash != old_hash:
        raise RuntimeError(f"CRLF reconstruction does not explain manifest mismatch for {path}")
    # Parsing both encodings must produce the same records.
    lf_rows = list(csv.reader(io.StringIO(committed.decode("utf-8"))))
    crlf_rows = list(csv.reader(io.StringIO(reconstructed.decode("utf-8"))))
    if lf_rows != crlf_rows:
        raise RuntimeError(f"CSV records changed under line-ending normalization: {path}")
    return {
        "diagnosis": "CRLF_TO_LF_NORMALIZATION",
        "path": path,
        "original_manifest_sha256": old_hash,
        "committed_sha256": sha256_bytes(committed),
        "reconstructed_crlf_sha256": reconstructed_hash,
        "row_count": len(lf_rows),
        "scientific_effect": "text line endings only; parsed CSV records are unchanged",
    }


def _write_canonical_manifest(repo: Path, commit: str, prefix: str, output: Path) -> int:
    files = git_files(repo, commit, prefix)
    lines: list[str] = []
    for repository_path in files:
        relative = PurePosixPath(repository_path).relative_to(PurePosixPath(prefix)).as_posix()
        lines.append(f"{sha256_bytes(git_blob(repo, commit, repository_path))}  {relative}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(files)


def repair_result_manifest(repo: Path, commit: str, config: dict[str, Any], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    run_relative = config["phase2d_run_relative"]
    manifest_path = f"{run_relative}/MANIFEST.sha256"
    manifest_blob = git_blob(repo, commit, manifest_path)
    entries = parse_manifest_bytes(manifest_blob)
    (output / "ORIGINAL_RESULT_MANIFEST.sha256").write_bytes(manifest_blob)

    mismatches: list[dict[str, Any]] = []
    for relative, old_hash in sorted(entries.items()):
        repository_path = f"{run_relative}/{relative}"
        committed = git_blob(repo, commit, repository_path)
        committed_hash = sha256_bytes(committed)
        if committed_hash == old_hash:
            continue
        if relative == "PACKAGE_CONSOLE.log":
            record = classify_console_append(
                committed=committed,
                old_hash=old_hash,
                repo=repo,
                commit=commit,
                config=config,
            )
            record.update({"path": relative, "original_manifest_sha256": old_hash})
            mismatches.append(record)
        elif relative == "manuscript/generated/figure_source_data.csv":
            mismatches.append(classify_crlf_normalization(committed, old_hash, relative))
        else:
            raise RuntimeError(f"unexplained Phase 2D result-manifest mismatch: {relative}")

    observed = sorted(record["path"] for record in mismatches)
    expected = sorted(config["expected_result_mismatch_paths"])
    if observed != expected:
        raise RuntimeError(f"unexpected result-manifest mismatch set: observed={observed}, expected={expected}")

    full_files = _write_canonical_manifest(
        repo, commit, run_relative, output / "CANONICAL_FULL_COMMITTED_RESULT_MANIFEST.sha256"
    )
    report = {
        "created_utc": utc_now_iso(),
        "status": "PASS",
        "phase2d_commit": commit,
        "phase2d_run": run_relative,
        "original_entries": len(entries),
        "full_committed_run_files": full_files,
        "accepted_difference_count": len(mismatches),
        "expected_post_manifest_console_append_count": sum(r["diagnosis"] == "EXPECTED_POST_MANIFEST_CONSOLE_APPEND" for r in mismatches),
        "crlf_normalization_count": sum(r["diagnosis"] == "CRLF_TO_LF_NORMALIZATION" for r in mismatches),
        "unexplained_mismatch_count": 0,
        "mismatches": mismatches,
        "scientific_interpretation": "The frozen Phase 2D scientific run is PASS. The original scientific-output manifest predated five deterministic console-status lines and Git LF normalization of one generated CSV. Canonical manifests now hash the exact local Phase 2D commit; no scientific computation or document is rerun or altered.",
    }
    write_json(output / "RESULT_MANIFEST_REPAIR_REPORT.json", report)
    return report


def repair_package_manifest(repo: Path, commit: str, config: dict[str, Any], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    package_relative = config["phase2d_package_relative"]
    manifest_path = f"{package_relative}/PACKAGE_MANIFEST.sha256"
    manifest_blob = git_blob(repo, commit, manifest_path)
    entries = parse_manifest_bytes(manifest_blob)
    (output / "ORIGINAL_PACKAGE_MANIFEST.sha256").write_bytes(manifest_blob)
    mismatches: list[dict[str, Any]] = []
    for relative, old_hash in sorted(entries.items()):
        repository_path = f"{package_relative}/{relative}"
        committed = git_blob(repo, commit, repository_path)
        if sha256_bytes(committed) == old_hash:
            continue
        if relative == "manuscript/generated/figure_source_data.csv":
            mismatches.append(classify_crlf_normalization(committed, old_hash, relative))
        else:
            raise RuntimeError(f"unexplained Phase 2D package-manifest mismatch: {relative}")
    observed = sorted(record["path"] for record in mismatches)
    expected = sorted(config["expected_package_mismatch_paths"])
    if observed != expected:
        raise RuntimeError(f"unexpected package-manifest mismatch set: observed={observed}, expected={expected}")
    full_files = _write_canonical_manifest(
        repo, commit, package_relative, output / "CANONICAL_FULL_COMMITTED_PACKAGE_MANIFEST.sha256"
    )
    report = {
        "created_utc": utc_now_iso(),
        "status": "PASS",
        "phase2d_commit": commit,
        "phase2d_package": package_relative,
        "original_entries": len(entries),
        "full_committed_package_files": full_files,
        "accepted_difference_count": len(mismatches),
        "crlf_normalization_count": len(mismatches),
        "unexplained_mismatch_count": 0,
        "mismatches": mismatches,
        "scientific_interpretation": "The committed package differs from its ZIP manifest only by Git CRLF-to-LF normalization of the preregistered generated CSV. Parsed values and every other package blob are unchanged.",
    }
    write_json(output / "PACKAGE_MANIFEST_REPAIR_REPORT.json", report)
    return report


def run_provenance_repair(repo: Path, config: dict[str, Any], output: Path) -> dict[str, Any]:
    commit = discover_phase2d_commit(repo, config)
    _assert_paths_unchanged(repo, commit, config)
    status = json.loads(git_text(repo, commit, f"{config['phase2d_run_relative']}/RUN_STATUS.json"))["status"]
    decision = json.loads(git_text(repo, commit, f"{config['phase2d_run_relative']}/SCIENTIFIC_DECISION.json"))["label"]
    if status != config["expected_status"] or decision != config["expected_decision"]:
        raise RuntimeError(f"Phase 2D commit has unexpected status/decision: {status}/{decision}")
    result = repair_result_manifest(repo, commit, config, output / "result_manifest")
    package = repair_package_manifest(repo, commit, config, output / "package_manifest")
    summary = {
        "created_utc": utc_now_iso(),
        "status": "PASS",
        "phase2d_commit": commit,
        "phase2d_status": status,
        "phase2d_decision": decision,
        "result_manifest": result,
        "package_manifest": package,
        "new_simulations_run": False,
        "manuscript_or_theory_changed": False,
    }
    write_json(output / "PROVENANCE_REPAIR_SUMMARY.json", summary)
    return summary
