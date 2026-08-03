from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fiber_phase2b.artifact_repair import (
    classify_expected_console_append,
    repair_phase2a_manifest,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ConsoleAppendClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prefix = (
            b"[validation] exact checks: PASS\n"
            b"[pilot] completed 214/214 paired trials\n"
            b"[pilot] running alignment-bound structural scan\n"
        )
        self.output = "/home/afazeli2006/GRAND_Work/results/FIBER_GRAND_Phase2A/run_test"
        self.zip_path = self.output + "/FIBER_GRAND_PHASE2A_RETURN_run_test.zip"
        self.digest = "a" * 64
        self.suffix = (
            "[phase2a] status=PASS\n"
            f"[phase2a] output={self.output}\n"
            f"[phase2a] return_zip={self.zip_path}\n"
            f"[phase2a] return_zip_sha256={self.digest}\n"
        ).encode()

    def classify(self, blob: bytes, **overrides: str):
        kwargs = {
            "committed_blob": blob,
            "original_manifest_sha256": _sha(self.prefix),
            "expected_prefix_terminal_line": "[pilot] running alignment-bound structural scan",
            "expected_status": "PASS",
            "expected_output_path": self.output,
            "expected_zip_path": self.zip_path,
            "expected_zip_sha256": self.digest,
        }
        kwargs.update(overrides)
        return classify_expected_console_append(**kwargs)

    def test_accepts_only_exact_four_line_append(self) -> None:
        result = self.classify(self.prefix + self.suffix)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["diagnosis"], "EXPECTED_POST_MANIFEST_CONSOLE_APPEND")
        self.assertEqual(result["appended_line_count"], 4)

    def test_rejects_extra_appended_line(self) -> None:
        self.assertIsNone(self.classify(self.prefix + self.suffix + b"EXTRA\n"))

    def test_rejects_wrong_sidecar_digest(self) -> None:
        self.assertIsNone(
            self.classify(self.prefix + self.suffix, expected_zip_sha256="b" * 64)
        )

    def test_rejects_non_line_boundary_prefix(self) -> None:
        wrong = _sha(self.prefix[:-1])
        self.assertIsNone(
            classify_expected_console_append(
                committed_blob=self.prefix + self.suffix,
                original_manifest_sha256=wrong,
                expected_prefix_terminal_line="[pilot] running alignment-bound structural scan",
                expected_status="PASS",
                expected_output_path=self.output,
                expected_zip_path=self.zip_path,
                expected_zip_sha256=self.digest,
            )
        )


class FrozenManifestRepairTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> str:
        process = subprocess.run(
            ["git", "-C", str(repo), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if process.returncode:
            raise AssertionError(process.stderr)
        return process.stdout.strip()

    def _build_repo(self, root: Path) -> tuple[Path, str, str, dict[str, object]]:
        repo = root / "repo"
        repo.mkdir()
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "test@example.invalid")
        self._git(repo, "config", "user.name", "Phase2B R1 Test")

        run_rel = "results/FIBER_GRAND_Phase2A/run_test"
        run_dir = repo / run_rel
        (run_dir / "pilot").mkdir(parents=True)
        (run_dir / "validation").mkdir(parents=True)

        expected_csv = [
            "pilot/bound_scan.csv",
            "pilot/cell_summary.csv",
            "pilot/paired_trials.csv",
            "pilot/schedule_summary.csv",
            "pilot/stress_summary.csv",
        ]
        manifest_hashes: dict[str, str] = {}
        for index, relative in enumerate(expected_csv):
            lf = f"a,b\n{index},{index + 1}\n".encode()
            (run_dir / relative).write_bytes(lf)
            manifest_hashes[relative] = _sha(lf.replace(b"\n", b"\r\n"))

        prefix = (
            b"[validation] exact checks: PASS\n"
            b"[pilot] completed 214/214 paired trials\n"
            b"[pilot] running alignment-bound structural scan\n"
        )
        zip_name = "FIBER_GRAND_PHASE2A_RETURN_run_test.zip"
        zip_digest = "c" * 64
        output_path = str(run_dir.resolve())
        zip_path = str((run_dir / zip_name).resolve())
        suffix = (
            "[phase2a] status=PASS\n"
            f"[phase2a] output={output_path}\n"
            f"[phase2a] return_zip={zip_path}\n"
            f"[phase2a] return_zip_sha256={zip_digest}\n"
        ).encode()
        (run_dir / "PACKAGE_CONSOLE.log").write_bytes(prefix + suffix)
        manifest_hashes["PACKAGE_CONSOLE.log"] = _sha(prefix)

        status_files = {
            "RUN_STATUS.json": {"status": "PASS"},
            "validation/exact_validation_summary.json": {"status": "PASS"},
            "pilot/pilot_summary.json": {
                "status": "PASS",
                "disagreements": 0,
                "exhaustive_ml_failures": 0,
            },
        }
        for relative, payload in status_files.items():
            data = (json.dumps(payload, sort_keys=True) + "\n").encode()
            (run_dir / relative).write_bytes(data)
            manifest_hashes[relative] = _sha(data)

        unchanged = b"frozen numerical evidence\n"
        (run_dir / "PHASE2A_REPORT.json").write_bytes(unchanged)
        manifest_hashes["PHASE2A_REPORT.json"] = _sha(unchanged)

        manifest_lines = [
            f"{digest}  {relative}" for relative, digest in sorted(manifest_hashes.items())
        ]
        (run_dir / "MANIFEST.sha256").write_text(
            "\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n"
        )
        (run_dir / f"{zip_name}.sha256").write_text(
            f"{zip_digest}  {zip_name}\n", encoding="utf-8", newline="\n"
        )

        self._git(repo, "add", ".")
        self._git(repo, "commit", "-q", "-m", "frozen Phase 2A")
        commit = self._git(repo, "rev-parse", "HEAD")
        policy = {
            "expected_crlf_paths": expected_csv,
            "expected_post_manifest_append_path": "PACKAGE_CONSOLE.log",
            "expected_console_prefix_terminal_line": (
                "[pilot] running alignment-bound structural scan"
            ),
            "require_clean_worktree_copy": True,
            "frozen_replay_export_paths": [
                "pilot/bound_scan.csv",
                "pilot/paired_trials.csv",
            ],
        }
        return repo, commit, run_rel, policy

    def test_full_repair_passes_only_frozen_transformations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit, run_rel, policy = self._build_repo(root)
            report = repair_phase2a_manifest(
                repo, commit, run_rel, root / "out", policy
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["crlf_normalization_count"], 5)
            self.assertEqual(report["expected_post_manifest_console_append_count"], 1)
            self.assertEqual(report["unexplained_mismatch_count"], 0)
            self.assertEqual(report["worktree_mismatch_count"], 0)
            self.assertEqual(report["frozen_replay_export_paths"], [
                "pilot/bound_scan.csv",
                "pilot/paired_trials.csv",
            ])
            self.assertTrue((root / "out/FROZEN_REPLAY_INPUTS/pilot/bound_scan.csv").is_file())
            self.assertTrue((root / "out/FROZEN_REPLAY_INPUTS/pilot/paired_trials.csv").is_file())

    def test_full_repair_rejects_modified_replay_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit, run_rel, policy = self._build_repo(root)
            (repo / run_rel / "pilot/paired_trials.csv").write_text(
                "tampered\n", encoding="utf-8", newline="\n"
            )
            report = repair_phase2a_manifest(
                repo, commit, run_rel, root / "out", policy
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertGreater(report["worktree_mismatch_count"], 0)


if __name__ == "__main__":
    unittest.main()
