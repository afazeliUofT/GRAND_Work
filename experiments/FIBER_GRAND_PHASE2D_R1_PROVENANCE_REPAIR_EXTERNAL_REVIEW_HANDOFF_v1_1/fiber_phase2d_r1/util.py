from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git_blob(repo: Path, commit: str, relative: str) -> bytes:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe Git path: {relative!r}")
    probe = run(["git", "-C", str(repo), "show", f"{commit}:{relative}"])
    if probe.returncode != 0:
        raise RuntimeError(
            f"cannot read committed blob {commit}:{relative}: "
            f"{probe.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return probe.stdout


def git_text(repo: Path, commit: str, relative: str) -> str:
    return git_blob(repo, commit, relative).decode("utf-8")


def git_files(repo: Path, commit: str, prefix: str) -> list[str]:
    probe = run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit, "--", prefix])
    if probe.returncode != 0:
        raise RuntimeError(probe.stderr.decode("utf-8", errors="replace").strip())
    return [line for line in probe.stdout.decode("utf-8").splitlines() if line]


def parse_manifest_bytes(data: bytes) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in data.decode("utf-8").splitlines():
        if not raw.strip():
            continue
        digest, relative = raw.split("  ", 1)
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeError(f"unsafe manifest path: {relative!r}")
        if relative in entries:
            raise RuntimeError(f"duplicate manifest path: {relative!r}")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise RuntimeError(f"invalid SHA-256 digest for {relative!r}")
        entries[relative] = digest
    return entries


def write_manifest_for_files(root: Path, paths: Iterable[Path], destination: Path) -> None:
    lines: list[str] = []
    for path in sorted({p.resolve() for p in paths}):
        if not path.is_file() or path == destination.resolve():
            continue
        relative = path.relative_to(root.resolve()).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_tree_manifest(root: Path, destination: Path, *, exclude: Iterable[Path] = ()) -> None:
    excluded = {p.resolve() for p in exclude}
    paths = [
        p for p in root.rglob("*")
        if p.is_file() and p.resolve() not in excluded and p.resolve() != destination.resolve()
    ]
    write_manifest_for_files(root, paths, destination)


def create_zip_from_directory(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            if path == destination:
                continue
            archive.write(path, arcname=path.relative_to(source).as_posix())
    return sha256_file(destination)


def copy_blob(repo: Path, commit: str, source_relative: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(git_blob(repo, commit, source_relative))
