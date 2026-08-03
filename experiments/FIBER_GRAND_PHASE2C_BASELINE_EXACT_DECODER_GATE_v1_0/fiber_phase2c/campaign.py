from __future__ import annotations

import csv
import math
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from .theory import generated_attempt_cap
from .trials import TrialSpec, build_trial_specs, write_trial_inputs
from .util import median, percentile_nearest_rank, read_csv, utc_now_iso, write_csv, write_json


_TRUE = {"1", "true", "True", "TRUE"}


def _b(value: Any) -> bool:
    return str(value) in _TRUE


def _i(value: Any) -> int:
    text = str(value).strip()
    return int(text) if text else 0


def _f(value: Any) -> float:
    text = str(value).strip()
    return float(text) if text else float("nan")


def _ratio(num: float | int, den: float | int) -> float:
    return float(num) / float(den) if float(den) > 0 else float("inf")


def _log2_ratio(num: float | int, den: float | int) -> float:
    if float(num) <= 0 or float(den) <= 0:
        return float("nan")
    return math.log2(float(num) / float(den))


def _ties(value: Any) -> tuple[str, ...]:
    text = str(value).strip()
    if not text:
        return ()
    return tuple(sorted(x for x in text.split(",") if x))


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _run_batch(binary: Path, input_path: Path, output_path: Path, log_path: Path) -> dict[str, Any]:
    started = time.perf_counter_ns()
    process = subprocess.run(
        [str(binary), "batch", str(input_path), str(output_path)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = time.perf_counter_ns() - started
    log_path.write_text(
        "$ " + " ".join([str(binary), "batch", str(input_path), str(output_path)]) + "\n"
        + process.stdout,
        encoding="utf-8",
        newline="\n",
    )
    if process.returncode != 0:
        raise RuntimeError(f"compiled Phase-2C batch failed with return code {process.returncode}; see {log_path}")
    return {"returncode": process.returncode, "elapsed_ns": elapsed, "output": str(output_path)}


def _same_exact_signature(row: dict[str, str], left: str, right: str) -> bool:
    return (
        row[f"{left}_score"] == row[f"{right}_score"]
        and _ties(row[f"{left}_ties"]) == _ties(row[f"{right}_ties"])
        and row[f"{left}_decoded"] == row[f"{right}_decoded"]
    )


def _validate_and_merge(specs: Sequence[TrialSpec], cpp_rows: Sequence[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {int(row["trial_id"]): row for row in cpp_rows}
    if len(by_id) != len(cpp_rows):
        raise RuntimeError("duplicate trial IDs in compiled output")
    if set(by_id) != {spec.trial_id for spec in specs}:
        raise RuntimeError("compiled output trial-ID set differs from preregistered input")

    merged: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    def record(spec: TrialSpec, category: str, detail: str) -> None:
        violations.append({"trial_id": spec.trial_id, "cell_id": spec.cell_id, "category": category, "detail": detail})

    for spec in specs:
        raw = by_id[spec.trial_id]
        dedup_complete = _b(raw["dedup_complete"])
        history_complete = _b(raw["history_complete"])
        exhaustive_complete = _b(raw["exhaustive_complete"])
        branch_complete = _b(raw["branch_complete"])

        if dedup_complete and history_complete:
            if not _same_exact_signature(raw, "dedup", "history"):
                record(spec, "DECODER_DISAGREEMENT", "deduplicated and history-pair exact decoders returned different ML signatures")
            for metric in ("stop_shell", "q_disc", "q_membership", "q_score"):
                if raw[f"dedup_{metric}"] != raw[f"history_{metric}"]:
                    record(spec, "DECODER_WORK_INVARIANT", f"dedup/history {metric} mismatch")
        if exhaustive_complete and dedup_complete and not _same_exact_signature(raw, "dedup", "exhaustive"):
            record(spec, "EXHAUSTIVE_DISAGREEMENT", "deduplicated decoder disagrees with exhaustive codeword ML")
        if branch_complete and dedup_complete and not _same_exact_signature(raw, "dedup", "branch"):
            record(spec, "BRANCH_DISAGREEMENT", "deduplicated decoder disagrees with complete branch-and-bound ML")

        dedup_stop = _i(raw["dedup_stop_shell"])
        if dedup_complete and dedup_stop > spec.theorem_stop_shell_cap:
            record(
                spec,
                "THEOREM_CAP_VIOLATION",
                f"observed stop shell {dedup_stop} exceeds realization cap {spec.theorem_stop_shell_cap}",
            )
        if dedup_complete:
            expected_attempts = generated_attempt_cap(spec.n, dedup_stop, True)
            if _i(raw["dedup_generated_attempts"]) != expected_attempts:
                record(spec, "DEDUP_ENUMERATION_COUNT", f"got {_i(raw['dedup_generated_attempts'])}, expected {expected_attempts}")
        if history_complete:
            expected_attempts = generated_attempt_cap(spec.n, _i(raw["history_stop_shell"]), False)
            if _i(raw["history_generated_attempts"]) != expected_attempts:
                record(spec, "HISTORY_ENUMERATION_COUNT", f"got {_i(raw['history_generated_attempts'])}, expected {expected_attempts}")
        if _i(raw["dedup_q_disc"]) != _i(raw["dedup_q_membership"]):
            record(spec, "MEMBERSHIP_ACCOUNTING", "one membership query was not recorded per distinct candidate")
        if _i(raw["dedup_q_score"]) > _i(raw["dedup_q_membership"]):
            record(spec, "SCORING_ACCOUNTING", "complete likelihood evaluations exceed membership queries")

        code_size = 1 << spec.k
        q_score = _i(raw["dedup_q_score"])
        q_mem = _i(raw["dedup_q_membership"])
        q_disc = _i(raw["dedup_q_disc"])
        dedup_ns = _i(raw["dedup_total_ns"])
        history_ns = _i(raw["history_total_ns"])
        exhaustive_ns = _i(raw["exhaustive_total_ns"])
        branch_ns = _i(raw["branch_total_ns"])
        bestpath_decoded = raw["bestpath_decoded"].strip()
        tx_hex = hex(spec.transmitted_word)

        row: dict[str, Any] = spec.metadata_row()
        row.update(raw)
        row.update(
            {
                "dedup_complete_bool": dedup_complete,
                "history_complete_bool": history_complete,
                "exhaustive_complete_bool": exhaustive_complete,
                "branch_complete_bool": branch_complete,
                "codeword_score_savings": _ratio(code_size, q_score) if q_score else float("inf"),
                "codebook_membership_ratio": _ratio(code_size, q_mem) if q_mem else float("inf"),
                "membership_query_exponent": math.log2(max(1, q_mem)) / spec.n,
                "score_query_exponent": math.log2(max(1, q_score)) / spec.n,
                "rate_minus_membership_exponent": (spec.k / spec.n) - math.log2(max(1, q_mem)) / spec.n,
                "rate_minus_score_exponent": (spec.k / spec.n) - math.log2(max(1, q_score)) / spec.n,
                "history_over_dedup_generated": _ratio(_i(raw["history_generated_attempts"]), _i(raw["dedup_generated_attempts"])),
                "history_over_dedup_walltime": _ratio(history_ns, dedup_ns),
                "exhaustive_over_dedup_walltime": _ratio(exhaustive_ns, dedup_ns) if exhaustive_complete else "",
                "branch_over_dedup_walltime": _ratio(branch_ns, dedup_ns) if branch_complete else "",
                "theorem_stop_shell_slack": spec.theorem_stop_shell_cap - dedup_stop if dedup_complete else "",
                "bestpath_ml_selected_disagreement_bool": _b(raw["bestpath_selected_disagreement"]),
                "bestpath_ml_strict_disjoint_bool": _b(raw["bestpath_strict_disjoint"]),
                "bestpath_error_bool": bool(bestpath_decoded and bestpath_decoded != tx_hex),
                "dedup_ml_error_bool": _b(raw["dedup_ml_error"]),
                "distinct_candidate_fraction_of_codebook": q_disc / code_size,
            }
        )
        merged.append(row)
    return merged, violations


def _numeric(rows: Sequence[dict[str, Any]], key: str, predicate=lambda _r: True) -> list[float]:
    out: list[float] = []
    for row in rows:
        if not predicate(row):
            continue
        value = row.get(key, "")
        if value == "" or value is None:
            continue
        number = float(value)
        if math.isfinite(number):
            out.append(number)
    return out


def _summarize_group(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    natural = [r for r in rows if r["trial_kind"] == "natural"]
    complete = [r for r in natural if r["dedup_complete_bool"]]
    paired = [r for r in complete if r["history_complete_bool"]]
    exhaustive = [r for r in complete if r["exhaustive_complete_bool"]]
    branch = [r for r in complete if r["branch_complete_bool"]]
    score_savings = _numeric(complete, "codeword_score_savings")
    membership = _numeric(complete, "codebook_membership_ratio")
    history_speed = _numeric(paired, "history_over_dedup_walltime")
    history_work = _numeric(paired, "history_over_dedup_generated")
    exhaustive_speed = _numeric(exhaustive, "exhaustive_over_dedup_walltime")
    branch_speed = _numeric(branch, "branch_over_dedup_walltime")

    def med(values: Sequence[float]) -> float | str:
        return median(values) if values else ""

    def pct(values: Sequence[float], q: float, minimum: int = 1) -> float | str:
        return percentile_nearest_rank(values, q) if len(values) >= minimum else ""

    first = rows[0]
    return {
        "cell_id": first["cell_id"],
        "n": first["n"],
        "k": first["k"],
        "rate": first["rate"],
        "family": first["family"],
        "rate_label": first["rate_label"],
        "natural_trials": len(natural),
        "dedup_complete": len(complete),
        "dedup_censored": len(natural) - len(complete),
        "dedup_censor_fraction": (len(natural) - len(complete)) / len(natural) if natural else 0.0,
        "history_paired_complete": len(paired),
        "exhaustive_complete": len(exhaustive),
        "branch_complete": len(branch),
        "median_q_membership": med(_numeric(complete, "dedup_q_membership")),
        "p90_q_membership": pct(_numeric(complete, "dedup_q_membership"), 0.90),
        "median_q_score": med(_numeric(complete, "dedup_q_score")),
        "p90_q_score": pct(_numeric(complete, "dedup_q_score"), 0.90),
        "median_codeword_score_savings": med(score_savings),
        "p10_codeword_score_savings": pct(score_savings, 0.10),
        "p90_codeword_score_savings": pct(score_savings, 0.90),
        "median_codebook_membership_ratio": med(membership),
        "p10_codebook_membership_ratio": pct(membership, 0.10),
        "median_membership_query_exponent": med(_numeric(complete, "membership_query_exponent")),
        "median_rate_minus_membership_exponent": med(_numeric(complete, "rate_minus_membership_exponent")),
        "median_rate_minus_score_exponent": med(_numeric(complete, "rate_minus_score_exponent")),
        "median_stop_shell": med(_numeric(complete, "dedup_stop_shell")),
        "p90_stop_shell": pct(_numeric(complete, "dedup_stop_shell"), 0.90),
        "median_theorem_cap_slack": med(_numeric(complete, "theorem_stop_shell_slack")),
        "median_history_over_dedup_generated": med(history_work),
        "median_history_over_dedup_walltime": med(history_speed),
        "median_exhaustive_over_dedup_walltime": med(exhaustive_speed),
        "minimum_exhaustive_over_dedup_walltime": min(exhaustive_speed) if exhaustive_speed else "",
        "median_branch_over_dedup_walltime": med(branch_speed),
        "bestpath_selected_disagreement_count": sum(bool(r["bestpath_ml_selected_disagreement_bool"]) for r in complete),
        "bestpath_selected_disagreement_fraction": sum(bool(r["bestpath_ml_selected_disagreement_bool"]) for r in complete) / len(complete) if complete else "",
        "bestpath_strict_disjoint_count": sum(bool(r["bestpath_ml_strict_disjoint_bool"]) for r in complete),
        "bestpath_strict_disjoint_fraction": sum(bool(r["bestpath_ml_strict_disjoint_bool"]) for r in complete) / len(complete) if complete else "",
        "ml_error_count": sum(bool(r["dedup_ml_error_bool"]) for r in complete),
        "ml_error_rate": sum(bool(r["dedup_ml_error_bool"]) for r in complete) / len(complete) if complete else "",
        "bestpath_error_count": sum(bool(r["bestpath_error_bool"]) for r in complete),
        "bestpath_error_rate": sum(bool(r["bestpath_error_bool"]) for r in complete) / len(complete) if complete else "",
    }


def summarize_cells(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["cell_id"])].append(row)
    return [_summarize_group(groups[key]) for key in sorted(groups)]


def summarize_stress(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["trial_kind"] == "stress":
            groups[(str(row["cell_id"]), int(row["observed_error_weight"]))].append(row)
    out: list[dict[str, Any]] = []
    for (cell, weight), group in sorted(groups.items()):
        complete = [r for r in group if r["dedup_complete_bool"]]
        first = group[0]
        out.append(
            {
                "cell_id": cell,
                "n": first["n"],
                "k": first["k"],
                "family": first["family"],
                "observed_error_weight": weight,
                "trials": len(group),
                "dedup_complete": len(complete),
                "history_complete": sum(bool(r["history_complete_bool"]) for r in group),
                "median_q_membership": median(_numeric(complete, "dedup_q_membership")) if complete else "",
                "median_q_score": median(_numeric(complete, "dedup_q_score")) if complete else "",
                "median_score_savings": median(_numeric(complete, "codeword_score_savings")) if complete else "",
                "median_stop_shell": median(_numeric(complete, "dedup_stop_shell")) if complete else "",
                "median_theorem_cap_slack": median(_numeric(complete, "theorem_stop_shell_slack")) if complete else "",
                "bestpath_selected_disagreement_count": sum(bool(r["bestpath_ml_selected_disagreement_bool"]) for r in complete),
            }
        )
    return out


def _decision(config: dict[str, Any], rows: Sequence[dict[str, Any]], cells: Sequence[dict[str, Any]], violations: Sequence[dict[str, Any]]) -> dict[str, Any]:
    gate = config["decision_gate"]
    natural = [r for r in rows if r["trial_kind"] == "natural"]
    exact_failures = [v for v in violations if v["category"] in {
        "DECODER_DISAGREEMENT", "EXHAUSTIVE_DISAGREEMENT", "BRANCH_DISAGREEMENT",
        "THEOREM_CAP_VIOLATION", "DEDUP_ENUMERATION_COUNT", "HISTORY_ENUMERATION_COUNT",
        "MEMBERSHIP_ACCOUNTING", "SCORING_ACCOUNTING",
    }]
    censor_fraction = sum(not bool(r["dedup_complete_bool"]) for r in natural) / len(natural) if natural else 1.0

    n32 = [c for c in cells if int(c["n"]) == 32]
    query_cells = [
        c for c in n32
        if c["median_codeword_score_savings"] != ""
        and float(c["median_codeword_score_savings"]) >= float(gate["median_exact_score_savings"])
        and float(c["p10_codeword_score_savings"]) >= float(gate["p10_exact_score_savings"])
        and float(c["median_codebook_membership_ratio"]) >= float(gate["median_membership_ratio"])
    ]
    dedup_speed_cells = [
        c for c in n32
        if c["median_history_over_dedup_walltime"] != ""
        and float(c["median_history_over_dedup_walltime"]) >= float(gate["median_history_over_dedup_walltime"])
    ]
    n32_exhaustive = _numeric(
        [r for r in natural if int(r["n"]) == 32 and r["exhaustive_complete_bool"]],
        "exhaustive_over_dedup_walltime",
    )
    n24plus_branch = _numeric(
        [r for r in natural if int(r["n"]) >= 24 and r["branch_complete_bool"]],
        "branch_over_dedup_walltime",
    )
    query_pass = len(query_cells) >= int(gate["n32_min_cells"])
    censor_pass = censor_fraction <= float(gate["max_natural_censor_fraction"])
    exhaustive_pass = bool(n32_exhaustive) and median(n32_exhaustive) >= float(gate["min_n32_exhaustive_speedup"])
    generation_pass = len(dedup_speed_cells) >= int(gate["n32_min_cells"])
    branch_context = {
        "complete_n24plus_cases": len(n24plus_branch),
        "median_branch_over_dedup_walltime": median(n24plus_branch) if n24plus_branch else "",
        "dedup_faster_fraction": sum(v >= 1.0 for v in n24plus_branch) / len(n24plus_branch) if n24plus_branch else "",
    }

    if exact_failures:
        label = "STOP_CORRECTNESS_FAILURE"
        reason = "At least one exact-decoder, exact-baseline, theorem-cap, or accounting invariant failed."
    elif not censor_pass:
        label = "NARROW_COMPLEXITY_TAIL_UNRESOLVED"
        reason = "The exact decoder is correct on completed cases, but the preregistered natural-channel completion gate failed."
    elif query_pass and exhaustive_pass:
        label = "GO_PAPER_I_BASELINE_EXACT_DECODER"
        reason = "The baseline exact decoder passed correctness and demonstrated large, repeated codeword-likelihood savings together with a material exact-exhaustive wall-clock advantage."
    elif query_pass:
        label = "NARROW_TO_THEOREM_AND_QUERY_COMPLEXITY"
        reason = "The exact membership-oracle/query-complexity evidence is strong, but end-to-end advantage over the exact exhaustive baseline is not yet established."
    else:
        label = "STOP_BASELINE_DECODER_ROUTE"
        reason = "The preregistered n=32 codeword-scoring and membership-query savings were not repeated across enough code/rate cells."

    return {
        "created_utc": utc_now_iso(),
        "label": label,
        "reason": reason,
        "execution_correctness_pass": not exact_failures,
        "query_complexity_gate_pass": query_pass,
        "exact_exhaustive_speed_gate_pass": exhaustive_pass,
        "deduplicated_generation_speed_gate_pass": generation_pass,
        "natural_censor_gate_pass": censor_pass,
        "natural_censor_fraction": censor_fraction,
        "n32_query_cells_passed": [c["cell_id"] for c in query_cells],
        "n32_dedup_speed_cells_passed": [c["cell_id"] for c in dedup_speed_cells],
        "n32_exhaustive_calibration_cases": len(n32_exhaustive),
        "median_n32_exhaustive_over_dedup_walltime": median(n32_exhaustive) if n32_exhaustive else "",
        "branch_baseline_context": branch_context,
        "bestpath_selected_disagreements": sum(bool(r["bestpath_ml_selected_disagreement_bool"]) for r in natural if r["dedup_complete_bool"]),
        "bestpath_strict_disjoint_cases": sum(bool(r["bestpath_ml_strict_disjoint_bool"]) for r in natural if r["dedup_complete_bool"]),
        "large_campaign_authorized": False,
        "conference_submission_ready": False,
        "next_step": "Write and independently review the narrow Paper-I conference manuscript only if the label is GO_PAPER_I_BASELINE_EXACT_DECODER; no additional simulation is authorized by this package.",
        "external_proof_review_required": True,
        "external_novelty_review_required": True,
    }


def run_campaign(binary: Path, config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter_ns()
    specs = build_trial_specs(config)
    metadata_path, input_path = write_trial_inputs(specs, output_dir)
    cpp_output = output_dir / "CPP_OUTPUT.tsv"
    process = _run_batch(binary, input_path, cpp_output, output_dir / "CPP_BATCH.log")
    cpp_rows = _read_tsv(cpp_output)
    merged, violations = _validate_and_merge(specs, cpp_rows)
    write_csv(output_dir / "TRIAL_RESULTS.csv", merged)
    write_json(output_dir / "VALIDATION_VIOLATIONS.json", {"count": len(violations), "violations": violations})
    cells = summarize_cells(merged)
    stress = summarize_stress(merged)
    write_csv(output_dir / "CELL_SUMMARY.csv", cells)
    write_csv(output_dir / "STRESS_SUMMARY.csv", stress)
    decision = _decision(config, merged, cells, violations)
    write_json(output_dir / "SCIENTIFIC_DECISION.json", decision)
    summary = {
        "phase": "Phase 2C baseline exact-decoder gate",
        "created_utc": utc_now_iso(),
        "status": "PASS" if decision["execution_correctness_pass"] else "FAIL",
        "trial_count": len(merged),
        "natural_trials": sum(r["trial_kind"] == "natural" for r in merged),
        "stress_trials": sum(r["trial_kind"] == "stress" for r in merged),
        "dedup_complete": sum(bool(r["dedup_complete_bool"]) for r in merged),
        "history_complete": sum(bool(r["history_complete_bool"]) for r in merged),
        "exhaustive_complete": sum(bool(r["exhaustive_complete_bool"]) for r in merged),
        "branch_complete": sum(bool(r["branch_complete_bool"]) for r in merged),
        "validation_violation_count": len(violations),
        "bestpath_selected_disagreements": sum(bool(r["bestpath_ml_selected_disagreement_bool"]) for r in merged if r["dedup_complete_bool"]),
        "bestpath_strict_disjoint_cases": sum(bool(r["bestpath_ml_strict_disjoint_bool"]) for r in merged if r["dedup_complete_bool"]),
        "cpp_process": process,
        "elapsed_ns": time.perf_counter_ns() - started,
        "decision": decision,
        "input_files": {"metadata": str(metadata_path), "cpp_input": str(input_path), "cpp_output": str(cpp_output)},
    }
    write_json(output_dir / "CAMPAIGN_REPORT.json", summary)
    return {"summary": summary, "rows": merged, "cells": cells, "stress": stress, "decision": decision}
