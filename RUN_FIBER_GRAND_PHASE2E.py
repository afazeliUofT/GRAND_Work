#!/usr/bin/env python3
"""One-command WSL launcher for FIBER-GRAND Paper-I Phase 2E.

Run from the connected VS Code WSL terminal:
    cd /home/afazeli2006/GRAND_Work
    python3 RUN_FIBER_GRAND_PHASE2E.py

The wrapper installs one immutable ZIP, creates an isolated virtual environment outside Git,
runs no simulations, compiles/verifies the repaired manuscript and supplement, creates a minimal
standalone bundle, commits the package/results, and pushes the current main branch. It never calls
shell ``exit`` or replaces the parent shell, so the VS Code terminal remains open after success,
failure, or interruption.
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
from typing import Sequence

PACKAGE_ZIP_BASENAME = "FIBER_GRAND_PHASE2E_REVIEW_ADJUDICATION_ITW_FINALIZATION_v1_0_2026-08-03.zip"
PACKAGE_ZIP_STEM = "FIBER_GRAND_PHASE2E_REVIEW_ADJUDICATION_ITW_FINALIZATION_v1_0_2026-08-03"
PACKAGE_ZIP_SHA256 = "67e9415d566493b45d92c4b02592a4f6f9959a914d9b02715b78d5af9d169691"
PACKAGE_ROOT_NAME = "FIBER_GRAND_PHASE2E_REVIEW_ADJUDICATION_ITW_FINALIZATION_v1_0"
DEFAULT_REPO_ROOT = Path("/home/afazeli2006/GRAND_Work")
PACKAGE_RELATIVE_PATH = Path("experiments") / PACKAGE_ROOT_NAME
RESULTS_NAMESPACE = Path("results") / "FIBER_GRAND_Phase2E"
EXPECTED_GITHUB_REPOSITORY = "afazeliuoft/grand_work"
REQUIRED_PHASE2D_R1_COMMIT = "c7b4eed3247382a29c9d794035ef60956c952bfc"
MINIMUM_PYTHON = (3, 10)
MAX_UNCOMPRESSED_PACKAGE_BYTES = 25 * 1024 * 1024


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(temp, path)


class Logger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a", encoding="utf-8", buffering=1)

    def write(self, message: str = "") -> None:
        line = message.rstrip("\n")
        print(line, flush=True)
        self.handle.write(line + "\n")

    def flush(self) -> None:
        self.handle.flush()

    def close(self) -> None:
        try:
            self.handle.flush()
            self.handle.close()
        except Exception:
            pass


def capture(command: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(x) for x in command], cwd=str(cwd) if cwd else None,
        text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


def run_streaming(
    command: Sequence[str], *, logger: Logger, cwd: Path | None = None,
    env: dict[str, str] | None = None, command_log: Path | None = None,
) -> int:
    logger.write(f"$ {shlex.join(str(x) for x in command)}")
    command_handle = None
    try:
        if command_log:
            command_log.parent.mkdir(parents=True, exist_ok=True)
            command_handle = command_log.open("w", encoding="utf-8", buffering=1)
        process = subprocess.Popen(
            [str(x) for x in command], cwd=str(cwd) if cwd else None, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            text = line.rstrip("\n")
            logger.write(text)
            if command_handle:
                command_handle.write(text + "\n")
        rc = process.wait()
        logger.write(f"[command return code] {rc}")
        return rc
    except OSError as exc:
        logger.write(f"[command launch failure] {exc!r}")
        return 127
    finally:
        if command_handle:
            command_handle.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install and run FIBER-GRAND Phase 2E in WSL.")
    p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help=argparse.SUPPRESS)
    p.add_argument("--zip", dest="zip_path", type=Path, default=None, help=argparse.SUPPRESS)
    p.add_argument("--no-push", action="store_true", help="Run locally without Git commit/push.")
    return p.parse_args()


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


def is_ancestor(repo: Path, older: str, newer: str) -> bool:
    return capture(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer]).returncode == 0


def validate_repository(repo_root: Path, logger: Logger, require_network: bool) -> tuple[Path, str, str, Path, str]:
    repo_root = repo_root.expanduser().resolve()
    probe = capture(["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"])
    if probe.returncode:
        raise RuntimeError(f"Not a Git working tree: {repo_root}\n{probe.stderr.strip()}")
    actual = Path(probe.stdout.strip()).resolve()
    if actual != repo_root:
        raise RuntimeError(f"Expected repository root {repo_root}, but Git reports {actual}")

    remote = capture(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
    if remote.returncode:
        raise RuntimeError("Cannot read Git origin")
    remote_url = remote.stdout.strip()
    if normalize_github_remote(remote_url) != EXPECTED_GITHUB_REPOSITORY:
        raise RuntimeError(f"Unexpected origin {remote_url!r}; expected {EXPECTED_GITHUB_REPOSITORY!r}")

    branch_probe = capture(["git", "-C", str(repo_root), "symbolic-ref", "--quiet", "--short", "HEAD"])
    if branch_probe.returncode or not branch_probe.stdout.strip():
        raise RuntimeError("Repository is in detached-HEAD state")
    branch = branch_probe.stdout.strip()
    if branch != "main":
        raise RuntimeError(f"Phase 2E must run on main; current branch is {branch!r}")

    head_probe = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    if head_probe.returncode:
        raise RuntimeError("Cannot resolve local HEAD")
    local_head = head_probe.stdout.strip()
    if not is_ancestor(repo_root, REQUIRED_PHASE2D_R1_COMMIT, local_head):
        raise RuntimeError("Required Phase 2D-R1 PASS commit is not an ancestor of local HEAD")

    if capture(["git", "-C", str(repo_root), "diff", "--quiet"]).returncode != 0:
        raise RuntimeError("Tracked working-tree changes exist; preserve or commit them before Phase 2E")
    if capture(["git", "-C", str(repo_root), "diff", "--cached", "--quiet"]).returncode != 0:
        raise RuntimeError("Staged changes exist; unstage or commit them before Phase 2E")

    git_dir_probe = capture(["git", "-C", str(repo_root), "rev-parse", "--git-dir"])
    if git_dir_probe.returncode:
        raise RuntimeError("Cannot resolve .git directory")
    git_dir = Path(git_dir_probe.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (repo_root / git_dir).resolve()

    if require_network:
        rc = run_streaming(["git", "-C", str(repo_root), "fetch", "origin", "main"], logger=logger)
        if rc:
            raise RuntimeError("Unable to fetch origin/main; no repository changes were made")
        remote_head_probe = capture(["git", "-C", str(repo_root), "rev-parse", "refs/remotes/origin/main"])
        if remote_head_probe.returncode:
            raise RuntimeError("Cannot resolve fetched origin/main")
        remote_head = remote_head_probe.stdout.strip()
        if not is_ancestor(repo_root, remote_head, local_head):
            if is_ancestor(repo_root, local_head, remote_head):
                raise RuntimeError("origin/main is ahead; run `git pull --ff-only` and rerun Phase 2E")
            raise RuntimeError("local main and origin/main have diverged; manual Git review is required")
        logger.write(f"[repo] origin/main={remote_head}; push is fast-forward safe")

    logger.write(f"[repo] root={repo_root}")
    logger.write(f"[repo] origin={remote_url}")
    logger.write(f"[repo] branch={branch}")
    logger.write(f"[repo] local_head={local_head}")
    logger.write(f"[repo] Phase 2D-R1 PASS commit verified: {REQUIRED_PHASE2D_R1_COMMIT}")
    return repo_root, remote_url, branch, git_dir, local_head


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
    logger.write(f"[git] line-ending policy verified at {path}")


def add_local_git_excludes(git_dir: Path, logger: Logger) -> None:
    path = git_dir / "info" / "exclude"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    patterns = [
        ".venv/", ".venv*/", "**/.venv/", "**/.venv*/", "**/__pycache__/", "*.py[cod]",
        ".pytest_cache/", "results/FIBER_GRAND_Phase2E/**/FIBER_GRAND_PHASE2E_RETURN_*.zip",
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
        if str(path) not in seen:
            seen.add(str(path)); out.append(path)
    return out


def locate_package_zip(explicit: Path | None, logger: Logger) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates = [explicit.expanduser().resolve()]
    else:
        for directory in download_directories():
            if directory.is_dir():
                candidates.extend(directory.glob(PACKAGE_ZIP_BASENAME))
                candidates.extend(directory.glob(PACKAGE_ZIP_STEM + "*.zip"))
    unique = {str(p.resolve()): p.resolve() for p in candidates if p.is_file()}
    mismatches: list[str] = []
    for candidate in sorted(unique.values(), key=lambda p: p.stat().st_mtime_ns, reverse=True):
        digest = sha256_file(candidate)
        if digest == PACKAGE_ZIP_SHA256:
            logger.write(f"[package] located={candidate}")
            logger.write(f"[package] sha256={digest} (verified)")
            return candidate
        mismatches.append(f"{candidate}: {digest}")
    raise FileNotFoundError(
        f"Could not find the required package ZIP {PACKAGE_ZIP_BASENAME!r}.\n" +
        ("\n".join(mismatches) if mismatches else "No candidate file was found.")
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


def verify_internal_manifest(package_root: Path) -> None:
    manifest = package_root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        raise RuntimeError("Package has no PACKAGE_MANIFEST.sha256")
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        expected[rel] = digest
    actual = {p.relative_to(package_root).as_posix() for p in package_root.rglob("*") if p.is_file() and p != manifest}
    if actual != set(expected):
        raise RuntimeError(f"Package manifest file-set mismatch: missing={sorted(set(expected)-actual)}, extra={sorted(actual-set(expected))}")
    for rel, digest in expected.items():
        got = sha256_file(package_root / rel)
        if got != digest:
            raise RuntimeError(f"Package manifest mismatch for {rel}: expected {digest}, got {got}")


def install_package(package_zip: Path, repo_root: Path, logger: Logger) -> Path:
    target = repo_root / PACKAGE_RELATIVE_PATH
    with zipfile.ZipFile(package_zip) as zf:
        infos = zf.infolist()
        total = sum(info.file_size for info in infos)
        if total > MAX_UNCOMPRESSED_PACKAGE_BYTES:
            raise RuntimeError("Package exceeds the allowed uncompressed size")
        roots = set()
        for info in infos:
            pure = validate_zip_member(info)
            if pure.parts:
                roots.add(pure.parts[0])
        if roots != {PACKAGE_ROOT_NAME}:
            raise RuntimeError(f"Unexpected package root(s): {sorted(roots)}")
        temp_parent = Path(tempfile.mkdtemp(prefix="fiber_grand_phase2e_install_", dir=str(repo_root)))
        try:
            zf.extractall(temp_parent)
            extracted = temp_parent / PACKAGE_ROOT_NAME
            verify_internal_manifest(extracted)
            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(extracted), str(target))
        finally:
            shutil.rmtree(temp_parent, ignore_errors=True)
    logger.write(f"[package] installed={target}")
    return target


def prepare_venv(logger: Logger) -> Path:
    if sys.version_info < MINIMUM_PYTHON:
        raise RuntimeError(f"Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer is required")
    venv = Path.home() / ".venvs" / "fiber_grand_phase2e_v1_0"
    python = venv / "bin" / "python"
    if not python.is_file():
        venv.parent.mkdir(parents=True, exist_ok=True)
        rc = run_streaming([sys.executable, "-m", "venv", str(venv)], logger=logger)
        if rc:
            raise RuntimeError("Unable to create the Phase 2E virtual environment")
    probe = capture([str(python), "-c", "import sys; print(sys.version_info[:3])"])
    if probe.returncode:
        raise RuntimeError("Unable to execute the Phase 2E virtual environment")
    logger.write(f"[venv] interpreter={python}")
    logger.write(f"[venv] version={probe.stdout.strip()}; no third-party dependencies are required")
    logger.write("[venv] parent-shell activation is unnecessary")
    return python


def next_run_directory(repo_root: Path, stamp: str) -> tuple[Path, str]:
    base = repo_root / RESULTS_NAMESPACE / f"run_{stamp}"
    path = base
    index = 1
    while path.exists():
        path = Path(str(base) + f"_{index}"); index += 1
    path.mkdir(parents=True)
    return path, path.relative_to(repo_root).as_posix()


def path_has_venv(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(part == ".venv" or part.startswith(".venv") for part in parts)


def create_commit_ready_manifest(repo_root: Path, run_dir: Path) -> None:
    manifest = run_dir / "COMMIT_READY_MANIFEST.sha256"
    lines = []
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        if path == manifest or (path.name.startswith("FIBER_GRAND_PHASE2E_RETURN_") and path.suffix == ".zip"):
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def git_commit_and_push(
    repo_root: Path, package_target: Path, run_dir: Path, branch: str,
    wrapper_path: Path, status: str, logger: Logger,
) -> tuple[str | None, bool]:
    run_rel = run_dir.relative_to(repo_root).as_posix()
    latest = repo_root / RESULTS_NAMESPACE / "LATEST.json"
    standalone_info = json.loads((run_dir / "STANDALONE_BUNDLE.json").read_text(encoding="utf-8")) if (run_dir / "STANDALONE_BUNDLE.json").is_file() else {}
    atomic_json(latest, {
        "created_utc": utc_iso(), "result_directory": run_rel, "status": status,
        "decision": "ITW_READY_AFTER_REVIEW_REPAIR" if status == "PASS" else "NOT_AVAILABLE",
        "package_zip_sha256": PACKAGE_ZIP_SHA256,
        "standalone_bundle_sha256": standalone_info.get("sha256"),
    })
    pathspecs = [PACKAGE_RELATIVE_PATH.as_posix(), run_rel, latest.relative_to(repo_root).as_posix(), ".gitattributes"]
    try:
        pathspecs.append(wrapper_path.resolve().relative_to(repo_root).as_posix())
    except ValueError:
        logger.write("[git] wrapper is outside the repository and will not be committed")

    add = capture(["git", "-C", str(repo_root), "add", "--", *pathspecs])
    if add.returncode:
        raise RuntimeError(f"git add failed: {add.stderr.strip()}")
    staged_probe = capture(["git", "-C", str(repo_root), "diff", "--cached", "--name-only", "--", *pathspecs])
    if staged_probe.returncode:
        raise RuntimeError("Cannot inspect staged files")
    staged = [line.strip() for line in staged_probe.stdout.splitlines() if line.strip()]
    forbidden = [p for p in staged if path_has_venv(p) or (Path(p).name.startswith("FIBER_GRAND_PHASE2E_RETURN_") and p.endswith(".zip"))]
    if forbidden:
        raise RuntimeError(f"Safety stop: forbidden paths staged: {forbidden}")
    if not staged:
        head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        return (head.stdout.strip() if head.returncode == 0 else None), False
    logger.write(f"[git] staged {len(staged)} intended files; no .venv or local return ZIP is staged")

    message = f"FIBER-GRAND Phase 2E review adjudication/ITW finalization {status} {run_dir.name}"
    rc = run_streaming(["git", "-C", str(repo_root), "commit", "--only", "-m", message, "--", *pathspecs], logger=logger)
    if rc:
        raise RuntimeError("Git commit failed; results remain locally preserved")
    head = capture(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    if head.returncode:
        raise RuntimeError("Cannot resolve new commit")
    commit = head.stdout.strip()
    names = capture(["git", "-C", str(repo_root), "diff-tree", "--no-commit-id", "--name-only", "-r", commit])
    if any(path_has_venv(line.strip()) for line in names.stdout.splitlines()):
        raise RuntimeError("Committed tree unexpectedly contains a venv path")

    push_rc = run_streaming(["git", "-C", str(repo_root), "push", "-u", "origin", f"{branch}:{branch}"], logger=logger)
    pushed = push_rc == 0
    if pushed:
        logger.write(f"[git] pushed branch={branch} commit={commit}")
    else:
        logger.write(f"[git] push failed; local commit preserved. Retry: git -C {repo_root} push -u origin {branch}:{branch}")
    return commit, pushed


def execute(args: argparse.Namespace, logger: Logger) -> None:
    stamp = utc_stamp()
    repo_root, remote_url, branch, git_dir, local_head = validate_repository(args.repo_root, logger, not args.no_push)
    ensure_gitattributes(repo_root, logger)
    add_local_git_excludes(git_dir, logger)
    package_zip = locate_package_zip(args.zip_path, logger)
    package_target = install_package(package_zip, repo_root, logger)
    venv_python = prepare_venv(logger)

    run_dir, run_rel = next_run_directory(repo_root, stamp)
    logger.write(f"[run] output={run_dir}")
    atomic_json(run_dir / "WRAPPER_METADATA.json", {
        "created_utc": utc_iso(), "wrapper": str(Path(__file__).resolve()),
        "repository_root": str(repo_root), "origin": remote_url, "branch": branch,
        "local_head_before": local_head, "package_zip": str(package_zip),
        "package_zip_sha256": PACKAGE_ZIP_SHA256, "package_installation": str(package_target),
        "venv_python": str(venv_python), "new_simulations_authorized": False,
    })

    env = os.environ.copy()
    env.update({"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"})
    unit_rc = run_streaming(
        [str(venv_python), "-m", "unittest", "discover", "-s", "tests", "-v"],
        logger=logger, cwd=package_target, env=env, command_log=run_dir / "UNIT_TESTS.log",
    )
    if unit_rc:
        scientific_status = "FAIL_UNIT_TESTS"
    else:
        package_rc = run_streaming(
            [str(venv_python), str(package_target / "run_phase2e.py"),
             "--repo-root", str(repo_root),
             "--config", str(package_target / "config" / "phase2e_default.json"),
             "--output", str(run_dir)],
            logger=logger, cwd=package_target, env=env, command_log=run_dir / "PACKAGE_CONSOLE.log",
        )
        package_status = "MISSING"
        if (run_dir / "RUN_STATUS.json").is_file():
            try:
                package_status = json.loads((run_dir / "RUN_STATUS.json").read_text(encoding="utf-8")).get("status", "UNKNOWN")
            except Exception:
                package_status = "UNREADABLE"
        scientific_status = "PASS" if package_rc == 0 and package_status == "PASS" else "FAIL_PACKAGE_RUN"

    standalone_path = None
    standalone_sha = None
    if scientific_status == "PASS" and (run_dir / "STANDALONE_BUNDLE.json").is_file():
        info = json.loads((run_dir / "STANDALONE_BUNDLE.json").read_text(encoding="utf-8"))
        source = Path(info["bundle"])
        standalone_sha = info["sha256"]
        downloads = package_zip.parent
        destination = downloads / source.name
        shutil.copy2(source, destination)
        sidecar_source = source.with_suffix(source.suffix + ".sha256")
        if sidecar_source.is_file():
            shutil.copy2(sidecar_source, destination.with_suffix(destination.suffix + ".sha256"))
        else:
            destination.with_suffix(destination.suffix + ".sha256").write_text(
                f"{standalone_sha}  {destination.name}\n", encoding="utf-8", newline="\n")
        standalone_path = destination
        logger.write(f"[standalone] copied={destination}")
        logger.write(f"[standalone] sha256={standalone_sha}")

    logger.flush()
    shutil.copy2(logger.path, run_dir / "WRAPPER_EXECUTION.log")
    atomic_json(run_dir / "WRAPPER_STATUS.json", {
        "created_utc": utc_iso(), "status": scientific_status,
        "unit_test_returncode": unit_rc, "new_simulations_run": False,
    })
    (run_dir / "RESULT_READY.txt").write_text(
        f"SCIENTIFIC_RUN_STATUS={scientific_status}\n"
        f"RESULT_DIRECTORY={run_rel}\n"
        f"PHASE2E_DECISION={'ITW_READY_AFTER_REVIEW_REPAIR' if scientific_status == 'PASS' else 'NOT_AVAILABLE'}\n"
        "NEW_SIMULATIONS_RUN=false\n",
        encoding="utf-8", newline="\n"
    )
    create_commit_ready_manifest(repo_root, run_dir)

    if args.no_push:
        logger.write("[git] --no-push selected; no commit or push performed")
        commit = None; pushed = False
    else:
        try:
            commit, pushed = git_commit_and_push(repo_root, package_target, run_dir, branch, Path(__file__), scientific_status, logger)
        except Exception as exc:
            commit = None; pushed = False
            logger.write(f"[git] ERROR: {exc!r}")
            logger.write(traceback.format_exc().rstrip())

    logger.write("")
    logger.write("=" * 78)
    logger.write(f"FINAL_SCIENTIFIC_RUN_STATUS={scientific_status}")
    logger.write(f"RESULT_DIRECTORY={run_dir}")
    logger.write(f"GIT_BRANCH={branch}")
    logger.write(f"GIT_COMMIT={commit or 'NOT_CREATED_OR_UNKNOWN'}")
    logger.write(f"GIT_PUSHED={'true' if pushed else 'false'}")
    logger.write(f"PHASE2E_DECISION={'ITW_READY_AFTER_REVIEW_REPAIR' if scientific_status == 'PASS' else 'NOT_AVAILABLE'}")
    logger.write(f"MINIMAL_STANDALONE_BUNDLE={standalone_path or 'NOT_CREATED'}")
    logger.write(f"MINIMAL_STANDALONE_BUNDLE_SHA256={standalone_sha or 'NOT_AVAILABLE'}")
    logger.write("NEW_SIMULATIONS_RUN=false")
    logger.write("Next: human proofreading and venue-template/deadline check; no new simulation campaign.")
    logger.write("The VS Code terminal remains open; this wrapper issued no shell exit command.")
    logger.write("=" * 78)


def main() -> None:
    args = parse_args()
    temp_log = Path(tempfile.gettempdir()) / f"FIBER_GRAND_PHASE2E_WRAPPER_{utc_stamp()}_{os.getpid()}.log"
    logger = Logger(temp_log)
    try:
        logger.write("FIBER-GRAND Paper I - Phase 2E review-adjudication/ITW-finalization wrapper")
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
