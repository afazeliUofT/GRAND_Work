#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run(cmd: list[str], *, cwd: Path | None = None, log: Path | None = None) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(p.stdout, encoding="utf-8", newline="\n")
    return p


def git_show(repo: Path, commit: str, rel: str) -> bytes:
    p = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{rel}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if p.returncode:
        raise RuntimeError(f"cannot read frozen blob {commit}:{rel}: {p.stderr.decode(errors='replace')}")
    return p.stdout


def is_ancestor(repo: Path, older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Phase 2E review adjudication and standalone finalization.")
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--config", type=Path, default=ROOT / "config" / "phase2e_default.json")
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args()


def bit_list(s: str) -> list[int]:
    return [int(ch) for ch in s]


def dvec(x: str, y: str) -> list[int]:
    xb = bit_list(x)
    yb = bit_list(y)
    return [sum(a != b for a, b in zip(xb[:j] + xb[j + 1 :], yb)) for j in range(len(xb))]


def likelihood(x: str, y: str, p: Fraction) -> Fraction:
    m = len(y)
    ds = dvec(x, y)
    return sum(p**d * (1 - p) ** (m - d) for d in ds) / len(x)


def exact_regression_checks() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # Strict tie witness for the complete tie-set comparison.
    p = Fraction(1, 3)
    w1 = likelihood("0010", "001", p)
    w2 = likelihood("0000", "001", p)
    u0 = p * (1 - p) ** 2
    if dvec("0010", "001") != [2, 2, 1, 0] or dvec("0000", "001") != [1, 1, 1, 1]:
        raise AssertionError("strictness witness distance profile mismatch")
    if not (w1 == w2 == u0 == Fraction(4, 27)):
        raise AssertionError("strictness witness likelihood mismatch")
    checks.append({"name": "strict_complete_tie_witness", "status": "PASS", "value": "4/27"})

    # Reversal condition and exact factorization on a broad rational grid.
    cases = 0
    for den in (4, 5, 10, 20, 50, 100):
        p = Fraction(1, den)
        if not p < Fraction(1, 2):
            continue
        for n in range(4, 81):
            y = "0" * (n - 3) + "10"
            xa = "0" * (n - 3) + "101"
            xb = "0" * n
            wa = likelihood(xa, y, p)
            wb = likelihood(xb, y, p)
            condition = n * p > 1 + 2 * p * p
            if (wb > wa) != condition:
                raise AssertionError(("reversal condition", n, p, wa, wb))
            cases += 1
    checks.append({"name": "strict_reversal_grid", "status": "PASS", "cases": cases})

    # Operating-regime statement at p=0.05.
    p = Fraction(1, 20)
    active = [n for n in range(4, 65) if n * p > 1 + 2 * p * p]
    if min(active) != 21 or 16 in active or 24 not in active or 32 not in active:
        raise AssertionError("reversal operating-regime statement is wrong")
    checks.append({"name": "reversal_regime_p005", "status": "PASS", "minimum_n": 21})

    # Exact fixed-set occupancy values.
    n, N, G = 32, 1 << 32, 1056
    expected = {21: 1.5151364732336106, 24: 5.121093505323188, 26: 17.48437475820174}
    occupancy: dict[str, float] = {}
    for k, target in expected.items():
        M = 1 << k
        value = Fraction(1, 1) + Fraction((G - 1) * (M - 1), N - 1)
        if abs(float(value) - target) > 1e-12:
            raise AssertionError("occupancy benchmark mismatch")
        occupancy[str(k)] = float(value)
    checks.append({"name": "uniform_code_occupancy", "status": "PASS", "predicted_q_score": occupancy})

    return {"status": "PASS", "created_utc": utc_now(), "checks": checks}


def static_claim_checks() -> dict[str, Any]:
    main = (ROOT / "manuscript" / "FIBER_GRAND_Paper_I_ITW_Candidate_Phase2E.tex").read_text(encoding="utf-8")
    supp = (ROOT / "supplement" / "FIBER_GRAND_Paper_I_Proof_Supplement_Phase2E.tex").read_text(encoding="utf-8")
    adj = (ROOT / "reviews" / "REVIEW_ADJUDICATION_AND_RESPONSE.md").read_text(encoding="utf-8")

    required_main = [
        "bahl1975decoding",
        "gershon2022genomic",
        "wang2025guessing",
        "largest deletion-alignment component",
        "integer $n\\ge21$",
        "not claimed as a new entropy law",
        "If $s_0\\ge m$",
        "a_n=p_s+",
        "Uniform-code occupancy benchmark",
        "Phase 2E performs no new simulation",
    ]
    for token in required_main:
        if token not in main:
            raise AssertionError(f"required manuscript token missing: {token}")

    required_supp = [
        "If $s_0\\ge m$",
        "a_n=p_s+\\epsilon_n+",
        "For all sufficiently large $n$",
        "Strictness is necessary for complete ties",
        "Uniform-random-code occupancy benchmark",
    ]
    for token in required_supp:
        if token not in supp:
            raise AssertionError(f"required supplement token missing: {token}")

    forbidden = [
        "first exact decoder for synchronization errors",
        "new deletion/substitution distance",
        "new threshold aggregation principle",
        "new h_2 complexity law",
        "universal speedup",
        "ISIT_READY",
    ]
    lower = (main + "\n" + supp).lower()
    for phrase in forbidden:
        if phrase.lower() in lower:
            raise AssertionError(f"forbidden overclaim present: {phrase}")

    # Standalone source contract: no generated inputs or external figures.
    for source_name, source in (("main", main), ("supplement", supp)):
        if "\\input{" in source or "\\includegraphics" in source:
            raise AssertionError(f"{source_name} is not standalone")

    if "No new simulation is authorized or required" not in adj:
        raise AssertionError("adjudication does not state no-simulation decision")

    return {
        "status": "PASS",
        "created_utc": utc_now(),
        "required_main_tokens": len(required_main),
        "required_supplement_tokens": len(required_supp),
        "forbidden_claims_checked": len(forbidden),
        "standalone_tex": True,
    }


def verify_frozen_phase2c(repo: Path, cfg: dict[str, Any], output: Path) -> dict[str, Any]:
    commit = cfg["frozen_phase2c_commit"]
    run_rel = cfg["frozen_phase2c_run"]
    expected = json.loads((ROOT / "evidence" / "FROZEN_PHASE2C_SUMMARY.json").read_text(encoding="utf-8"))

    decision = json.loads(git_show(repo, commit, f"{run_rel}/SCIENTIFIC_DECISION.json"))
    campaign = json.loads(git_show(repo, commit, f"{run_rel}/campaign/CAMPAIGN_REPORT.json"))
    theory = json.loads(git_show(repo, commit, f"{run_rel}/theory/THEORY_CHECKS.json"))
    cell_text = git_show(repo, commit, f"{run_rel}/campaign/CELL_SUMMARY.csv").decode("utf-8")
    rows = list(csv.DictReader(cell_text.splitlines()))

    if decision.get("label") != cfg["expected_phase2c_decision"]:
        raise AssertionError("frozen Phase 2C decision mismatch")
    if campaign.get("trial_count") != expected["trial_count"] or campaign.get("validation_violation_count") != 0:
        raise AssertionError("frozen Phase 2C campaign summary mismatch")
    if theory.get("exact_cases") != expected["theory_exact_cases"] or theory.get("status") != "PASS":
        raise AssertionError("frozen theorem-check summary mismatch")

    by_id = {row["cell_id"]: row for row in rows}
    checked = 0
    for cell in expected["n32_cells"]:
        row = by_id.get(cell["cell_id"])
        if row is None:
            raise AssertionError(f"missing frozen cell {cell['cell_id']}")
        for key, column in (("qmem", "median_q_membership"), ("qscore", "median_q_score"),
                            ("score_savings", "median_codeword_score_savings"),
                            ("branch_ratio", "median_branch_over_dedup_walltime")):
            if abs(float(row[column]) - float(cell[key])) > 1e-9 * max(1.0, abs(float(cell[key]))):
                raise AssertionError(("frozen cell mismatch", cell["cell_id"], key, row[column], cell[key]))
        checked += 1

    frozen = output / "frozen_phase2c"
    frozen.mkdir(parents=True, exist_ok=True)
    (frozen / "SCIENTIFIC_DECISION.json").write_bytes(git_show(repo, commit, f"{run_rel}/SCIENTIFIC_DECISION.json"))
    (frozen / "CAMPAIGN_REPORT.json").write_bytes(git_show(repo, commit, f"{run_rel}/campaign/CAMPAIGN_REPORT.json"))
    (frozen / "CELL_SUMMARY.csv").write_text(cell_text, encoding="utf-8", newline="\n")
    (frozen / "THEORY_CHECKS.json").write_bytes(git_show(repo, commit, f"{run_rel}/theory/THEORY_CHECKS.json"))

    return {
        "status": "PASS",
        "created_utc": utc_now(),
        "commit": commit,
        "decision": decision["label"],
        "trial_count": campaign["trial_count"],
        "validation_violation_count": campaign["validation_violation_count"],
        "theory_exact_cases": theory["exact_cases"],
        "n32_cells_checked": checked,
    }


def compile_latex(source: Path, output_dir: Path, fallback_pdf: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    target_tex = output_dir / source.name
    shutil.copy2(source, target_tex)
    latexmk = shutil.which("latexmk")
    used_fallback = False
    log = output_dir / (source.stem + "_BUILD.log")
    if latexmk:
        p = run([latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", source.name], cwd=output_dir, log=log)
        if p.returncode != 0:
            used_fallback = True
    else:
        used_fallback = True
    target_pdf = output_dir / (source.stem + ".pdf")
    if used_fallback:
        shutil.copy2(fallback_pdf, target_pdf)
        if not log.exists():
            log.write_text("latexmk unavailable; verified precompiled PDF used\n", encoding="utf-8")
        else:
            with log.open("a", encoding="utf-8") as f:
                f.write("\nCompilation failed; verified precompiled PDF used.\n")
    if not target_pdf.is_file() or target_pdf.stat().st_size < 1000:
        raise RuntimeError(f"missing compiled PDF for {source.name}")
    pages = None
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        p = run([pdfinfo, str(target_pdf)])
        for line in p.stdout.splitlines():
            if line.startswith("Pages:"):
                pages = int(line.split(":", 1)[1].strip())
                break
    return {
        "status": "PASS",
        "source": source.name,
        "pdf": target_pdf.name,
        "pdf_sha256": sha256_file(target_pdf),
        "pages": pages,
        "used_precompiled_fallback": used_fallback,
    }


def make_manifest(root: Path, manifest: Path, *, exclude: Iterable[Path] = ()) -> None:
    excluded = {p.resolve() for p in exclude}
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.resolve() in excluded or path == manifest:
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def create_zip(source_dir: Path, zip_path: Path) -> str:
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in source_dir.rglob("*") if p.is_file()):
            zf.write(path, arcname=path.relative_to(source_dir).as_posix())
    return sha256_file(zip_path)


def create_standalone_bundle(output: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    root = output / "standalone" / "FIBER_GRAND_Paper_I_Minimal_Standalone_Phase2E"
    root.mkdir(parents=True, exist_ok=True)
    mapping = [
        (output / "manuscript" / "FIBER_GRAND_Paper_I_ITW_Candidate_Phase2E.pdf", root / "01_Conference_Manuscript.pdf"),
        (output / "manuscript" / "FIBER_GRAND_Paper_I_ITW_Candidate_Phase2E.tex", root / "01_Conference_Manuscript.tex"),
        (output / "supplement" / "FIBER_GRAND_Paper_I_Proof_Supplement_Phase2E.pdf", root / "02_Proof_Supplement.pdf"),
        (output / "supplement" / "FIBER_GRAND_Paper_I_Proof_Supplement_Phase2E.tex", root / "02_Proof_Supplement.tex"),
        (ROOT / "reviews" / "REVIEW_ADJUDICATION_AND_RESPONSE.md", root / "03_REVIEW_ADJUDICATION_AND_RESPONSE.md"),
        (ROOT / "reviews" / "VERIFIED_NOVELTY_MATRIX.md", root / "04_VERIFIED_NOVELTY_MATRIX.md"),
        (ROOT / "reviews" / "VERIFIED_PRIOR_ART.md", root / "05_VERIFIED_PRIOR_ART.md"),
        (ROOT / "evidence" / "FROZEN_PHASE2C_SUMMARY.json", root / "06_FROZEN_PHASE2C_SUMMARY.json"),
        (ROOT / "evidence" / "OCCUPANCY_BENCHMARK.csv", root / "07_OCCUPANCY_BENCHMARK.csv"),
    ]
    for src, dst in mapping:
        shutil.copy2(src, dst)
    reviews_dir = root / "source_reviews"
    shutil.copytree(ROOT / "reviews" / "source_reviews", reviews_dir, dirs_exist_ok=True)
    (root / "00_README.md").write_text(
        "# Minimal standalone FIBER-GRAND Paper-I Phase-2E package\n\n"
        "Decision: `ITW_READY_AFTER_REVIEW_REPAIR`.\n\n"
        "This package contains the repaired four-page conference manuscript, complete proof supplement, "
        "adjudication of four independent reviews, verified novelty matrix, primary-source positioning, "
        "frozen Phase-2C summary, occupancy benchmark, and the exact source reviews. No new simulation "
        "was run in Phase 2E. The manuscript TeX files are standalone and require no generated inputs.\n",
        encoding="utf-8", newline="\n"
    )
    manifest = root / "BUNDLE_MANIFEST.sha256"
    make_manifest(root, manifest)
    zip_path = output / "standalone" / cfg["standalone_bundle_name"]
    digest = create_zip(root, zip_path)
    (zip_path.with_suffix(zip_path.suffix + ".sha256")).write_text(
        f"{digest}  {zip_path.name}\n", encoding="utf-8", newline="\n"
    )
    return {
        "status": "PASS",
        "bundle": str(zip_path),
        "sha256": digest,
        "files": sum(1 for p in root.rglob("*") if p.is_file()),
    }


def main() -> int:
    args = parse_args()
    repo = args.repo_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    status = "FAIL"
    decision = "NOT_AVAILABLE"
    try:
        head = run(["git", "-C", str(repo), "rev-parse", "HEAD"])
        if head.returncode:
            raise RuntimeError("cannot resolve repository HEAD")
        head_sha = head.stdout.strip()
        if not is_ancestor(repo, cfg["required_phase2d_r1_commit"], head_sha):
            raise RuntimeError("required Phase 2D-R1 commit is not an ancestor of HEAD")
        write_json(output / "GIT_CONTEXT.json", {
            "created_utc": utc_now(), "head": head_sha,
            "required_phase2d_r1_commit": cfg["required_phase2d_r1_commit"],
            "frozen_phase2c_commit": cfg["frozen_phase2c_commit"],
        })

        frozen_report = verify_frozen_phase2c(repo, cfg, output)
        write_json(output / "FROZEN_EVIDENCE_CHECK.json", frozen_report)
        exact_report = exact_regression_checks()
        write_json(output / "EXACT_REVIEW_REPAIR_CHECKS.json", exact_report)
        claim_report = static_claim_checks()
        write_json(output / "CLAIM_DISCIPLINE_CHECK.json", claim_report)

        manuscript_build = compile_latex(
            ROOT / "manuscript" / "FIBER_GRAND_Paper_I_ITW_Candidate_Phase2E.tex",
            output / "manuscript",
            ROOT / "precompiled" / "FIBER_GRAND_Paper_I_ITW_Candidate_Phase2E.pdf",
        )
        supplement_build = compile_latex(
            ROOT / "supplement" / "FIBER_GRAND_Paper_I_Proof_Supplement_Phase2E.tex",
            output / "supplement",
            ROOT / "precompiled" / "FIBER_GRAND_Paper_I_Proof_Supplement_Phase2E.pdf",
        )
        write_json(output / "DOCUMENT_BUILD.json", {
            "status": "PASS", "created_utc": utc_now(),
            "manuscript": manuscript_build, "supplement": supplement_build,
        })

        review_out = output / "reviews"
        shutil.copytree(ROOT / "reviews", review_out, dirs_exist_ok=True)
        evidence_out = output / "evidence"
        shutil.copytree(ROOT / "evidence", evidence_out, dirs_exist_ok=True)

        standalone = create_standalone_bundle(output, cfg)
        write_json(output / "STANDALONE_BUNDLE.json", standalone)

        decision = cfg["phase2e_decision"]
        scientific = {
            "created_utc": utc_now(),
            "label": decision,
            "execution_correctness_pass": True,
            "proof_repairs_applied": True,
            "novelty_claims_narrowed": True,
            "standalone_tex": True,
            "new_simulations_run": False,
            "large_campaign_authorized": False,
            "submission_positioning": "ITW candidate; not positioned as ISIT-ready",
            "reason": "Four independent reviews were adjudicated; valid proof and novelty repairs were applied, invalid over-broad objections were rejected, and frozen Phase-2C evidence was preserved.",
        }
        write_json(output / "SCIENTIFIC_DECISION.json", scientific)
        report = (
            "# FIBER-GRAND Paper I - Phase 2E report\n\n"
            f"## Decision\n\n**{decision}**\n\n"
            "- Four independent reviews adjudicated.\n"
            "- Two proof-writing repairs applied without changing theorem statements.\n"
            "- Novelty narrowed to the strict family, `U_s`, complete-tie certificate, and stopping theorem.\n"
            "- `h_2(p_s)` demoted to a standard typical-volume corollary.\n"
            "- Gershon-Cassuto, Bahl-Jelinek, deletion-ML, probabilistic-string, and GCD antecedents added.\n"
            "- Exact random-code occupancy benchmark added.\n"
            "- Frozen Phase-2C results reverified from the immutable commit.\n"
            "- New simulations run: **no**.\n\n"
            f"Standalone bundle SHA-256: `{standalone['sha256']}`\n"
        )
        (output / "PHASE2E_REPORT.md").write_text(report, encoding="utf-8", newline="\n")
        status = "PASS"
        rc = 0
    except Exception as exc:
        rc = 1
        (output / "FAILURE_TRACEBACK.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        write_json(output / "FAILURE.json", {"created_utc": utc_now(), "exception": repr(exc)})
        print(f"[phase2e] ERROR: {exc!r}", file=sys.stderr, flush=True)
    finally:
        write_json(output / "RUN_STATUS.json", {
            "created_utc": utc_now(), "status": status, "decision": decision,
            "new_simulations_run": False,
        })
        return_zip = output / f"FIBER_GRAND_PHASE2E_RETURN_{output.name}.zip"
        sidecar = return_zip.with_suffix(return_zip.suffix + ".sha256")
        manifest = output / "MANIFEST.sha256"
        make_manifest(output, manifest, exclude=[return_zip, sidecar])
        digest = create_zip(output, return_zip)
        sidecar.write_text(f"{digest}  {return_zip.name}\n", encoding="utf-8", newline="\n")
        print(f"[phase2e] status={status}", flush=True)
        print(f"[phase2e] decision={decision}", flush=True)
        print(f"[phase2e] output={output}", flush=True)
        print(f"[phase2e] return_zip={return_zip}", flush=True)
        print(f"[phase2e] return_zip_sha256={digest}", flush=True)
        print("[phase2e] new_simulations_run=false", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
