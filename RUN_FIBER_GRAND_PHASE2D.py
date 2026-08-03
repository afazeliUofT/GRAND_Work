#!/usr/bin/env python3
"""One-command WSL launcher for FIBER-GRAND Paper-I Phase 2D.

Run from the connected VS Code WSL terminal:
    cd /home/afazeli2006/GRAND_Work
    python3 RUN_FIBER_GRAND_PHASE2D.py

This wrapper never executes a shell ``exit`` and never replaces the parent shell,
so the VS Code terminal remains open after success, failure, or interruption.
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

PACKAGE_ZIP_BASENAME = "FIBER_GRAND_PHASE2D_MANUSCRIPT_INTEGRATION_REVIEW_v1_0_2026-08-03.zip"
PACKAGE_ZIP_STEM = "FIBER_GRAND_PHASE2D_MANUSCRIPT_INTEGRATION_REVIEW_v1_0_2026-08-03"
PACKAGE_ZIP_SHA256 = "7aca6640b3b310151a86975d3a0e8a4b1d2baede41aa99f2cd9870e27d011adb"
PACKAGE_ROOT_NAME = "FIBER_GRAND_PHASE2D_MANUSCRIPT_INTEGRATION_REVIEW_v1_0"
DEFAULT_REPO_ROOT = Path("/home/afazeli2006/GRAND_Work")
PACKAGE_RELATIVE_PATH = Path("experiments") / PACKAGE_ROOT_NAME
RESULTS_NAMESPACE = Path("results") / "FIBER_GRAND_Phase2D"
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        rc = process.wait()
        logger.write(f"[command return code] {rc}")
        return rc
    except OSError as exc:
        logger.write(f"[command launch failure] {exc!r}")
        if command_handle is not None:
            command_handle.write(f"COMMAND_LAUNCH_FAILURE={exc!r}\n")
        return 127
    finally:
        if command_handle is not None:
            command_handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FIBER-GRAND Phase-2D manuscript-integration gate.")
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--zip", dest="zip_path", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--no-push", action="store_true", help="Run without Git commit/push.")
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

    ancestor = capture(["git", "-C", str(repo_root), "merge-base", "--is-ancestor", REQUIRED_PHASE2C_COMMIT, "HEAD"])
    if ancestor.returncode != 0:
        head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"]).stdout.strip()
        raise RuntimeError(f"Required Phase-2C commit is not an ancestor of HEAD {head}")

    git_dir_probe = capture(["git", "-C", str(repo_root), "rev-parse", "--git-dir"])
    if git_dir_probe.returncode != 0:
        raise RuntimeError(f"Cannot resolve .git directory: {git_dir_probe.stderr.strip()}")
    git_dir = Path(git_dir_probe.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (repo_root / git_dir).resolve()

    logger.write(f"[repo] root={repo_root}")
    logger.write(f"[repo] origin={remote_url}")
    logger.write(f"[repo] branch={branch}")
    logger.write(f"[repo] Phase 2C GO commit verified as ancestor: {REQUIRED_PHASE2C_COMMIT}")
    return repo_root, remote_url, branch, git_dir


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
        ".pytest_cache/", "results/FIBER_GRAND_Phase2D/**/FIBER_GRAND_PHASE2D_RETURN_*.zip",
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
            candidates.extend(p / "Downloads" for p in users.iterdir() if p.is_dir())
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
        candidates.append(explicit.expanduser())
    else:
        for directory in download_directories():
            if directory.is_dir():
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
    detail = "\n".join(mismatches) if mismatches else "No candidate ZIP found."
    raise FileNotFoundError(f"Could not locate the required package ZIP.\n{detail}")


def validate_zip_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename.replace("\\", "/")
    pure = PurePosixPath(name)
    if not name or name.startswith("/") or pure.is_absolute() or ".." in pure.parts:
        raise RuntimeError(f"Unsafe ZIP path: {info.filename!r}")
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise RuntimeError(f"Symbolic links are forbidden: {info.filename!r}")
    if mode and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise RuntimeError(f"Non-regular ZIP member: {info.filename!r}")
    return pure


def verify_package_manifest(root: Path) -> None:
    manifest = root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        raise RuntimeError("Package has no PACKAGE_MANIFEST.sha256")
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeError(f"Unsafe manifest path: {relative!r}")
        expected[relative] = digest
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p != manifest
    }
    if actual != set(expected):
        raise RuntimeError(
            f"Manifest file-set mismatch; missing={sorted(set(expected)-actual)}, extra={sorted(actual-set(expected))}"
        )
    for relative, digest in expected.items():
        got = sha256_file(root / relative)
        if got != digest:
            raise RuntimeError(f"Package hash mismatch for {relative}: expected {digest}, got {got}")


def install_package(package_zip: Path, repo_root: Path, logger: Logger) -> Path:
    experiments = repo_root / "experiments"
    experiments.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="fiber_phase2d_extract_", dir=str(experiments)))
    try:
        with zipfile.ZipFile(package_zip) as archive:
            infos = archive.infolist()
            total = 0
            roots: set[str] = set()
            for info in infos:
                pure = validate_zip_member(info)
                roots.add(pure.parts[0])
                total += info.file_size
                if total > MAX_UNCOMPRESSED_PACKAGE_BYTES:
                    raise RuntimeError("Package exceeds uncompressed-size safety limit")
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
    venv = Path.home() / ".venvs" / "fiber_grand_phase2d_v1_0"
    python = venv / "bin" / "python"
    if not python.is_file():
        rc = run_streaming([sys.executable, "-m", "venv", str(venv)], logger=logger)
        if rc != 0:
            raise RuntimeError("Unable to create the isolated Python environment")
    probe = capture([str(python), "-c", "import sys; print('.'.join(map(str,sys.version_info[:3])))"])
    if probe.returncode != 0:
        raise RuntimeError(f"Unable to execute venv Python: {probe.stderr.strip()}")
    version = tuple(int(x) for x in probe.stdout.strip().split("."))
    if version < MINIMUM_PYTHON:
        raise RuntimeError(f"Python {version} is too old; require {MINIMUM_PYTHON}")
    logger.write(f"[venv] interpreter={python}")
    logger.write(f"[venv] version={version}; no third-party Python dependencies are required")
    logger.write("[venv] parent-shell activation is unnecessary")
    return python


def next_run_directory(repo_root: Path, stamp: str) -> tuple[Path, Path]:
    base = repo_root / RESULTS_NAMESPACE / f"run_{stamp}"
    run = base
    index = 1
    while run.exists():
        run = Path(str(base) + f"_{index}")
        index += 1
    run.mkdir(parents=True)
    return run, run.relative_to(repo_root)


def path_has_venv(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(part == ".venv" or part.startswith(".venv") for part in parts)


def verify_result_manifest_against_commit(repo_root: Path, commit: str, run_relative: Path) -> None:
    manifest_rel = (run_relative / "MANIFEST.sha256").as_posix()
    manifest_probe = capture(["git", "-C", str(repo_root), "show", f"{commit}:{manifest_rel}"])
    if manifest_probe.returncode != 0:
        raise RuntimeError("Committed result has no readable MANIFEST.sha256")
    for line in manifest_probe.stdout.splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        blob_rel = (run_relative / relative).as_posix()
        blob = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{commit}:{blob_rel}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if blob.returncode != 0:
            raise RuntimeError(f"Committed manifest references missing blob {blob_rel}")
        got = sha256_bytes(blob.stdout)
        if got != expected:
            raise RuntimeError(f"Committed manifest mismatch for {blob_rel}: expected {expected}, got {got}")


def git_commit_and_push(
    *,
    repo_root: Path,
    package_target: Path,
    run_dir: Path,
    run_relative: Path,
    branch: str,
    status: str,
    decision: str,
    logger: Logger,
    wrapper_path: Path,
) -> tuple[str | None, bool]:
    latest = repo_root / RESULTS_NAMESPACE / "LATEST.json"
    atomic_json(
        latest,
        {
            "created_utc": utc_iso(),
            "package_zip_sha256": PACKAGE_ZIP_SHA256,
            "result_directory": run_relative.as_posix(),
            "scientific_run_status": status,
            "scientific_decision": decision,
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
        },
    )

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
        or (Path(path).name.startswith("FIBER_GRAND_PHASE2D_RETURN_") and path.endswith(".zip"))
    ]
    if forbidden:
        raise RuntimeError(f"Safety stop: forbidden paths staged: {forbidden}")
    if not staged_paths:
        head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        return (head.stdout.strip() if head.returncode == 0 else None), False

    logger.write(f"[git] staged {len(staged_paths)} intended files; no .venv or return ZIP is staged")
    message = f"FIBER-GRAND Phase 2D manuscript integration {status} {run_dir.name}"
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
    verify_result_manifest_against_commit(repo_root, commit, run_relative)
    logger.write("[git] committed result blobs verified against MANIFEST.sha256")
    push_rc = run_streaming(
        ["git", "-C", str(repo_root), "push", "-u", "origin", f"{branch}:{branch}"],
        logger=logger,
    )
    pushed = push_rc == 0
    if pushed:
        logger.write(f"[git] pushed branch={branch} commit={commit}")
    else:
        logger.write("[git] push failed; the local commit is preserved")
        logger.write(f"[git] manual retry: git -C {shlex.quote(str(repo_root))} push -u origin {shlex.quote(branch + ':' + branch)}")
    return commit, pushed


def execute(args: argparse.Namespace, logger: Logger) -> None:
    stamp = utc_stamp()
    repo_root, remote_url, branch, git_dir = validate_repository(args.repo_root, logger)
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

    if unit_rc != 0:
        scientific_status = "FAIL_UNIT_TESTS"
        decision = "NOT_AVAILABLE"
        atomic_json(run_dir / "WRAPPER_STATUS.json", {"created_utc": utc_iso(), "status": scientific_status})
    else:
        package_rc = run_streaming(
            [
                str(venv_python), str(package_target / "run_phase2d.py"),
                "--repo-root", str(repo_root),
                "--config", str(package_target / "config" / "phase2d_default.json"),
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
        scientific_status = "PASS" if package_rc == 0 and package_status == "PASS" else "FAIL_PACKAGE_RUN"
        atomic_json(
            run_dir / "WRAPPER_STATUS.json",
            {
                "created_utc": utc_iso(), "status": scientific_status,
                "unit_test_returncode": unit_rc, "package_returncode": package_rc,
                "package_run_status": package_status, "scientific_decision": decision,
            },
        )

    logger.flush()
    shutil.copy2(logger.path, run_dir / "WRAPPER_EXECUTION.log")
    (run_dir / "RESULT_READY.txt").write_text(
        "\n".join([
            f"SCIENTIFIC_RUN_STATUS={scientific_status}",
            f"SCIENTIFIC_DECISION={decision}",
            f"RESULT_DIRECTORY={run_relative.as_posix()}",
            f"PACKAGE_SHA256={PACKAGE_ZIP_SHA256}",
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
    else:
        try:
            commit, pushed = git_commit_and_push(
                repo_root=repo_root,
                package_target=package_target,
                run_dir=run_dir,
                run_relative=run_relative,
                branch=branch,
                status=scientific_status,
                decision=decision,
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
    logger.write(f"PHASE2D_DECISION={decision}")
    logger.write("NEW_SIMULATIONS_RUN=false")
    logger.write("The next evidence is independent proof and novelty review, not another simulation campaign.")
    logger.write("The VS Code terminal remains open; this wrapper issued no shell exit command.")
    logger.write("=" * 78)


def main() -> None:
    args = parse_args()
    temp_log = Path(tempfile.gettempdir()) / f"FIBER_GRAND_PHASE2D_WRAPPER_{utc_stamp()}_{os.getpid()}.log"
    logger = Logger(temp_log)
    try:
        logger.write("FIBER-GRAND Paper I - Phase 2D manuscript-integration wrapper")
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
