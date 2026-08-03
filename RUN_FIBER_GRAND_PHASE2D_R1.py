#!/usr/bin/env python3
"""One-command WSL launcher for FIBER-GRAND Paper-I Phase 2D-R1.

Run from the connected VS Code WSL terminal:
    cd /home/afazeli2006/GRAND_Work
    python3 RUN_FIBER_GRAND_PHASE2D_R1.py

This wrapper repairs only Phase-2D artifact provenance, creates the external-review
handoff bundle, commits the repair, and pushes the existing local Phase-2D commit plus
the new repair commit. It does not rerun Phase 2C, Phase 2D, proofs, or simulations.
It never calls shell ``exit`` and never replaces the parent shell, so the VS Code
terminal remains open after success, failure, or interruption.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

PACKAGE_ZIP_BASENAME = "FIBER_GRAND_PHASE2D_R1_PROVENANCE_REPAIR_EXTERNAL_REVIEW_HANDOFF_v1_1_2026-08-03.zip"
PACKAGE_ZIP_STEM = "FIBER_GRAND_PHASE2D_R1_PROVENANCE_REPAIR_EXTERNAL_REVIEW_HANDOFF_v1_1_2026-08-03"
PACKAGE_ZIP_SHA256 = "e8585380c6ed4875178f4ceb165227db157c96827eea503a7ffd9fd036f13802"
PACKAGE_ROOT_NAME = "FIBER_GRAND_PHASE2D_R1_PROVENANCE_REPAIR_EXTERNAL_REVIEW_HANDOFF_v1_1"
DEFAULT_REPO_ROOT = Path("/home/afazeli2006/GRAND_Work")
PACKAGE_RELATIVE_PATH = Path("experiments") / PACKAGE_ROOT_NAME
RESULTS_NAMESPACE = Path("results") / "FIBER_GRAND_Phase2D_R1"
EXPECTED_GITHUB_REPOSITORY = "afazeliuoft/grand_work"
REQUIRED_PHASE2C_COMMIT = "2f7736b70bf7f6f659a6707fad716407635a7deb"
MINIMUM_PYTHON = (3, 10)
MAX_UNCOMPRESSED_PACKAGE_BYTES = 100 * 1024 * 1024


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


class Logger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", buffering=1)

    def write(self, message: str = "") -> None:
        line = message.rstrip("\n")
        print(line, flush=True)
        self._handle.write(line + "\n")

    def flush(self) -> None:
        self._handle.flush()

    def close(self) -> None:
        try:
            self._handle.flush()
            self._handle.close()
        except Exception:
            pass


def capture(command: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(x) for x in command],
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_streaming(
    command: Sequence[str],
    *,
    logger: Logger,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    command_log: Path | None = None,
) -> int:
    logger.write(f"$ {shlex.join(str(x) for x in command)}")
    command_handle = None
    try:
        if command_log is not None:
            command_log.parent.mkdir(parents=True, exist_ok=True)
            command_handle = command_log.open("w", encoding="utf-8", buffering=1)
        process = subprocess.Popen(
            [str(x) for x in command],
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            text = line.rstrip("\n")
            logger.write(text)
            if command_handle is not None:
                command_handle.write(text + "\n")
        return_code = process.wait()
        logger.write(f"[command return code] {return_code}")
        return return_code
    except OSError as exc:
        logger.write(f"[command launch failure] {exc!r}")
        if command_handle is not None:
            command_handle.write(f"COMMAND_LAUNCH_FAILURE={exc!r}\n")
        return 127
    finally:
        if command_handle is not None:
            command_handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FIBER-GRAND Phase-2D-R1 provenance repair and review handoff.")
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--zip", dest="zip_path", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--no-push", action="store_true", help="Run locally without Git commit or push.")
    return parser.parse_args()


def normalize_github_remote(url: str) -> str | None:
    value = url.strip()
    path: str | None = None
    if value.startswith("git@github.com:"):
        path = value.split(":", 1)[1]
    elif value.startswith("ssh://git@github.com/"):
        path = value.split("github.com/", 1)[1]
    elif "github.com/" in value:
        path = value.split("github.com/", 1)[1]
    if path is None:
        return None
    path = path.split("?", 1)[0].split("#", 1)[0].strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path.lower()


def is_ancestor(repo_root: Path, older: str, newer: str) -> bool:
    return capture(["git", "-C", str(repo_root), "merge-base", "--is-ancestor", older, newer]).returncode == 0


def validate_repository(repo_root: Path, logger: Logger, *, require_network: bool) -> tuple[Path, str, str, Path, str, str | None]:
    repo_root = repo_root.expanduser().resolve()
    probe = capture(["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"])
    if probe.returncode != 0:
        raise RuntimeError(f"Not a Git working tree: {repo_root}\n{probe.stderr.strip()}")
    actual = Path(probe.stdout.strip()).resolve()
    if actual != repo_root:
        raise RuntimeError(f"Expected repository root {repo_root}, but Git reports {actual}")

    remote_probe = capture(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
    if remote_probe.returncode != 0:
        raise RuntimeError(f"Cannot read Git origin: {remote_probe.stderr.strip()}")
    remote_url = remote_probe.stdout.strip()
    if normalize_github_remote(remote_url) != EXPECTED_GITHUB_REPOSITORY:
        raise RuntimeError(f"Unexpected origin {remote_url!r}; expected {EXPECTED_GITHUB_REPOSITORY!r}")

    branch_probe = capture(["git", "-C", str(repo_root), "symbolic-ref", "--quiet", "--short", "HEAD"])
    if branch_probe.returncode != 0 or not branch_probe.stdout.strip():
        raise RuntimeError("Repository is in detached-HEAD state")
    branch = branch_probe.stdout.strip()
    if branch != "main":
        raise RuntimeError(f"Phase 2D-R1 must run on main; current branch is {branch!r}")

    head_probe = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    if head_probe.returncode != 0:
        raise RuntimeError("Cannot resolve local HEAD")
    local_head = head_probe.stdout.strip()
    if not is_ancestor(repo_root, REQUIRED_PHASE2C_COMMIT, local_head):
        raise RuntimeError("The frozen Phase 2C GO commit is not an ancestor of local HEAD")

    # The failed Phase 2D wrapper already created a local commit. No tracked edit may be pending.
    if capture(["git", "-C", str(repo_root), "diff", "--quiet"]).returncode != 0:
        raise RuntimeError("Tracked working-tree changes exist; preserve or commit them before Phase 2D-R1")
    if capture(["git", "-C", str(repo_root), "diff", "--cached", "--quiet"]).returncode != 0:
        raise RuntimeError("Staged changes exist; unstage or commit them before Phase 2D-R1")

    git_dir_probe = capture(["git", "-C", str(repo_root), "rev-parse", "--git-dir"])
    if git_dir_probe.returncode != 0:
        raise RuntimeError("Cannot resolve .git directory")
    git_dir = Path(git_dir_probe.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (repo_root / git_dir).resolve()

    remote_head: str | None = None
    if require_network:
        fetch_rc = run_streaming(["git", "-C", str(repo_root), "fetch", "origin", "main"], logger=logger)
        if fetch_rc != 0:
            raise RuntimeError("Unable to fetch origin/main; no local history was changed")
        remote_probe = capture(["git", "-C", str(repo_root), "rev-parse", "refs/remotes/origin/main"])
        if remote_probe.returncode != 0:
            raise RuntimeError("Cannot resolve fetched origin/main")
        remote_head = remote_probe.stdout.strip()
        if not is_ancestor(repo_root, remote_head, local_head):
            if is_ancestor(repo_root, local_head, remote_head):
                raise RuntimeError("origin/main is ahead of local main; run `git pull --ff-only` and rerun Phase 2D-R1")
            raise RuntimeError("local main and origin/main have diverged; manual Git review is required")

    logger.write(f"[repo] root={repo_root}")
    logger.write(f"[repo] origin={remote_url}")
    logger.write(f"[repo] branch={branch}")
    logger.write(f"[repo] local_head={local_head}")
    if remote_head:
        logger.write(f"[repo] origin/main={remote_head}; local push is fast-forward safe")
    logger.write(f"[repo] Phase 2C GO commit verified as ancestor: {REQUIRED_PHASE2C_COMMIT}")
    return repo_root, remote_url, branch, git_dir, local_head, remote_head


def ensure_gitattributes(repo_root: Path, logger: Logger) -> None:
    path = repo_root / ".gitattributes"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    required = [
        "*.csv text eol=lf", "*.tsv text eol=lf", "*.json text eol=lf", "*.md text eol=lf",
        "*.tex text eol=lf", "*.py text eol=lf", "*.log text eol=lf", "*.txt text eol=lf",
        "*.sha256 text eol=lf",
    ]
    lines = existing.splitlines()
    changed = False
    for rule in required:
        if rule not in lines:
            lines.append(rule)
            changed = True
    if changed:
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    logger.write(f"[git] repository line-ending policy verified at {path}")


def add_local_git_excludes(git_dir: Path, logger: Logger) -> None:
    path = git_dir / "info" / "exclude"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    patterns = [
        ".venv/", ".venv*/", "**/.venv/", "**/.venv*/", "**/__pycache__/", "*.py[cod]",
        ".pytest_cache/", "results/FIBER_GRAND_Phase2D_R1/**/FIBER_GRAND_PHASE2D_R1_RETURN_*.zip",
    ]
    lines = existing.splitlines()
    changed = False
    for pattern in patterns:
        if pattern not in lines:
            lines.append(pattern)
            changed = True
    if changed:
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    logger.write(f"[git] local excludes verified at {path}")


def download_directories() -> list[Path]:
    candidates = [Path.home() / "Downloads"]
    for drive in ("c", "d"):
        users = Path(f"/mnt/{drive}/Users")
        if users.is_dir():
            candidates.extend(path / "Downloads" for path in users.iterdir() if path.is_dir())
    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def locate_package_zip(explicit: Path | None, logger: Logger) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates = [explicit.expanduser().resolve()]
    else:
        for directory in download_directories():
            if not directory.is_dir():
                continue
            candidates.extend(directory.glob(PACKAGE_ZIP_BASENAME))
            candidates.extend(directory.glob(PACKAGE_ZIP_STEM + "*.zip"))
    unique: dict[str, Path] = {}
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            unique[str(resolved)] = resolved
    mismatches: list[str] = []
    for candidate in sorted(unique.values(), key=lambda p: p.stat().st_mtime_ns, reverse=True):
        digest = sha256_file(candidate)
        if digest == PACKAGE_ZIP_SHA256:
            logger.write(f"[package] located={candidate}")
            logger.write(f"[package] sha256={digest} (verified)")
            return candidate
        mismatches.append(f"{candidate}: {digest}")
    details = "\n".join(mismatches) if mismatches else "No candidate file was found."
    raise FileNotFoundError(
        f"Could not find a package ZIP with the required SHA-256. Expected {PACKAGE_ZIP_BASENAME!r}.\n{details}"
    )


def validate_zip_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename.replace("\\", "/")
    pure = PurePosixPath(name)
    if not name or name.startswith("/") or pure.is_absolute() or ".." in pure.parts:
        raise RuntimeError(f"Unsafe ZIP member path: {info.filename!r}")
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise RuntimeError(f"Symbolic links are forbidden: {info.filename!r}")
    if mode and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise RuntimeError(f"Non-regular ZIP member is forbidden: {info.filename!r}")
    return pure


def verify_package_manifest(package_root: Path) -> None:
    manifest = package_root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        raise RuntimeError("Package has no PACKAGE_MANIFEST.sha256")
    expected: dict[str, str] = {}
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, relative = raw.split("  ", 1)
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeError(f"Unsafe package-manifest path: {relative!r}")
        expected[relative] = digest
    actual = {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and path != manifest
    }
    if actual != set(expected):
        raise RuntimeError(
            f"Package manifest file-set mismatch; missing={sorted(set(expected)-actual)}, extra={sorted(actual-set(expected))}"
        )
    for relative, digest in expected.items():
        got = sha256_file(package_root / relative)
        if got != digest:
            raise RuntimeError(f"Package hash mismatch for {relative}: expected {digest}, got {got}")


def install_package(package_zip: Path, repo_root: Path, logger: Logger) -> Path:
    temporary = Path(tempfile.mkdtemp(prefix="fiber_grand_phase2d_r1_extract_"))
    try:
        with zipfile.ZipFile(package_zip) as archive:
            infos = archive.infolist()
            total = sum(info.file_size for info in infos)
            if total > MAX_UNCOMPRESSED_PACKAGE_BYTES:
                raise RuntimeError("Package exceeds the uncompressed-size safety limit")
            roots: set[str] = set()
            for info in infos:
                pure = validate_zip_member(info)
                roots.add(pure.parts[0])
            if roots != {PACKAGE_ROOT_NAME}:
                raise RuntimeError(f"Unexpected package root(s): {sorted(roots)}")
            archive.extractall(temporary)
        extracted = temporary / PACKAGE_ROOT_NAME
        verify_package_manifest(extracted)
        target = repo_root / PACKAGE_RELATIVE_PATH
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(extracted), str(target))
        verify_package_manifest(target)
        logger.write(f"[package] installed={target}")
        return target
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def prepare_venv(logger: Logger) -> Path:
    venv = Path.home() / ".venvs" / "fiber_grand_phase2d_r1_v1_1"
    python = venv / "bin" / "python"
    if not python.is_file():
        rc = run_streaming([sys.executable, "-m", "venv", str(venv)], logger=logger)
        if rc != 0:
            raise RuntimeError("Unable to create the isolated Python environment")
    probe = capture([str(python), "-c", "import sys; print('.'.join(map(str,sys.version_info[:3])))"])
    if probe.returncode != 0:
        raise RuntimeError(f"Unable to execute venv Python: {probe.stderr.strip()}")
    version = tuple(int(piece) for piece in probe.stdout.strip().split("."))
    if version < MINIMUM_PYTHON:
        raise RuntimeError(f"Python {version} is too old; require {MINIMUM_PYTHON}")
    logger.write(f"[venv] interpreter={python}")
    logger.write(f"[venv] version={version}; no third-party Python dependencies are required")
    logger.write("[venv] parent-shell activation is unnecessary")
    return python


def next_run_directory(repo_root: Path, stamp: str) -> tuple[Path, Path]:
    namespace = repo_root / RESULTS_NAMESPACE
    namespace.mkdir(parents=True, exist_ok=True)
    base = namespace / f"run_{stamp}"
    candidate = base
    counter = 1
    while candidate.exists():
        counter += 1
        candidate = namespace / f"run_{stamp}_{counter}"
    candidate.mkdir(parents=True)
    return candidate, candidate.relative_to(repo_root)


def path_has_venv(path: str) -> bool:
    return any(part == ".venv" or part.startswith(".venv") for part in PurePosixPath(path).parts)


def parse_sha256_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, relative = raw.split("  ", 1)
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeError(f"Unsafe result-manifest path: {relative!r}")
        entries[relative] = digest
    return entries


def git_blob_bytes(repo_root: Path, object_spec: str) -> bytes:
    probe = subprocess.run(
        ["git", "-C", str(repo_root), "show", object_spec],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            f"Cannot read Git blob {object_spec!r}: {probe.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return probe.stdout


def write_commit_ready_manifest(run_dir: Path) -> Path:
    manifest = run_dir / "COMMIT_READY_MANIFEST.sha256"
    scope = run_dir / "MANIFEST_SCOPE.md"
    scope.write_text(
        "# Phase 2D-R1 commit-manifest scope\n\n"
        "`SCIENTIFIC_OUTPUT_MANIFEST.sha256` covers the package-generated repair and review artifacts. "
        "`COMMIT_READY_MANIFEST.sha256` is generated by the WSL wrapper after all wrapper metadata, "
        "the Windows-copy record, and GitHub review pointer exist. It covers every committed file in "
        "this result directory except itself and the uncommitted local Phase-2D-R1 return ZIP.\n",
        encoding="utf-8",
        newline="\n",
    )
    lines: list[str] = []
    for path in sorted(candidate for candidate in run_dir.rglob("*") if candidate.is_file()):
        if path == manifest:
            continue
        if path.name.startswith("FIBER_GRAND_PHASE2D_R1_RETURN_") and path.suffix == ".zip":
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return manifest


def verify_result_manifest_in_git(
    *,
    repo_root: Path,
    run_relative: Path,
    manifest: Path,
    treeish: str | None,
) -> None:
    entries = parse_sha256_manifest(manifest)
    mismatches: list[str] = []
    for relative, expected in entries.items():
        repository_path = (run_relative / PurePosixPath(relative)).as_posix()
        object_spec = f":{repository_path}" if treeish is None else f"{treeish}:{repository_path}"
        actual = hashlib.sha256(git_blob_bytes(repo_root, object_spec)).hexdigest()
        if actual != expected:
            mismatches.append(f"{relative}: expected {expected}, Git blob has {actual}")
    if mismatches:
        stage = "staged index" if treeish is None else f"commit {treeish}"
        raise RuntimeError(f"Result manifest does not match the {stage}:\n" + "\n".join(mismatches[:50]))


def copy_review_bundle_to_windows(run_dir: Path, logger: Logger) -> tuple[str | None, str | None]:
    source = run_dir / "external_review" / "FIBER_GRAND_Paper_I_External_Review_Bundle_Phase2D_R1.zip"
    if not source.is_file():
        atomic_json(run_dir / "WINDOWS_DOWNLOAD_COPY.json", {"status": "SOURCE_NOT_FOUND"})
        return None, None
    destination_directory = None
    preferred = Path("/mnt/c/Users/alifa/Downloads")
    if preferred.is_dir():
        destination_directory = preferred
    else:
        for candidate in download_directories():
            if candidate.is_dir() and str(candidate).startswith("/mnt/"):
                destination_directory = candidate
                break
    if destination_directory is None:
        atomic_json(
            run_dir / "WINDOWS_DOWNLOAD_COPY.json",
            {"status": "NO_WINDOWS_DOWNLOADS_FOUND", "source": str(source), "sha256": sha256_file(source)},
        )
        logger.write(f"[review] Windows Downloads not found; bundle remains at {source}")
        return None, sha256_file(source)
    destination = destination_directory / source.name
    shutil.copy2(source, destination)
    digest = sha256_file(destination)
    if digest != sha256_file(source):
        raise RuntimeError("Windows copy of the external-review bundle failed SHA-256 verification")
    sidecar = destination.with_suffix(destination.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {destination.name}\n", encoding="utf-8", newline="\n")
    atomic_json(
        run_dir / "WINDOWS_DOWNLOAD_COPY.json",
        {"status": "PASS", "source": str(source), "destination": str(destination), "sha256": digest},
    )
    logger.write(f"[review] external-review bundle copied to {destination}")
    logger.write(f"[review] external-review bundle sha256={digest}")
    return str(destination), digest


def git_commit_and_push(
    *,
    repo_root: Path,
    package_target: Path,
    run_dir: Path,
    branch: str,
    status: str,
    decision: str,
    phase2d_commit: str,
    logger: Logger,
    wrapper_path: Path,
) -> tuple[str | None, bool]:
    latest = repo_root / RESULTS_NAMESPACE / "LATEST.json"
    run_relative = run_dir.relative_to(repo_root)
    atomic_json(
        latest,
        {
            "created_utc": utc_iso(),
            "package_zip_sha256": PACKAGE_ZIP_SHA256,
            "result_directory": run_relative.as_posix(),
            "scientific_run_status": status,
            "scientific_decision": decision,
            "repaired_phase2d_commit": phase2d_commit,
        },
    )
    atomic_json(
        run_dir / "GITHUB_REVIEW_POINTER.json",
        {
            "branch": branch,
            "origin_repository": EXPECTED_GITHUB_REPOSITORY,
            "result_directory": run_relative.as_posix(),
            "package_directory": package_target.relative_to(repo_root).as_posix(),
            "scientific_run_status": status,
            "scientific_decision": decision,
            "repaired_phase2d_commit": phase2d_commit,
        },
    )
    commit_ready_manifest = write_commit_ready_manifest(run_dir)

    pathspecs = [
        package_target.relative_to(repo_root).as_posix(),
        run_relative.as_posix(),
        latest.relative_to(repo_root).as_posix(),
        ".gitattributes",
    ]
    try:
        pathspecs.append(wrapper_path.resolve().relative_to(repo_root).as_posix())
    except ValueError:
        logger.write("[git] wrapper is outside the repository and will not be committed")

    add = capture(["git", "-C", str(repo_root), "add", "--", *pathspecs])
    if add.returncode != 0:
        raise RuntimeError(f"git add failed: {add.stderr.strip()}")
    staged = capture(["git", "-C", str(repo_root), "diff", "--cached", "--name-only", "--", *pathspecs])
    if staged.returncode != 0:
        raise RuntimeError(f"Cannot inspect staged files: {staged.stderr.strip()}")
    staged_paths = [line.strip() for line in staged.stdout.splitlines() if line.strip()]
    forbidden = [
        path for path in staged_paths
        if path_has_venv(path)
        or (Path(path).name.startswith("FIBER_GRAND_PHASE2D_R1_RETURN_") and path.endswith(".zip"))
    ]
    if forbidden:
        raise RuntimeError(f"Safety stop: forbidden paths staged: {forbidden}")
    verify_result_manifest_in_git(
        repo_root=repo_root,
        run_relative=run_relative,
        manifest=commit_ready_manifest,
        treeish=None,
    )
    logger.write("[git] commit-ready result manifest matches every staged result blob")
    if not staged_paths:
        head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        return (head.stdout.strip() if head.returncode == 0 else None), False

    logger.write(f"[git] staged {len(staged_paths)} intended files; no .venv or return ZIP is staged")
    message = f"FIBER-GRAND Phase 2D-R1 provenance repair/review handoff {status} {run_dir.name}"
    rc = run_streaming(
        ["git", "-C", str(repo_root), "commit", "--only", "-m", message, "--", *pathspecs],
        logger=logger,
    )
    if rc != 0:
        raise RuntimeError("Git commit failed; files remain available for review")
    head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    if head.returncode != 0:
        raise RuntimeError("Cannot read newly created commit")
    commit = head.stdout.strip()
    verify_result_manifest_in_git(
        repo_root=repo_root,
        run_relative=run_relative,
        manifest=commit_ready_manifest,
        treeish=commit,
    )
    if not is_ancestor(repo_root, phase2d_commit, commit):
        raise RuntimeError("New Phase 2D-R1 commit does not preserve the original Phase 2D commit as an ancestor")
    logger.write("[git] committed result blobs reverified against COMMIT_READY_MANIFEST.sha256")

    push_rc = run_streaming(
        ["git", "-C", str(repo_root), "push", "-u", "origin", f"{branch}:{branch}"],
        logger=logger,
    )
    pushed = push_rc == 0
    if pushed:
        verify_fetch = capture(["git", "-C", str(repo_root), "fetch", "origin", "main"])
        remote = capture(["git", "-C", str(repo_root), "rev-parse", "refs/remotes/origin/main"])
        if verify_fetch.returncode != 0 or remote.returncode != 0 or remote.stdout.strip() != commit:
            raise RuntimeError("Push returned success but origin/main could not be reverified at the new commit")
        if not is_ancestor(repo_root, phase2d_commit, remote.stdout.strip()):
            raise RuntimeError("Pushed origin/main does not contain the original Phase 2D commit")
        logger.write(f"[git] pushed and reverified branch={branch} commit={commit}")
    else:
        logger.write("[git] push failed; both local commits are preserved")
        logger.write(f"[git] manual retry: git -C {shlex.quote(str(repo_root))} push -u origin {shlex.quote(branch + ':' + branch)}")
    return commit, pushed


def execute(args: argparse.Namespace, logger: Logger) -> None:
    stamp = utc_stamp()
    repo_root, remote_url, branch, git_dir, local_head_before, remote_head_before = validate_repository(
        args.repo_root, logger, require_network=not args.no_push
    )
    add_local_git_excludes(git_dir, logger)
    ensure_gitattributes(repo_root, logger)
    package_zip = locate_package_zip(args.zip_path, logger)
    package_target = install_package(package_zip, repo_root, logger)
    venv_python = prepare_venv(logger)
    run_dir, run_relative = next_run_directory(repo_root, stamp)
    logger.write(f"[run] output={run_dir}")

    atomic_json(
        run_dir / "WRAPPER_METADATA.json",
        {
            "created_utc": utc_iso(),
            "wrapper": str(Path(__file__).resolve()),
            "repository_root": str(repo_root),
            "origin": remote_url,
            "branch": branch,
            "local_head_before": local_head_before,
            "origin_main_before": remote_head_before,
            "package_zip": str(package_zip),
            "package_zip_sha256": PACKAGE_ZIP_SHA256,
            "package_installation": str(package_target),
            "venv_python": str(venv_python),
            "new_simulations_authorized": False,
            "auto_push_requested": not args.no_push,
        },
    )

    env = os.environ.copy()
    env.update({"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"})
    unit_rc = run_streaming(
        [str(venv_python), "-m", "unittest", "discover", "-s", "tests", "-v"],
        logger=logger,
        cwd=package_target,
        env=env,
        command_log=run_dir / "UNIT_TESTS.log",
    )

    phase2d_commit = "NOT_AVAILABLE"
    if unit_rc != 0:
        scientific_status = "FAIL_UNIT_TESTS"
        decision = "NOT_AVAILABLE"
        atomic_json(run_dir / "WRAPPER_STATUS.json", {"created_utc": utc_iso(), "status": scientific_status})
    else:
        package_rc = run_streaming(
            [
                str(venv_python), str(package_target / "run_phase2d_r1.py"),
                "--repo-root", str(repo_root),
                "--config", str(package_target / "config" / "phase2d_r1_default.json"),
                "--output", str(run_dir),
            ],
            logger=logger,
            cwd=package_target,
            env=env,
            command_log=run_dir / "PACKAGE_CONSOLE.log",
        )
        package_status = "MISSING"
        status_path = run_dir / "RUN_STATUS.json"
        if status_path.is_file():
            try:
                package_status = str(json.loads(status_path.read_text(encoding="utf-8")).get("status", "UNKNOWN"))
            except Exception:
                package_status = "UNREADABLE"
        decision = "NOT_AVAILABLE"
        decision_path = run_dir / "SCIENTIFIC_DECISION.json"
        if decision_path.is_file():
            try:
                decision = str(json.loads(decision_path.read_text(encoding="utf-8")).get("label", "UNKNOWN"))
            except Exception:
                decision = "UNREADABLE"
        provenance_path = run_dir / "phase2d_artifact_repair" / "PROVENANCE_REPAIR_SUMMARY.json"
        if provenance_path.is_file():
            try:
                phase2d_commit = str(json.loads(provenance_path.read_text(encoding="utf-8")).get("phase2d_commit", "UNKNOWN"))
            except Exception:
                phase2d_commit = "UNREADABLE"
        scientific_status = "PASS" if package_rc == 0 and package_status == "PASS" else "FAIL_PACKAGE_RUN"
        atomic_json(
            run_dir / "WRAPPER_STATUS.json",
            {
                "created_utc": utc_iso(),
                "status": scientific_status,
                "unit_test_returncode": unit_rc,
                "package_returncode": package_rc,
                "package_run_status": package_status,
                "scientific_decision": decision,
                "phase2d_commit": phase2d_commit,
            },
        )

    review_copy, review_hash = copy_review_bundle_to_windows(run_dir, logger) if scientific_status == "PASS" else (None, None)
    logger.flush()
    shutil.copy2(logger.path, run_dir / "WRAPPER_EXECUTION.log")
    (run_dir / "RESULT_READY.txt").write_text(
        "\n".join([
            f"SCIENTIFIC_RUN_STATUS={scientific_status}",
            f"SCIENTIFIC_DECISION={decision}",
            f"REPAIRED_PHASE2D_COMMIT={phase2d_commit}",
            f"RESULT_DIRECTORY={run_relative.as_posix()}",
            f"PACKAGE_SHA256={PACKAGE_ZIP_SHA256}",
            f"EXTERNAL_REVIEW_BUNDLE_WINDOWS={review_copy or 'NOT_COPIED'}",
            f"EXTERNAL_REVIEW_BUNDLE_SHA256={review_hash or 'NOT_AVAILABLE'}",
            "NEW_SIMULATIONS_RUN=false",
            "HUMAN_PROOF_AND_NOVELTY_REVIEW_REQUIRED=true",
        ]) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    if args.no_push:
        logger.write("[git] --no-push selected; no commit or push was performed")
        commit = None
        pushed = False
    elif scientific_status != "PASS":
        logger.write("[git] scientific/provenance run did not pass; no commit or push was attempted")
        commit = None
        pushed = False
    else:
        try:
            commit, pushed = git_commit_and_push(
                repo_root=repo_root,
                package_target=package_target,
                run_dir=run_dir,
                branch=branch,
                status=scientific_status,
                decision=decision,
                phase2d_commit=phase2d_commit,
                logger=logger,
                wrapper_path=Path(__file__),
            )
        except Exception as exc:
            commit = None
            pushed = False
            logger.write(f"[git] ERROR: {exc!r}")
            logger.write(traceback.format_exc().rstrip())

    logger.write("")
    logger.write("=" * 78)
    logger.write(f"FINAL_SCIENTIFIC_RUN_STATUS={scientific_status}")
    logger.write(f"RESULT_DIRECTORY={run_dir}")
    logger.write(f"GIT_BRANCH={branch}")
    logger.write(f"GIT_COMMIT={commit or 'NOT_CREATED_OR_UNKNOWN'}")
    logger.write(f"GIT_PUSHED={'true' if pushed else 'false'}")
    logger.write(f"PHASE2D_R1_DECISION={decision}")
    logger.write(f"REPAIRED_PHASE2D_COMMIT={phase2d_commit}")
    logger.write(f"EXTERNAL_REVIEW_BUNDLE={review_copy or str(run_dir / 'external_review' / 'FIBER_GRAND_Paper_I_External_Review_Bundle_Phase2D_R1.zip')}")
    logger.write(f"EXTERNAL_REVIEW_BUNDLE_SHA256={review_hash or 'SEE_EXTERNAL_REVIEW_BUNDLE.json'}")
    logger.write("NEW_SIMULATIONS_RUN=false")
    logger.write("Next: send the external-review bundle for independent proof and novelty review.")
    logger.write("The VS Code terminal remains open; this wrapper issued no shell exit command.")
    logger.write("=" * 78)


def main() -> None:
    args = parse_args()
    temp_log = Path(tempfile.gettempdir()) / f"FIBER_GRAND_PHASE2D_R1_WRAPPER_{utc_stamp()}_{os.getpid()}.log"
    logger = Logger(temp_log)
    try:
        logger.write("FIBER-GRAND Paper I - Phase 2D-R1 provenance-repair/review-handoff wrapper")
        logger.write(f"WRAPPER_LOG={temp_log}")
        execute(args, logger)
    except KeyboardInterrupt:
        logger.write("[wrapper] interrupted by user; partial files were preserved")
        logger.write("The VS Code terminal remains open; this wrapper issued no shell exit command.")
    except Exception as exc:
        logger.write(f"[wrapper] FATAL ERROR: {exc!r}")
        logger.write(traceback.format_exc().rstrip())
        logger.write("The VS Code terminal remains open; this wrapper issued no shell exit command.")
    finally:
        logger.close()


if __name__ == "__main__":
    main()
