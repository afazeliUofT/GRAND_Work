#!/usr/bin/env python3
"""One-command WSL launcher for the FIBER-GRAND Paper-I Phase-2B-R1 gate.

Default use from the connected VS Code WSL terminal:
    cd /home/afazeli2006/GRAND_Work
    python3 RUN_FIBER_GRAND_PHASE2B_R1.py

The script deliberately never executes a shell `exit`, never replaces the parent
shell, and catches top-level failures so the VS Code terminal remains open.
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

PACKAGE_ZIP_BASENAME = "FIBER_GRAND_PHASE2B_R1_MANIFEST_REPAIR_AND_REPLAY_GATE_v1_1_2026-08-03.zip"
PACKAGE_ZIP_STEM = "FIBER_GRAND_PHASE2B_R1_MANIFEST_REPAIR_AND_REPLAY_GATE_v1_1_2026-08-03"
PACKAGE_ZIP_SHA256 = "468350e52390abbba7ca519019eca23a2e23b2d2204f8ddd8e94fc3df3a7e2ec"
PACKAGE_ROOT_NAME = "FIBER_GRAND_PHASE2B_R1_MANIFEST_REPAIR_AND_REPLAY_GATE_v1_1"
DEFAULT_REPO_ROOT = Path("/home/afazeli2006/GRAND_Work")
PACKAGE_RELATIVE_PATH = Path("experiments") / PACKAGE_ROOT_NAME
RESULTS_NAMESPACE = Path("results") / "FIBER_GRAND_Phase2B_R1"
EXPECTED_GITHUB_REPOSITORY = "afazeliuoft/grand_work"
MINIMUM_PYTHON = (3, 10)
MAX_UNCOMPRESSED_PACKAGE_BYTES = 100 * 1024 * 1024
FROZEN_PHASE2A_COMMIT = "c4073f84a2e8c7f6d19281db64e862347602fa02"
REQUIRED_PRIOR_PHASE2B_COMMIT = "35eeebb685e50824d8ddc3e88403e1c5a9f0bd1c"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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

    def close(self) -> None:
        try:
            self._handle.flush()
            self._handle.close()
        except Exception:
            pass


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install and run the FIBER-GRAND Phase-2B-R1 manifest-repair and replay gate in WSL.")
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--zip", dest="zip_path", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--smoke", action="store_true", help="Run the included smoke configuration instead of the bounded default.")
    parser.add_argument("--no-push", action="store_true", help="Run locally without Git staging, commit, or push.")
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


def validate_repository(repo_root: Path, logger: Logger) -> tuple[Path, str, str, Path]:
    repo_root = repo_root.expanduser().resolve()
    probe = capture(["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"])
    if probe.returncode != 0:
        raise RuntimeError(f"Not a Git working tree: {repo_root}\n{probe.stderr.strip()}")
    actual_root = Path(probe.stdout.strip()).resolve()
    if actual_root != repo_root:
        raise RuntimeError(f"Expected repository root {repo_root}, but Git reports {actual_root}")

    remote_probe = capture(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
    if remote_probe.returncode != 0:
        raise RuntimeError(f"Cannot read Git remote 'origin': {remote_probe.stderr.strip()}")
    remote_url = remote_probe.stdout.strip()
    normalized = normalize_github_remote(remote_url)
    if normalized != EXPECTED_GITHUB_REPOSITORY:
        raise RuntimeError(
            f"Refusing to operate on unexpected origin {remote_url!r}; expected GitHub repository "
            f"{EXPECTED_GITHUB_REPOSITORY!r}."
        )

    branch_probe = capture(["git", "-C", str(repo_root), "symbolic-ref", "--quiet", "--short", "HEAD"])
    if branch_probe.returncode != 0 or not branch_probe.stdout.strip():
        raise RuntimeError("The repository is in detached-HEAD state; switch to a branch before running.")
    branch = branch_probe.stdout.strip()

    git_dir_probe = capture(["git", "-C", str(repo_root), "rev-parse", "--git-dir"])
    if git_dir_probe.returncode != 0:
        raise RuntimeError(f"Cannot resolve .git directory: {git_dir_probe.stderr.strip()}")
    git_dir = Path(git_dir_probe.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (repo_root / git_dir).resolve()

    logger.write(f"[repo] root={repo_root}")
    logger.write(f"[repo] origin={remote_url}")
    logger.write(f"[repo] branch={branch}")
    return repo_root, remote_url, branch, git_dir


def add_local_git_excludes(git_dir: Path, logger: Logger) -> None:
    exclude_path = git_dir / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    patterns = [
        ".venv/",
        ".venv*/",
        "**/.venv/",
        "**/.venv*/",
        "**/__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
        "results/FIBER_GRAND_Phase2B_R1/**/FIBER_GRAND_PHASE2B_R1_RETURN_*.zip",
    ]
    lines = existing.splitlines()
    changed = False
    for pattern in patterns:
        if pattern not in lines:
            lines.append(pattern)
            changed = True
    if changed:
        exclude_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    logger.write(f"[git] local excludes verified at {exclude_path}")


def ensure_gitattributes(repo_root: Path, logger: Logger) -> None:
    path = repo_root / ".gitattributes"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    required = ["*.csv text eol=lf", "*.tsv text eol=lf", "*.json text eol=lf", "*.md text eol=lf", "*.tex text eol=lf", "*.py text eol=lf", "*.cpp text eol=lf", "*.log text eol=lf", "*.txt text eol=lf", "*.sha256 text eol=lf"]
    lines = existing.splitlines()
    conflicting = [line for line in lines if line.strip().startswith("*.csv ") and line.strip() != "*.csv text eol=lf"]
    if conflicting:
        raise RuntimeError(f"Conflicting CSV .gitattributes rule(s): {conflicting}")
    changed = False
    for rule in required:
        if rule not in lines:
            lines.append(rule); changed = True
    if changed:
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    logger.write(f"[git] repository line-ending policy verified at {path}")


def download_directories() -> list[Path]:
    candidates = [Path.home() / "Downloads"]
    for drive in ("c", "d"):
        users_root = Path(f"/mnt/{drive}/Users")
        if users_root.is_dir():
            candidates.extend(path / "Downloads" for path in users_root.iterdir() if path.is_dir())
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def locate_package_zip(explicit: Path | None, logger: Logger) -> Path:
    if explicit is not None:
        candidates = [explicit.expanduser().resolve()]
    else:
        candidates = []
        for directory in download_directories():
            if not directory.is_dir():
                continue
            candidates.extend(directory.glob(PACKAGE_ZIP_BASENAME))
            candidates.extend(directory.glob(PACKAGE_ZIP_STEM + "*.zip"))
    deduplicated: dict[str, Path] = {}
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            deduplicated[str(resolved)] = resolved
    ordered = sorted(deduplicated.values(), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    mismatches: list[str] = []
    for candidate in ordered:
        digest = sha256_file(candidate)
        if digest == PACKAGE_ZIP_SHA256:
            logger.write(f"[package] located={candidate}")
            logger.write(f"[package] sha256={digest} (verified)")
            return candidate
        mismatches.append(f"{candidate}: {digest}")
    details = "\n".join(mismatches) if mismatches else "No candidate file was found."
    raise FileNotFoundError(
        f"Could not find a package ZIP with the required SHA-256. Expected filename {PACKAGE_ZIP_BASENAME!r}.\n{details}"
    )


def validate_zip_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename.replace("\\", "/")
    pure = PurePosixPath(name)
    if not name or name.startswith("/") or pure.is_absolute() or ".." in pure.parts:
        raise RuntimeError(f"Unsafe ZIP member path: {info.filename!r}")
    unix_mode = info.external_attr >> 16
    if stat.S_ISLNK(unix_mode):
        raise RuntimeError(f"Symbolic links are forbidden in the package: {info.filename!r}")
    if unix_mode and not (stat.S_ISREG(unix_mode) or stat.S_ISDIR(unix_mode)):
        raise RuntimeError(f"Non-regular ZIP member is forbidden: {info.filename!r}")
    return pure


def verify_package_manifest(package_root: Path) -> None:
    manifest = package_root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        raise RuntimeError("Extracted package has no PACKAGE_MANIFEST.sha256")
    expected: dict[str, str] = {}
    for raw_line in manifest.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            digest, relative = raw_line.split("  ", 1)
        except ValueError as exc:
            raise RuntimeError(f"Malformed package manifest line: {raw_line!r}") from exc
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeError(f"Unsafe package-manifest path: {relative!r}")
        expected[relative] = digest
    actual_files = {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and path != manifest
    }
    if actual_files != set(expected):
        missing = sorted(set(expected) - actual_files)
        extra = sorted(actual_files - set(expected))
        raise RuntimeError(f"Package manifest file-set mismatch; missing={missing}, extra={extra}")
    for relative, expected_digest in expected.items():
        actual_digest = sha256_file(package_root / relative)
        if actual_digest != expected_digest:
            raise RuntimeError(
                f"Package manifest hash mismatch for {relative}: expected {expected_digest}, got {actual_digest}"
            )


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in root.rglob("*")
        if path.is_file()
    }


def install_package(zip_path: Path, repo_root: Path, logger: Logger) -> Path:
    target = repo_root / PACKAGE_RELATIVE_PATH
    temporary_parent = Path(tempfile.mkdtemp(prefix=".fiber_phase2b_r1_extract_", dir=str(repo_root)))
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            infos = archive.infolist()
            if not infos:
                raise RuntimeError("Package ZIP is empty")
            total = sum(info.file_size for info in infos)
            if total > MAX_UNCOMPRESSED_PACKAGE_BYTES:
                raise RuntimeError(f"Package expands to {total} bytes, above the safety limit")
            roots: set[str] = set()
            for info in infos:
                pure = validate_zip_member(info)
                if pure.parts:
                    roots.add(pure.parts[0])
            if roots != {PACKAGE_ROOT_NAME}:
                raise RuntimeError(f"Unexpected ZIP roots: {sorted(roots)}")
            archive.extractall(temporary_parent)
        extracted = temporary_parent / PACKAGE_ROOT_NAME
        verify_package_manifest(extracted)
        if target.exists():
            if tree_hashes(target) != tree_hashes(extracted):
                raise RuntimeError(
                    f"Existing package directory differs from the verified ZIP: {target}. "
                    "It was not overwritten; move or review it manually."
                )
            logger.write(f"[package] existing verified installation reused: {target}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(extracted, target)
            logger.write(f"[package] installed={target}")
        verify_package_manifest(target)
        return target
    finally:
        shutil.rmtree(temporary_parent, ignore_errors=True)


def python_version(python_executable: Path) -> tuple[int, int, int]:
    probe = capture([
        str(python_executable),
        "-c",
        "import json,sys; print(json.dumps(list(sys.version_info[:3])))",
    ])
    if probe.returncode != 0:
        raise RuntimeError(f"Cannot run {python_executable}: {probe.stderr.strip()}")
    values = json.loads(probe.stdout.strip())
    return int(values[0]), int(values[1]), int(values[2])


def prepare_venv(logger: Logger, stamp: str) -> Path:
    venv_root = Path.home() / ".venvs" / "fiber_grand_phase2b_r1_v1_1"
    venv_python = venv_root / "bin" / "python"
    recreate = False
    if venv_python.exists():
        try:
            version = python_version(venv_python)
            recreate = version[:2] < MINIMUM_PYTHON
        except Exception:
            recreate = True
        if recreate:
            backup = venv_root.with_name(venv_root.name + f".broken_{stamp}")
            os.replace(venv_root, backup)
            logger.write(f"[venv] moved unusable environment to {backup}")
    if not venv_python.exists():
        venv_root.parent.mkdir(parents=True, exist_ok=True)
        rc = run_streaming([sys.executable, "-m", "venv", str(venv_root)], logger=logger)
        if rc != 0:
            raise RuntimeError("Failed to create the Phase-2B-R1 virtual environment")
    version = python_version(venv_python)
    if version[:2] < MINIMUM_PYTHON:
        raise RuntimeError(f"Venv Python {version} is below required {MINIMUM_PYTHON}")
    logger.write(f"[venv] interpreter={venv_python}")
    logger.write(f"[venv] version={version}; no third-party dependencies are required")
    logger.write("[venv] the wrapper executes the package with this interpreter; parent-shell activation is unnecessary")
    return venv_python


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


def write_git_context(repo_root: Path, run_dir: Path, remote_url: str, branch: str) -> None:
    status = capture(["git", "-C", str(repo_root), "status", "--short", "--branch"])
    (run_dir / "GIT_CONTEXT_BEFORE.txt").write_text(
        f"ORIGIN={remote_url}\nBRANCH={branch}\n\n{status.stdout}{status.stderr}",
        encoding="utf-8",
    )


def path_has_venv(path_text: str) -> bool:
    return any(part == ".venv" or part.startswith(".venv") for part in PurePosixPath(path_text).parts)


def write_commit_ready_manifest(run_dir: Path) -> Path:
    """Hash the exact text artifacts intended for the Phase-2B-R1 result commit.

    The local return ZIP is deliberately excluded because it is not committed. Its
    `.sha256` sidecar is included. The manifest excludes itself to avoid a circular
    digest definition.
    """
    manifest = run_dir / "COMMIT_READY_MANIFEST.sha256"
    scope_note = run_dir / "MANIFEST_SCOPE.md"
    scope_note.write_text(
        "# Phase 2B-R1 result-manifest scope\n\n"
        "`MANIFEST.sha256` is the package-generated scientific-output manifest created "
        "before wrapper metadata is appended. `COMMIT_READY_MANIFEST.sha256` is generated "
        "by the WSL wrapper after all result metadata and the GitHub review pointer exist. "
        "It covers every committed file in this result directory except itself and the "
        "uncommitted local return ZIP. The return ZIP's SHA-256 sidecar is covered.\n",
        encoding="utf-8",
        newline="\n",
    )
    lines: list[str] = []
    for path in sorted(candidate for candidate in run_dir.rglob("*") if candidate.is_file()):
        if path == manifest:
            continue
        if path.name.startswith("FIBER_GRAND_PHASE2B_R1_RETURN_") and path.suffix == ".zip":
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return manifest


def parse_sha256_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, relative = raw.split("  ", 1)
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeError(f"Unsafe result-manifest path: {relative!r}")
        if relative in entries:
            raise RuntimeError(f"Duplicate result-manifest path: {relative!r}")
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


def git_commit_and_push(
    *,
    repo_root: Path,
    package_target: Path,
    run_dir: Path,
    status: str,
    branch: str,
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
        },
    )
    review_pointer = run_dir / "GITHUB_REVIEW_POINTER.json"
    atomic_json(
        review_pointer,
        {
            "branch": branch,
            "origin_repository": EXPECTED_GITHUB_REPOSITORY,
            "result_directory": run_relative.as_posix(),
            "package_directory": package_target.relative_to(repo_root).as_posix(),
            "scientific_run_status": status,
            "note": "Commit hash is printed by the wrapper after this file is committed.",
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
        wrapper_relative = wrapper_path.resolve().relative_to(repo_root).as_posix()
        pathspecs.append(wrapper_relative)
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
        if path_has_venv(path) or Path(path).name.startswith("FIBER_GRAND_PHASE2B_R1_RETURN_") and path.endswith(".zip")
    ]
    if forbidden:
        raise RuntimeError(f"Safety stop: forbidden paths became staged: {forbidden}")
    verify_result_manifest_in_git(
        repo_root=repo_root,
        run_relative=run_relative,
        manifest=commit_ready_manifest,
        treeish=None,
    )
    logger.write("[git] commit-ready result manifest matches every staged result blob")
    if not staged_paths:
        logger.write("[git] no new changes under the package/result path; no commit created")
        head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        return (head.stdout.strip() if head.returncode == 0 else None), False

    logger.write(f"[git] staged {len(staged_paths)} intended files; no .venv or return ZIP is staged")
    message = f"FIBER-GRAND Phase 2B-R1 manifest-repair/replay gate {status} {run_dir.name}"
    commit = run_streaming(
        ["git", "-C", str(repo_root), "commit", "--only", "-m", message, "--", *pathspecs],
        logger=logger,
    )
    if commit != 0:
        raise RuntimeError("Git commit failed; results remain in the working tree/index for manual review")
    head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    if head.returncode != 0:
        raise RuntimeError(f"Cannot read new commit: {head.stderr.strip()}")
    commit_hash = head.stdout.strip()
    committed_names = capture([
        "git", "-C", str(repo_root), "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash
    ])
    committed_paths = [line.strip() for line in committed_names.stdout.splitlines() if line.strip()]
    forbidden_commit = [path for path in committed_paths if path_has_venv(path)]
    if forbidden_commit:
        raise RuntimeError(f"Safety stop: commit unexpectedly contains venv paths: {forbidden_commit}")
    verify_result_manifest_in_git(
        repo_root=repo_root,
        run_relative=run_relative,
        manifest=commit_ready_manifest,
        treeish=commit_hash,
    )
    logger.write("[git] committed result blobs reverified against COMMIT_READY_MANIFEST.sha256")

    logger.write(f"[git] commit={commit_hash}")
    push_rc = run_streaming(
        ["git", "-C", str(repo_root), "push", "-u", "origin", f"{branch}:{branch}"],
        logger=logger,
    )
    pushed = push_rc == 0
    if pushed:
        logger.write(f"[git] pushed branch={branch} commit={commit_hash}")
    else:
        logger.write("[git] push failed; the local commit is preserved")
        logger.write(f"[git] manual retry: git -C {shlex.quote(str(repo_root))} push -u origin {shlex.quote(branch + ':' + branch)}")
    return commit_hash, pushed


def execute(args: argparse.Namespace, logger: Logger) -> None:
    stamp = utc_stamp()
    repo_root, remote_url, branch, git_dir = validate_repository(args.repo_root, logger)
    required_ancestors = (
        (FROZEN_PHASE2A_COMMIT, "frozen Phase 2A PASS"),
        (REQUIRED_PRIOR_PHASE2B_COMMIT, "recorded Phase 2B failed-run"),
    )
    for commit_hash, label in required_ancestors:
        ancestry = capture([
            "git", "-C", str(repo_root), "merge-base", "--is-ancestor",
            commit_hash, "HEAD",
        ])
        if ancestry.returncode != 0:
            raise RuntimeError(
                f"Required {label} commit {commit_hash} is not an ancestor of the current HEAD"
            )
        logger.write(f"[repo] {label} commit verified as ancestor: {commit_hash}")
    add_local_git_excludes(git_dir, logger)
    ensure_gitattributes(repo_root, logger)
    package_zip = locate_package_zip(args.zip_path, logger)
    package_target = install_package(package_zip, repo_root, logger)
    venv_python = prepare_venv(logger, stamp)

    run_dir, run_relative = next_run_directory(repo_root, stamp)
    logger.write(f"[run] output={run_dir}")
    write_git_context(repo_root, run_dir, remote_url, branch)
    atomic_json(
        run_dir / "WRAPPER_METADATA.json",
        {
            "created_utc": utc_iso(),
            "wrapper": str(Path(__file__).resolve()),
            "wrapper_sha256": sha256_file(Path(__file__).resolve()),
            "repository_root": str(repo_root),
            "origin": remote_url,
            "branch": branch,
            "package_zip": str(package_zip),
            "package_zip_sha256": PACKAGE_ZIP_SHA256,
            "package_installation": str(package_target),
            "venv_python": str(venv_python),
            "profile": "smoke" if args.smoke else "manifest_repair_full_replay_default",
            "auto_push_requested": not args.no_push,
        },
    )

    env = os.environ.copy()
    env.update({
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    })

    unit_log = run_dir / "UNIT_TESTS.log"
    unit_rc = run_streaming(
        [str(venv_python), "-m", "unittest", "discover", "-s", "tests", "-v"],
        logger=logger,
        cwd=package_target,
        env=env,
        command_log=unit_log,
    )
    if unit_rc != 0:
        scientific_status = "FAIL_UNIT_TESTS"
        atomic_json(run_dir / "WRAPPER_STATUS.json", {
            "created_utc": utc_iso(), "status": scientific_status, "unit_test_returncode": unit_rc,
        })
    else:
        config_name = "phase2b_r1_smoke.json" if args.smoke else "phase2b_r1_default.json"
        package_log = run_dir / "PACKAGE_CONSOLE.log"
        package_rc = run_streaming(
            [
                str(venv_python),
                str(package_target / "run_phase2b_r1.py"),
                "--repo-root", str(repo_root),
                "--config", str(package_target / "config" / config_name),
                "--output", str(run_dir),
                "--cache-root", str(Path.home() / ".cache" / "fiber_grand_phase2b_r1_v1_1"),
            ],
            logger=logger,
            cwd=package_target,
            env=env,
            command_log=package_log,
        )
        run_status_path = run_dir / "RUN_STATUS.json"
        package_status = "MISSING"
        if run_status_path.is_file():
            try:
                package_status = str(json.loads(run_status_path.read_text(encoding="utf-8")).get("status", "UNKNOWN"))
            except Exception:
                package_status = "UNREADABLE"
        scientific_status = "PASS" if package_rc == 0 and package_status == "PASS" else "FAIL_PACKAGE_RUN"
        atomic_json(
            run_dir / "WRAPPER_STATUS.json",
            {
                "created_utc": utc_iso(),
                "status": scientific_status,
                "unit_test_returncode": unit_rc,
                "package_returncode": package_rc,
                "package_run_status": package_status,
            },
        )

    # Freeze the execution log before Git actions so the committed snapshot does not
    # become dirty while push messages continue to print to the temporary logger.
    logger._handle.flush()  # internal but deliberate: take a coherent snapshot
    shutil.copy2(logger.path, run_dir / "WRAPPER_EXECUTION.log")
    (run_dir / "RESULT_READY.txt").write_text(
        "\n".join([
            f"SCIENTIFIC_RUN_STATUS={scientific_status}",
            f"RESULT_DIRECTORY={run_relative.as_posix()}",
            f"PACKAGE_SHA256={PACKAGE_ZIP_SHA256}",
            "HUMAN_SCIENTIFIC_REVIEW_REQUIRED=true",
        ]) + "\n",
        encoding="utf-8",
    )

    if args.no_push:
        logger.write("[git] --no-push selected; no Git staging, commit, or push was performed")
        commit_hash = None
        pushed = False
    else:
        try:
            commit_hash, pushed = git_commit_and_push(
                repo_root=repo_root,
                package_target=package_target,
                run_dir=run_dir,
                status=scientific_status,
                branch=branch,
                logger=logger,
                wrapper_path=Path(__file__),
            )
        except Exception as exc:
            commit_hash = None
            pushed = False
            logger.write(f"[git] ERROR: {exc!r}")
            logger.write(traceback.format_exc().rstrip())

    logger.write("")
    logger.write("=" * 78)
    logger.write(f"FINAL_SCIENTIFIC_RUN_STATUS={scientific_status}")
    logger.write(f"RESULT_DIRECTORY={run_dir}")
    logger.write(f"GIT_BRANCH={branch}")
    logger.write(f"GIT_COMMIT={commit_hash or 'NOT_CREATED_OR_UNKNOWN'}")
    logger.write(f"GIT_PUSHED={'true' if pushed else 'false'}")
    decision_path = run_dir / "SCIENTIFIC_DECISION.json"
    decision_label = "NOT_AVAILABLE"
    if decision_path.is_file():
        try:
            decision_label = str(json.loads(decision_path.read_text(encoding="utf-8")).get("label", "UNKNOWN"))
        except Exception:
            decision_label = "UNREADABLE"
    logger.write(f"PHASE2B_R1_DECISION={decision_label}")
    logger.write("Review the result directory and the Git commit before authorizing any later evidence phase.")
    logger.write("The VS Code terminal remains open; this wrapper issued no shell exit command.")
    logger.write("=" * 78)


def main() -> None:
    args = parse_args()
    temp_log = Path(tempfile.gettempdir()) / f"FIBER_GRAND_PHASE2B_R1_WRAPPER_{utc_stamp()}_{os.getpid()}.log"
    logger = Logger(temp_log)
    try:
        logger.write("FIBER-GRAND Paper I — Phase 2B-R1 manifest-repair and replay gate wrapper")
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
    # Do not raise SystemExit: ending this Python process naturally leaves the
    # interactive VS Code WSL shell and terminal open, including after failures.
    main()
