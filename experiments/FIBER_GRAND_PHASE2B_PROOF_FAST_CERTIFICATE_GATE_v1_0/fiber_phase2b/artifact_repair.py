from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from .util import sha256_file, utc_now_iso, write_json


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob(repo: Path, commit: str, rel: str) -> bytes:
    p = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{rel}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"cannot read committed blob {commit}:{rel}: {p.stderr.decode(errors='replace')}")
    return p.stdout


def _parse_manifest(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        out[rel] = digest
    return out


def repair_phase2a_manifest(repo: Path, base_commit: str, run_rel: str, output: Path) -> dict[str, Any]:
    run_dir = repo / run_rel
    original_path = run_dir / "MANIFEST.sha256"
    if not original_path.is_file():
        raise FileNotFoundError(original_path)
    original = _parse_manifest(original_path)
    canonical_lines: list[str] = []
    worktree_lines: list[str] = []
    mismatches: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel, old_hash in sorted(original.items()):
        full_rel = f"{run_rel}/{rel}"
        try:
            blob = _git_blob(repo, base_commit, full_rel)
        except RuntimeError:
            missing.append(rel)
            continue
        committed_hash = _sha(blob)
        canonical_lines.append(f"{committed_hash}  {rel}")
        wt = run_dir / rel
        if wt.is_file():
            worktree_lines.append(f"{sha256_file(wt)}  {rel}")
        reason = "MATCH"
        crlf_hash = None
        if committed_hash != old_hash:
            crlf_hash = _sha(blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            reason = "CRLF_TO_LF_NORMALIZATION" if rel.endswith(".csv") and crlf_hash == old_hash else "UNEXPLAINED_MISMATCH"
            mismatches.append({"path": rel, "original_manifest_sha256": old_hash, "committed_sha256": committed_hash, "reconstructed_crlf_sha256": crlf_hash, "diagnosis": reason})
    output.mkdir(parents=True, exist_ok=True)
    (output / "ORIGINAL_MANIFEST.sha256").write_bytes(original_path.read_bytes())
    (output / "CANONICAL_COMMITTED_MANIFEST.sha256").write_text("\n".join(canonical_lines) + "\n", encoding="utf-8", newline="\n")
    (output / "CURRENT_WORKTREE_MANIFEST.sha256").write_text("\n".join(worktree_lines) + "\n", encoding="utf-8", newline="\n")
    unexplained = [m for m in mismatches if m["diagnosis"] != "CRLF_TO_LF_NORMALIZATION"]
    report = {
        "created_utc": utc_now_iso(),
        "base_commit": base_commit,
        "phase2a_run": run_rel,
        "original_entries": len(original),
        "mismatch_count": len(mismatches),
        "crlf_normalization_count": len(mismatches) - len(unexplained),
        "unexplained_mismatch_count": len(unexplained),
        "missing_committed_files": missing,
        "mismatches": mismatches,
        "status": "PASS" if not unexplained and not missing else "FAIL",
        "scientific_interpretation": "Line-ending normalization changes artifact hashes but not parsed numerical values; no Phase-2A computation is rerun.",
    }
    write_json(output / "MANIFEST_REPAIR_REPORT.json", report)
    (output / "MANIFEST_REPAIR_NOTE.md").write_text(
        "# Phase 2A manifest repair\n\n"
        "The Phase 2A result manifest was written before Git normalized CSV files from CRLF to LF. "
        "This directory preserves the original manifest and supplies a canonical SHA-256 manifest of the exact blobs committed at the frozen Phase 2A commit. "
        "No simulation or numerical result was altered or rerun.\n",
        encoding="utf-8", newline="\n"
    )
    return report
