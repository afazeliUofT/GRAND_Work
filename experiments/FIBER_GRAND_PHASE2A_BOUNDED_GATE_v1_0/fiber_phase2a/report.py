from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from .util import median, percentile_nearest_rank, utc_now_iso, write_csv, write_json


def _cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["n"],
        row["rate_label"],
        row["family"],
        row["alignment_schedule"],
        row["p_num"],
        row["p_den"],
    )


def _paired_complete(row: dict[str, Any]) -> bool:
    return (
        bool(row["ind_complete"])
        and bool(row["cr_complete"])
        and bool(row["ac_complete"])
        and not bool(row["disagreement"])
    )


def _safe_ratio(num: int | float, den: int | float) -> float | str:
    return float(num) / float(den) if float(den) > 0 else ""


def summarize_cells(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["trial_kind"] == "natural":
            groups[_cell_key(row)].append(row)
    summaries: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda x: (int(x[0]), str(x[1]), str(x[2]), str(x[3]), int(x[5]))):
        cell = groups[key]
        paired = [r for r in cell if _paired_complete(r)]
        q_cr = [float(r["q_hist_improvement_ind_over_cr"]) for r in paired]
        q_ac = [float(r["q_hist_improvement_ind_over_ac"]) for r in paired]
        code_cr = [float(r["q_code_improvement_ind_over_cr"]) for r in paired]
        code_ac = [float(r["q_code_improvement_ind_over_ac"]) for r in paired]
        time_cr = [float(r["walltime_improvement_ind_over_cr"]) for r in paired]
        time_ac = [float(r["walltime_improvement_ind_over_ac"]) for r in paired]
        tail_status = "REPORTABLE" if len(paired) >= 100 else "INSUFFICIENT_N_FOR_99TH"
        summaries.append(
            {
                "n": key[0],
                "rate_label": key[1],
                "family": key[2],
                "alignment_schedule": key[3],
                "p_num": key[4],
                "p_den": key[5],
                "p_s": int(key[4]) / int(key[5]),
                "trials": len(cell),
                "paired_complete": len(paired),
                "ind_censored": sum(not bool(r["ind_complete"]) for r in cell),
                "cr_censored": sum(not bool(r["cr_complete"]) for r in cell),
                "ac_censored": sum(not bool(r["ac_complete"]) for r in cell),
                "disagreements": sum(bool(r["disagreement"]) for r in cell),
                "median_ind_q_hist": median([int(r["ind_q_hist"]) for r in cell]),
                "median_cr_q_hist": median([int(r["cr_q_hist"]) for r in cell]),
                "median_ac_q_hist": median([int(r["ac_q_hist"]) for r in cell]),
                "median_q_hist_ratio_ind_over_cr": median(q_cr) if q_cr else "",
                "median_q_hist_ratio_ind_over_ac": median(q_ac) if q_ac else "",
                "p90_q_hist_ratio_ind_over_cr": percentile_nearest_rank(q_cr, 0.90) if q_cr else "",
                "p90_q_hist_ratio_ind_over_ac": percentile_nearest_rank(q_ac, 0.90) if q_ac else "",
                "p99_q_hist_ratio_ind_over_cr": percentile_nearest_rank(q_cr, 0.99) if len(q_cr) >= 100 else "",
                "p99_q_hist_ratio_ind_over_ac": percentile_nearest_rank(q_ac, 0.99) if len(q_ac) >= 100 else "",
                "median_q_code_ratio_ind_over_cr": median(code_cr) if code_cr else "",
                "median_q_code_ratio_ind_over_ac": median(code_ac) if code_ac else "",
                "median_walltime_ratio_ind_over_cr": median(time_cr) if time_cr else "",
                "median_walltime_ratio_ind_over_ac": median(time_ac) if time_ac else "",
                "p90_walltime_ratio_ind_over_cr": percentile_nearest_rank(time_cr, 0.90) if time_cr else "",
                "p90_walltime_ratio_ind_over_ac": percentile_nearest_rank(time_ac, 0.90) if time_ac else "",
                "tail_status": tail_status,
            }
        )
    return summaries


def summarize_stress(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["trial_kind"] == "stress":
            groups[_cell_key(row) + (row["observed_error_weight"],)].append(row)
    out: list[dict[str, Any]] = []
    for key, cell in sorted(groups.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        paired = [r for r in cell if _paired_complete(r)]
        out.append(
            {
                "n": key[0],
                "rate_label": key[1],
                "family": key[2],
                "alignment_schedule": key[3],
                "p_num": key[4],
                "p_den": key[5],
                "observed_error_weight": key[6],
                "trials": len(cell),
                "paired_complete": len(paired),
                "ind_censored": sum(not bool(r["ind_complete"]) for r in cell),
                "cr_censored": sum(not bool(r["cr_complete"]) for r in cell),
                "ac_censored": sum(not bool(r["ac_complete"]) for r in cell),
                "median_q_hist_ratio_ind_over_cr": median([float(r["q_hist_improvement_ind_over_cr"]) for r in paired]) if paired else "",
                "median_q_hist_ratio_ind_over_ac": median([float(r["q_hist_improvement_ind_over_ac"]) for r in paired]) if paired else "",
                "median_walltime_ratio_ind_over_cr": median([float(r["walltime_improvement_ind_over_cr"]) for r in paired]) if paired else "",
                "median_walltime_ratio_ind_over_ac": median([float(r["walltime_improvement_ind_over_ac"]) for r in paired]) if paired else "",
            }
        )
    return out


def summarize_schedule_pairs(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare forward and even/odd tie orders on identical channel/code realizations."""
    by_realization: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (
            row["trial_kind"], row["trial_seed"], row["family"], row["n"], row["k"],
            row["p_num"], row["p_den"], row["forced_error_weight"],
        )
        by_realization[key][str(row["alignment_schedule"])] = row

    pair_rows: list[dict[str, Any]] = []
    for key, schedules in by_realization.items():
        if "forward" not in schedules or "even_odd" not in schedules:
            continue
        fwd = schedules["forward"]
        evo = schedules["even_odd"]
        row: dict[str, Any] = {
            "trial_kind": key[0],
            "trial_seed": key[1],
            "family": key[2],
            "n": key[3],
            "k": key[4],
            "p_num": key[5],
            "p_den": key[6],
            "forced_error_weight": key[7],
        }
        for prefix in ("ind", "cr", "ac"):
            row[f"{prefix}_both_complete"] = bool(fwd[f"{prefix}_complete"]) and bool(evo[f"{prefix}_complete"])
            row[f"{prefix}_q_hist_ratio_forward_over_even_odd"] = _safe_ratio(
                int(fwd[f"{prefix}_q_hist"]), int(evo[f"{prefix}_q_hist"])
            )
            row[f"{prefix}_walltime_ratio_forward_over_even_odd"] = _safe_ratio(
                int(fwd[f"{prefix}_total_time_ns"]), int(evo[f"{prefix}_total_time_ns"])
            )
        pair_rows.append(row)

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        groups[(row["trial_kind"], row["n"], row["family"], row["p_num"], row["p_den"])].append(row)

    out: list[dict[str, Any]] = []
    for key, group in sorted(groups.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        summary: dict[str, Any] = {
            "trial_kind": key[0], "n": key[1], "family": key[2],
            "p_num": key[3], "p_den": key[4], "paired_realizations": len(group),
        }
        for prefix in ("ind", "cr", "ac"):
            complete = [r for r in group if bool(r[f"{prefix}_both_complete"])]
            qvals = [float(r[f"{prefix}_q_hist_ratio_forward_over_even_odd"]) for r in complete]
            tvals = [float(r[f"{prefix}_walltime_ratio_forward_over_even_odd"]) for r in complete]
            summary[f"{prefix}_paired_complete"] = len(complete)
            summary[f"{prefix}_median_q_hist_ratio_forward_over_even_odd"] = median(qvals) if qvals else ""
            summary[f"{prefix}_median_walltime_ratio_forward_over_even_odd"] = median(tvals) if tvals else ""
        out.append(summary)
    return out


def _bound_metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    ac_ratios = [float(r["bound_ratio_ind_over_ac"]) for r in rows if math.isfinite(float(r["bound_ratio_ind_over_ac"]))]
    cr_ratios = [float(r["bound_ratio_ind_over_chain"]) for r in rows if math.isfinite(float(r["bound_ratio_ind_over_chain"]))]
    strict_ac = [r for r in rows if int(r["uac_bound"]) < int(r["independent_bound"])]
    strict_cr = [r for r in rows if int(r["chain_relaxed_bound"]) < int(r["independent_bound"])]
    hierarchy_failures = [r for r in rows if not int(r["uac_bound"]) <= int(r["chain_relaxed_bound"]) <= int(r["independent_bound"])]
    return {
        "cases": len(rows),
        "hierarchy_failures": len(hierarchy_failures),
        "strict_chain_cases": len(strict_cr),
        "strict_chain_fraction": len(strict_cr) / len(rows) if rows else 0.0,
        "strict_uac_cases": len(strict_ac),
        "strict_uac_fraction": len(strict_ac) / len(rows) if rows else 0.0,
        "median_bound_ratio_ind_over_chain": median(cr_ratios) if cr_ratios else "",
        "p90_bound_ratio_ind_over_chain": percentile_nearest_rank(cr_ratios, 0.90) if cr_ratios else "",
        "max_finite_bound_ratio_ind_over_chain": max(cr_ratios) if cr_ratios else "",
        "median_bound_ratio_ind_over_ac": median(ac_ratios) if ac_ratios else "",
        "p90_bound_ratio_ind_over_ac": percentile_nearest_rank(ac_ratios, 0.90) if ac_ratios else "",
        "max_finite_bound_ratio_ind_over_ac": max(ac_ratios) if ac_ratios else "",
        "zero_chain_positive_ind_cases": sum(int(r["chain_relaxed_bound"]) == 0 and int(r["independent_bound"]) > 0 for r in rows),
        "zero_uac_positive_ind_cases": sum(int(r["uac_bound"]) == 0 and int(r["independent_bound"]) > 0 for r in rows),
    }


def summarize_bound_scan(bound_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    overall = _bound_metrics(bound_rows)
    by_schedule: dict[str, Any] = {}
    for schedule in sorted({str(r.get("alignment_schedule", "unspecified")) for r in bound_rows}):
        by_schedule[schedule] = _bound_metrics([r for r in bound_rows if str(r.get("alignment_schedule", "unspecified")) == schedule])
    return {**overall, "by_schedule": by_schedule}


def classify(validation: dict[str, Any], pilot_summary: dict[str, Any], cells: Sequence[dict[str, Any]], bound_summary: dict[str, Any]) -> dict[str, Any]:
    if validation["status"] != "PASS" or pilot_summary["status"] != "PASS" or pilot_summary["exhaustive_ml_failures"] or bound_summary["hierarchy_failures"]:
        label = "BLOCKED_CORRECTNESS_FAILURE"
        reason = "At least one exact validation, bound-hierarchy, paired-decoder, or exhaustive-ML check failed."
    else:
        strong_cr = [c for c in cells if c["median_q_hist_ratio_ind_over_cr"] != "" and float(c["median_q_hist_ratio_ind_over_cr"]) >= 2.0]
        strong_ac = [c for c in cells if c["median_q_hist_ratio_ind_over_ac"] != "" and float(c["median_q_hist_ratio_ind_over_ac"]) >= 2.0]
        wall_cr = [c for c in cells if c["median_walltime_ratio_ind_over_cr"] != "" and float(c["median_walltime_ratio_ind_over_cr"]) > 1.0]
        wall_ac = [c for c in cells if c["median_walltime_ratio_ind_over_ac"] != "" and float(c["median_walltime_ratio_ind_over_ac"]) > 1.0]
        material = [c for c in cells if max(float(c["median_q_hist_ratio_ind_over_cr"] or 1.0), float(c["median_q_hist_ratio_ind_over_ac"] or 1.0)) >= 1.25]
        if (len(strong_cr) >= 4 and len(wall_cr) >= 2) or (len(strong_ac) >= 4 and len(wall_ac) >= 2):
            label = "CONTINUE_CANDIDATE_REQUIRES_SCIENTIFIC_REVIEW"
            reason = "A synchronization-specific bound repeatedly gives at least 2x median search-work reduction and at least two median wall-clock wins."
        elif material or float(bound_summary.get("median_bound_ratio_ind_over_ac") or 1.0) >= 1.25:
            label = "NARROW_OR_OPTIMIZE_CANDIDATE_REQUIRES_SCIENTIFIC_REVIEW"
            reason = "The specialized bounds are materially tighter somewhere, but the conference-level net-complexity gate is not yet established."
        else:
            label = "STOP_CANDIDATE_REQUIRES_SCIENTIFIC_REVIEW"
            reason = "The bounded pilot found no material search-work or structural-bound advantage."
    return {
        "automated_label": label,
        "reason": reason,
        "human_scientific_verdict_required": True,
        "conference_gate_passed": False,
        "tail_gate_status": "NOT_TESTED_TO_FINAL_PRECISION",
        "note": "This label is a screening diagnostic, not a publication claim or final novelty verdict.",
    }


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        return f"{value:.4g}"
    return str(value)


def _markdown_table(rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> str:
    if not rows:
        return "_No rows._\n"
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def make_report(output_dir: Path, validation: dict[str, Any], pilot_result: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    rows = pilot_result["rows"]
    bound_rows = pilot_result["bound_rows"]
    cells = summarize_cells(rows)
    stress = summarize_stress(rows)
    schedule_summary = summarize_schedule_pairs(rows)
    bound_summary = summarize_bound_scan(bound_rows)
    decision = classify(validation, pilot_result["summary"], cells, bound_summary)

    pilot_dir = output_dir / "pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    write_csv(pilot_dir / "cell_summary.csv", cells)
    write_csv(pilot_dir / "stress_summary.csv", stress)
    write_csv(pilot_dir / "schedule_summary.csv", schedule_summary)
    write_json(pilot_dir / "bound_scan_summary.json", bound_summary)
    write_json(pilot_dir / "SCREENING_DECISION.json", decision)

    columns = [
        "n", "rate_label", "family", "alignment_schedule", "p_s", "trials", "paired_complete",
        "median_q_hist_ratio_ind_over_cr", "median_walltime_ratio_ind_over_cr",
        "median_q_hist_ratio_ind_over_ac", "median_walltime_ratio_ind_over_ac",
        "ind_censored", "cr_censored", "ac_censored", "tail_status",
    ]
    validation_lines = [f"- **{r['name']}**: {r['status']} ({r['cases']} cases)" for r in validation.get("records", [])]
    schedule_lines = []
    for name, stats in bound_summary.get("by_schedule", {}).items():
        schedule_lines.append(
            f"- `{name}`: U_CR strict in {stats['strict_chain_cases']}/{stats['cases']} cases; "
            f"U_AC strict in {stats['strict_uac_cases']}/{stats['cases']} cases; "
            f"median U_ind/U_AC={_fmt(stats['median_bound_ratio_ind_over_ac'])}."
        )
    md = f"""# FIBER-GRAND Paper I — Phase 2A bounded-gate report

Generated: {utc_now_iso()}

## Automated screening label

**{decision['automated_label']}**

{decision['reason']}

This is not a paper-level GO verdict. The final verdict requires scientific review of the raw trials, proof source, and current literature.

## Correctness evidence

{chr(10).join(validation_lines)}

Paired three-mode decoder disagreements: **{pilot_result['summary']['disagreements']}**  
Exhaustive codeword-ML failures: **{pilot_result['summary']['exhaustive_ml_failures']}**  
Bound-hierarchy failures: **{bound_summary['hierarchy_failures']}**

## Natural-channel pilot by cell

{_markdown_table(cells, columns)}

`CR` is the O(n^2) recurrence-only chain relaxation; `AC` is the exact O(n^3) shell-consistent bound. A ratio above one favors the strengthened bound. Both use the same candidate stream as the independent certificate within a row. The two alignment schedules alter only the tie order among equal-probability alignment components. No 99th-percentile claim is made for cells with fewer than 100 paired complete trials.

## Structural bound scan by alignment schedule

{chr(10).join(schedule_lines)}

Forward shell completion is included as a negative control: its prefix frontier often makes the recurrence-only relaxation equal to the independent sum. The even/odd order tests whether schedule co-design creates useful nonmonotone frontier geometry without changing likelihood order.

## Interpretation rules

1. Any exact-validation, hierarchy, exhaustive-ML, or decoder disagreement blocks the project.
2. A cheap U_CR wall-clock win is stronger practical evidence than a large U_AC work reduction whose DP overhead dominates.
3. A sound but expensive U_AC result supports at most a mathematical/ITW route unless a cheaper realization or stronger complexity theorem is found.
4. Schedule gains are algorithm-design evidence only; they do not create novelty by themselves.
5. Negligible tightening across both specialized bounds is a STOP signal; adding channel models is not a remedy.

## Files to inspect

- `validation/exact_validation_summary.json`
- `pilot/paired_trials.csv`
- `pilot/cell_summary.csv`
- `pilot/stress_summary.csv`
- `pilot/schedule_summary.csv`
- `pilot/bound_scan.csv`
- `pilot/bound_scan_summary.json`
- `pilot/SCREENING_DECISION.json`
- `theory/FIBER_GRAND_Phase2A_Proof_Closure_Candidate.tex`
"""
    (output_dir / "PHASE2A_REPORT.md").write_text(md, encoding="utf-8")
    report = {
        "created_utc": utc_now_iso(),
        "validation_status": validation["status"],
        "pilot_status": pilot_result["summary"]["status"],
        "cell_count": len(cells),
        "schedule_summary_rows": len(schedule_summary),
        "bound_summary": bound_summary,
        "screening_decision": decision,
    }
    write_json(output_dir / "PHASE2A_REPORT.json", report)
    return report
