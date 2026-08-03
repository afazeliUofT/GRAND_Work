from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from .util import sha256_file, utc_now_iso, write_json

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DEFAULT_CONSOLE = "PACKAGE_CONSOLE.log"
_STATUS_FILE = "RUN_STATUS.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob(repo: Path, commit: str, relative: str) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"cannot read committed blob {commit}:{relative}: {detail}")
    return process.stdout


def _git_quiet(repo: Path, arguments: Sequence[str]) -> bool:
    process = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return process.returncode == 0


def _git_list_files(repo: Path, commit: str, prefix: str) -> list[str]:
    process = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit, "--", prefix],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode:
        raise RuntimeError(
            f"cannot enumerate committed files {commit}:{prefix}: {process.stderr.strip()}"
        )
    normalized = prefix.rstrip("/") + "/"
    return [
        line.strip()
        for line in process.stdout.splitlines()
        if line.strip().startswith(normalized)
    ]


def _parse_manifest_bytes(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Phase-2A manifest is not valid UTF-8") from exc

    entries: dict[str, str] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            digest, relative = raw.split("  ", 1)
        except ValueError as exc:
            raise RuntimeError(f"malformed manifest line {line_number}: {raw!r}") from exc
        if not _SHA256_RE.fullmatch(digest):
            raise RuntimeError(f"invalid SHA-256 on manifest line {line_number}: {digest!r}")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise RuntimeError(f"unsafe manifest path on line {line_number}: {relative!r}")
        if relative in entries:
            raise RuntimeError(f"duplicate manifest path: {relative!r}")
        entries[relative] = digest
    if not entries:
        raise RuntimeError("Phase-2A manifest is empty")
    return entries


def _parse_single_sha256_sidecar(data: bytes, expected_filename: str) -> tuple[str, str]:
    try:
        lines = [line for line in data.decode("utf-8").splitlines() if line.strip()]
    except UnicodeDecodeError as exc:
        raise RuntimeError("Phase-2A return-ZIP sidecar is not valid UTF-8") from exc
    if len(lines) != 1:
        raise RuntimeError(
            f"return-ZIP sidecar must contain exactly one nonempty line; got {len(lines)}"
        )
    try:
        digest, filename = lines[0].split("  ", 1)
    except ValueError as exc:
        raise RuntimeError(f"malformed return-ZIP sidecar: {lines[0]!r}") from exc
    if not _SHA256_RE.fullmatch(digest):
        raise RuntimeError(f"invalid return-ZIP SHA-256: {digest!r}")
    if filename != expected_filename:
        raise RuntimeError(
            f"return-ZIP sidecar names {filename!r}; expected {expected_filename!r}"
        )
    return digest, filename


def _strict_line_boundary_prefix_length(data: bytes, expected_digest: str) -> int | None:
    for index, byte in enumerate(data):
        if byte != 0x0A:  # LF
            continue
        end = index + 1
        if end >= len(data):
            continue
        if _sha(data[:end]) == expected_digest:
            return end
    return None


def classify_expected_console_append(
    *,
    committed_blob: bytes,
    original_manifest_sha256: str,
    expected_prefix_terminal_line: str,
    expected_status: str,
    expected_output_path: str,
    expected_zip_path: str,
    expected_zip_sha256: str,
) -> dict[str, Any] | None:
    """Classify only the exact historical four-line console append.

    The old manifest hash must match a strict newline-boundary prefix. That prefix
    must terminate at the frozen structural-scan line, and the remaining bytes must
    be exactly the independently specified four Phase-2A final status lines.
    """

    if not _SHA256_RE.fullmatch(original_manifest_sha256):
        return None
    if not _SHA256_RE.fullmatch(expected_zip_sha256):
        return None
    prefix_length = _strict_line_boundary_prefix_length(
        committed_blob,
        original_manifest_sha256,
    )
    if prefix_length is None:
        return None
    prefix = committed_blob[:prefix_length]
    try:
        prefix_lines = prefix.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return None
    if not prefix_lines or prefix_lines[-1] != expected_prefix_terminal_line:
        return None

    expected_lines = [
        f"[phase2a] status={expected_status}",
        f"[phase2a] output={expected_output_path}",
        f"[phase2a] return_zip={expected_zip_path}",
        f"[phase2a] return_zip_sha256={expected_zip_sha256}",
    ]
    expected_suffix = ("\n".join(expected_lines) + "\n").encode("utf-8")
    actual_suffix = committed_blob[prefix_length:]
    if actual_suffix != expected_suffix:
        return None
    return {
        "diagnosis": "EXPECTED_POST_MANIFEST_CONSOLE_APPEND",
        "manifest_prefix_sha256": original_manifest_sha256,
        "manifest_prefix_bytes": prefix_length,
        "prefix_terminal_line": expected_prefix_terminal_line,
        "committed_log_bytes": len(committed_blob),
        "appended_bytes": len(actual_suffix),
        "appended_line_count": 4,
        "appended_lines": expected_lines,
        "scientific_effect": (
            "four deterministic status lines appended after manifest creation; "
            "no numerical output changed"
        ),
    }


def _diagnose_csv_normalization(
    committed_blob: bytes,
    original_digest: str,
) -> dict[str, Any] | None:
    canonical_lf = committed_blob.replace(b"\r\n", b"\n")
    reconstructed_crlf = canonical_lf.replace(b"\n", b"\r\n")
    reconstructed_digest = _sha(reconstructed_crlf)
    if reconstructed_digest != original_digest:
        return None
    return {
        "diagnosis": "CRLF_TO_LF_NORMALIZATION",
        "reconstructed_crlf_sha256": reconstructed_digest,
        "scientific_effect": "text line endings only; parsed CSV fields are unchanged",
    }


def _phase2a_return_zip_name(run_relative: str) -> str:
    run_name = PurePosixPath(run_relative).name
    if not run_name.startswith("run_"):
        raise RuntimeError(f"unexpected frozen Phase-2A run directory: {run_name!r}")
    return f"FIBER_GRAND_PHASE2A_RETURN_{run_name}.zip"


def _diagnose_expected_console_append(
    *,
    repo: Path,
    base_commit: str,
    run_relative: str,
    committed_blob: bytes,
    original_digest: str,
    expected_prefix_terminal_line: str,
) -> dict[str, Any] | None:
    status_blob = _git_blob(repo, base_commit, f"{run_relative}/{_STATUS_FILE}")
    try:
        status_payload = json.loads(status_blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("frozen Phase-2A RUN_STATUS.json is unreadable") from exc
    run_status = str(status_payload.get("status", ""))
    if run_status not in {"PASS", "FAIL"}:
        raise RuntimeError(f"unexpected frozen Phase-2A status: {run_status!r}")

    return_zip_name = _phase2a_return_zip_name(run_relative)
    sidecar_name = return_zip_name + ".sha256"
    sidecar_blob = _git_blob(repo, base_commit, f"{run_relative}/{sidecar_name}")
    return_digest, sidecar_filename = _parse_single_sha256_sidecar(
        sidecar_blob,
        return_zip_name,
    )

    run_dir = (repo / PurePosixPath(run_relative)).resolve()
    local_return_zip = run_dir / return_zip_name
    local_zip_status = "ABSENT_NOT_REQUIRED"
    local_zip_digest: str | None = None
    if local_return_zip.is_file():
        local_zip_digest = sha256_file(local_return_zip)
        if local_zip_digest != return_digest:
            return {
                "diagnosis": "LOCAL_RETURN_ZIP_HASH_MISMATCH",
                "expected_return_zip_sha256": return_digest,
                "local_return_zip_sha256": local_zip_digest,
                "local_return_zip": str(local_return_zip),
            }
        local_zip_status = "MATCHES_COMMITTED_SIDECAR"

    classified = classify_expected_console_append(
        committed_blob=committed_blob,
        original_manifest_sha256=original_digest,
        expected_prefix_terminal_line=expected_prefix_terminal_line,
        expected_status=run_status,
        expected_output_path=str(run_dir),
        expected_zip_path=str(run_dir / sidecar_filename),
        expected_zip_sha256=return_digest,
    )
    if classified is None:
        return None
    classified.update(
        {
            "run_status_json": run_status,
            "return_zip_sidecar": sidecar_name,
            "return_zip_sidecar_sha256": return_digest,
            "local_return_zip_status": local_zip_status,
            "local_return_zip_sha256": local_zip_digest,
        }
    )
    return classified


def _worktree_equivalent(
    *,
    relative: str,
    worktree_blob: bytes,
    committed_blob: bytes,
    original_digest: str,
    expected_csv: set[str],
) -> bool:
    if worktree_blob == committed_blob:
        return True
    if relative in expected_csv and _sha(worktree_blob) == original_digest:
        # The WSL worktree can retain the original CRLF bytes while Git stores LF.
        return True
    return False


def repair_phase2a_manifest(
    repo: Path,
    base_commit: str,
    run_relative: str,
    output: Path,
    policy: dict[str, Any] | None = None,
    *,
    expected_crlf_paths: Sequence[str] | None = None,
    expected_console_path: str = _DEFAULT_CONSOLE,
    expected_console_prefix_terminal_line: str | None = None,
    require_clean_worktree_copy: bool = True,
) -> dict[str, Any]:
    """Create a canonical manifest for the frozen Phase-2A evidence.

    ``policy`` is accepted as a convenience for the frozen JSON configuration.
    Keyword arguments override it. The accepted difference set is closed: exact
    matches, the preregistered CSV CRLF-to-LF normalizations, and one semantically
    verified four-line console append. Everything else is fatal.
    """

    policy = dict(policy or {})
    if expected_crlf_paths is None:
        expected_crlf_paths = policy.get("expected_crlf_paths", [])
    if expected_console_path == _DEFAULT_CONSOLE:
        expected_console_path = str(
            policy.get("expected_post_manifest_append_path", expected_console_path)
        )
    if expected_console_prefix_terminal_line is None:
        expected_console_prefix_terminal_line = policy.get(
            "expected_console_prefix_terminal_line"
        )
    if "require_clean_worktree_copy" in policy:
        require_clean_worktree_copy = bool(policy["require_clean_worktree_copy"])
    frozen_replay_export_paths = [
        str(path) for path in policy.get("frozen_replay_export_paths", [])
    ]
    if not frozen_replay_export_paths:
        raise RuntimeError("frozen replay export paths are required")
    if expected_console_prefix_terminal_line is None:
        raise RuntimeError("expected console-prefix terminal line is required")

    repo = repo.resolve()
    expected_csv = set(str(path) for path in expected_crlf_paths)
    manifest_relative = f"{run_relative}/MANIFEST.sha256"
    original_bytes = _git_blob(repo, base_commit, manifest_relative)
    original = _parse_manifest_bytes(original_bytes)
    run_dir = repo / PurePosixPath(run_relative)

    base_to_head_clean = _git_quiet(
        repo,
        ["diff", "--quiet", base_commit, "HEAD", "--", run_relative],
    )
    index_clean = _git_quiet(
        repo,
        ["diff", "--cached", "--quiet", "--", run_relative],
    )

    canonical_lines: list[str] = []
    worktree_lines: list[str] = []
    mismatches: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    unexplained: list[dict[str, Any]] = []
    missing_committed: list[str] = []
    missing_worktree: list[str] = []
    worktree_mismatches: list[dict[str, Any]] = []

    for relative, original_digest in sorted(original.items()):
        full_relative = f"{run_relative}/{relative}"
        try:
            committed_blob = _git_blob(repo, base_commit, full_relative)
        except RuntimeError:
            missing_committed.append(relative)
            continue

        committed_digest = _sha(committed_blob)
        canonical_lines.append(f"{committed_digest}  {relative}")
        worktree_path = run_dir / PurePosixPath(relative)
        if worktree_path.is_file():
            worktree_blob = worktree_path.read_bytes()
            worktree_digest = _sha(worktree_blob)
            worktree_lines.append(f"{worktree_digest}  {relative}")
            if not _worktree_equivalent(
                relative=relative,
                worktree_blob=worktree_blob,
                committed_blob=committed_blob,
                original_digest=original_digest,
                expected_csv=expected_csv,
            ):
                worktree_mismatches.append(
                    {
                        "path": relative,
                        "worktree_sha256": worktree_digest,
                        "committed_sha256": committed_digest,
                        "original_manifest_sha256": original_digest,
                    }
                )
        else:
            missing_worktree.append(relative)

        if committed_digest == original_digest:
            continue

        record: dict[str, Any] = {
            "path": relative,
            "original_manifest_sha256": original_digest,
            "committed_sha256": committed_digest,
        }
        diagnosis: dict[str, Any] | None = None
        if relative in expected_csv:
            diagnosis = _diagnose_csv_normalization(committed_blob, original_digest)
        elif relative == expected_console_path:
            diagnosis = _diagnose_expected_console_append(
                repo=repo,
                base_commit=base_commit,
                run_relative=run_relative,
                committed_blob=committed_blob,
                original_digest=original_digest,
                expected_prefix_terminal_line=expected_console_prefix_terminal_line,
            )

        if diagnosis is None:
            record["diagnosis"] = "UNEXPLAINED_MISMATCH"
            mismatches.append(record)
            unexplained.append(record)
            continue

        record.update(diagnosis)
        mismatches.append(record)
        if record["diagnosis"] in {
            "CRLF_TO_LF_NORMALIZATION",
            "EXPECTED_POST_MANIFEST_CONSOLE_APPEND",
        }:
            accepted.append(record)
        else:
            unexplained.append(record)

    observed_csv = {
        item["path"]
        for item in accepted
        if item.get("diagnosis") == "CRLF_TO_LF_NORMALIZATION"
    }
    console_append_count = sum(
        item.get("diagnosis") == "EXPECTED_POST_MANIFEST_CONSOLE_APPEND"
        for item in accepted
    )

    policy_failures: list[dict[str, Any]] = []
    if observed_csv != expected_csv:
        policy_failures.append(
            {
                "diagnosis": "EXPECTED_CRLF_PATH_SET_MISMATCH",
                "expected": sorted(expected_csv),
                "observed": sorted(observed_csv),
            }
        )
    if console_append_count != 1:
        policy_failures.append(
            {
                "diagnosis": "EXPECTED_CONSOLE_APPEND_COUNT_MISMATCH",
                "expected": 1,
                "observed": console_append_count,
            }
        )
    if require_clean_worktree_copy and not base_to_head_clean:
        policy_failures.append(
            {
                "diagnosis": "PHASE2A_PATH_CHANGED_AFTER_FROZEN_COMMIT",
                "base_commit": base_commit,
            }
        )
    if require_clean_worktree_copy and not index_clean:
        policy_failures.append({"diagnosis": "PHASE2A_INDEX_HAS_STAGED_CHANGES"})
    if require_clean_worktree_copy and missing_worktree:
        policy_failures.append(
            {
                "diagnosis": "PHASE2A_WORKTREE_FILES_MISSING",
                "paths": sorted(missing_worktree),
            }
        )
    if require_clean_worktree_copy and worktree_mismatches:
        policy_failures.append(
            {
                "diagnosis": "PHASE2A_WORKTREE_CONTENT_MISMATCH",
                "count": len(worktree_mismatches),
            }
        )
    unexplained.extend(policy_failures)

    full_committed_paths = _git_list_files(repo, base_commit, run_relative)
    full_committed_manifest_lines: list[str] = []
    for full_relative in full_committed_paths:
        relative = PurePosixPath(full_relative).relative_to(PurePosixPath(run_relative)).as_posix()
        full_committed_manifest_lines.append(
            f"{_sha(_git_blob(repo, base_commit, full_relative))}  {relative}"
        )

    frozen_export_failures: list[dict[str, Any]] = []
    frozen_export_manifest_lines: list[str] = []
    frozen_root = output / "FROZEN_REPLAY_INPUTS"
    for relative in frozen_replay_export_paths:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            frozen_export_failures.append(
                {"diagnosis": "UNSAFE_FROZEN_REPLAY_EXPORT_PATH", "path": relative}
            )
            continue
        if relative not in original:
            frozen_export_failures.append(
                {"diagnosis": "FROZEN_REPLAY_EXPORT_NOT_IN_ORIGINAL_MANIFEST", "path": relative}
            )
            continue
        try:
            blob = _git_blob(repo, base_commit, f"{run_relative}/{relative}")
        except RuntimeError as exc:
            frozen_export_failures.append(
                {"diagnosis": "FROZEN_REPLAY_EXPORT_MISSING", "path": relative, "error": str(exc)}
            )
            continue
        target = frozen_root / pure
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        frozen_export_manifest_lines.append(f"{_sha(blob)}  {relative}")
    if frozen_replay_export_paths and len(frozen_export_manifest_lines) != len(frozen_replay_export_paths):
        policy_failures.extend(frozen_export_failures)
        unexplained.extend(frozen_export_failures)

    output.mkdir(parents=True, exist_ok=True)
    if frozen_export_manifest_lines:
        (output / "FROZEN_REPLAY_INPUTS_MANIFEST.sha256").write_text(
            "\n".join(frozen_export_manifest_lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    (output / "ORIGINAL_MANIFEST.sha256").write_bytes(original_bytes)
    (output / "CANONICAL_COMMITTED_MANIFEST.sha256").write_text(
        "\n".join(canonical_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / "CURRENT_WORKTREE_MANIFEST.sha256").write_text(
        "\n".join(worktree_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / "CANONICAL_FULL_COMMITTED_RUN_MANIFEST.sha256").write_text(
        "\n".join(full_committed_manifest_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    status = "PASS" if not unexplained and not missing_committed else "FAIL"
    report = {
        "created_utc": utc_now_iso(),
        "repair_version": "Phase2B-R1-v1.1",
        "base_commit": base_commit,
        "phase2a_run": run_relative,
        "original_entries": len(original),
        "full_committed_run_files": len(full_committed_paths),
        "frozen_replay_export_root": "FROZEN_REPLAY_INPUTS",
        "mismatch_count": len(mismatches),
        "accepted_difference_count": len(accepted),
        "crlf_normalization_count": len(observed_csv),
        "expected_crlf_paths": sorted(expected_csv),
        "observed_crlf_paths": sorted(observed_csv),
        "expected_post_manifest_console_append_count": console_append_count,
        "worktree_mismatch_count": len(worktree_mismatches),
        "worktree_mismatches": worktree_mismatches,
        "unexplained_mismatch_count": len(unexplained),
        "missing_committed_files": sorted(missing_committed),
        "missing_worktree_files": sorted(missing_worktree),
        "base_to_head_phase2a_path_unchanged": base_to_head_clean,
        "tracked_index_clean": index_clean,
        "frozen_replay_export_paths": frozen_replay_export_paths,
        "frozen_replay_export_failures": frozen_export_failures,
        "frozen_replay_inputs_manifest": (
            "FROZEN_REPLAY_INPUTS_MANIFEST.sha256"
            if frozen_export_manifest_lines
            else None
        ),
        "mismatches": mismatches,
        "policy_failures": policy_failures,
        "unexplained_mismatches": unexplained,
        "status": status,
        "scientific_interpretation": (
            "The canonical manifest hashes the exact blobs at the frozen Phase-2A commit. "
            "Accepted differences are restricted to the preregistered CSV CRLF-to-LF "
            "normalizations and the verified four-line PACKAGE_CONSOLE.log append. "
            "Replay inputs are exported directly from the frozen commit. No Phase-2A "
            "simulation, decoder output, or numerical result is altered or rerun."
        ),
    }
    write_json(output / "MANIFEST_REPAIR_REPORT.json", report)

    note = [
        "# Phase 2A manifest repair — Phase 2B-R1",
        "",
        "This is a closed-world integrity reconciliation of the frozen Phase-2A commit.",
        "No Phase-2A computation is rerun or modified.",
        "",
        f"- Preregistered CSV normalizations established: `{len(observed_csv)}`.",
        f"- Verified post-manifest console append: `{console_append_count}`.",
        f"- Worktree content mismatches: `{len(worktree_mismatches)}`.",
        f"- Canonical replay inputs exported from the frozen commit: `{len(frozen_export_manifest_lines)}`.",
        f"- Unexplained or policy-blocking differences: `{len(unexplained)}`.",
        "",
        "The console append is accepted only when:",
        "",
        "1. the old manifest hash equals a strict newline-boundary prefix of the committed log;",
        "2. that prefix ends at the frozen structural-scan line;",
        "3. the suffix is exactly the four final Phase-2A status lines;",
        "4. the printed status equals `RUN_STATUS.json`;",
        "5. the printed return-ZIP digest equals the committed sidecar; and",
        "6. a local return ZIP, when present, has the same digest.",
        "",
        f"Repair status: **{status}**.",
        "",
        "Any other byte difference remains fatal.",
    ]
    (output / "MANIFEST_REPAIR_NOTE.md").write_text(
        "\n".join(note) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report
