from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

from .theory import (
    binary_entropy,
    binomial_upper_quantile,
    exact_expected_membership_cap,
    generated_attempt_cap,
    realization_shell_cap,
    stopping_offset_uniform,
)
from .util import utc_now_iso, write_csv, write_json


def _fmt(value: Any) -> str:
    if value == "" or value is None:
        return "--"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "inf" if value > 0 else "nan"
        if abs(value) >= 10000 or (0 < abs(value) < 0.001):
            return f"{value:.3e}"
        return f"{value:.4g}"
    return str(value)


def _table(rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> str:
    if not rows:
        return "_No rows._\n"
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def finite_length_theory_table(config: dict[str, Any]) -> list[dict[str, Any]]:
    p_num = int(config["channel"]["p_num"])
    p_den = int(config["channel"]["p_den"])
    ns = sorted({int(cell["n"]) for cell in config["natural_campaign"]["cells"]})
    rows: list[dict[str, Any]] = []
    for n in ns:
        m = n - 1
        ell = stopping_offset_uniform(n, p_num, p_den)
        for delta in (0.01, 0.001):
            tau = binomial_upper_quantile(m, p_num, p_den, delta)
            stop = realization_shell_cap(n, p_num, p_den, tau)
            rows.append(
                {
                    "n": n,
                    "p_s": p_num / p_den,
                    "delta": delta,
                    "L_n": ell,
                    "binomial_error_weight_quantile": tau,
                    "certified_stop_shell": stop,
                    "deduplicated_generated_cap": generated_attempt_cap(n, stop, True),
                    "history_pair_generated_cap": generated_attempt_cap(n, stop, False),
                    "exact_expected_membership_cap": exact_expected_membership_cap(n, p_num, p_den),
                    "h2_p": binary_entropy(p_num / p_den),
                }
            )
    return rows


def make_report(
    output_dir: Path,
    config: dict[str, Any],
    theory: dict[str, Any],
    build: dict[str, Any],
    campaign: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cells = campaign["cells"]
    decision = campaign["decision"]
    finite = finite_length_theory_table(config)
    write_csv(output_dir / "THEORY_FINITE_LENGTH_TABLE.csv", finite)

    n32 = [row for row in cells if int(row["n"]) == 32]
    key_columns = [
        "cell_id",
        "natural_trials",
        "dedup_censor_fraction",
        "median_q_membership",
        "median_q_score",
        "median_codeword_score_savings",
        "p10_codeword_score_savings",
        "median_codebook_membership_ratio",
        "median_exhaustive_over_dedup_walltime",
        "median_branch_over_dedup_walltime",
        "bestpath_selected_disagreement_fraction",
    ]
    theory_columns = [
        "n", "p_s", "delta", "L_n", "binomial_error_weight_quantile", "certified_stop_shell",
        "deduplicated_generated_cap", "history_pair_generated_cap", "exact_expected_membership_cap", "h2_p",
    ]

    lines = [
        "# FIBER-GRAND Paper I — Phase 2C baseline exact-decoder gate",
        "",
        f"Generated: {utc_now_iso()}",
        "",
        "## Scientific decision",
        "",
        f"**{decision['label']}**",
        "",
        str(decision["reason"]),
        "",
        "This is a bounded evidence decision. It is not a conference acceptance, an absolute novelty determination, or authorization for a broader channel campaign.",
        "",
        "## Exactness and execution",
        "",
        f"- Theorem-support checks: **{theory['status']}** ({theory['exact_cases']} exact cases).",
        f"- C++17 build/self-test: **{build['status']}**.",
        f"- Preregistered trials: **{campaign['summary']['trial_count']}**; natural: {campaign['summary']['natural_trials']}; stress: {campaign['summary']['stress_trials']}.",
        f"- Validation violations: **{campaign['summary']['validation_violation_count']}**.",
        f"- Complete deduplicated exact decodes: {campaign['summary']['dedup_complete']}/{campaign['summary']['trial_count']}.",
        f"- Exhaustive exact-ML comparisons completed: {campaign['summary']['exhaustive_complete']}.",
        f"- Complete branch-and-bound comparisons: {campaign['summary']['branch_complete']}.",
        "",
        "## Main n=32 evidence",
        "",
        _table(n32, key_columns),
        "## Structural and practical interpretation",
        "",
        "1. `codeword_score_savings` is the codebook size divided by the number of complete aggregate-likelihood evaluations. It directly measures avoided codeword-wise ML scoring, not a universal runtime ratio.",
        "2. `codebook_membership_ratio` is the codebook size divided by distinct code-membership queries. Membership tests and complete likelihood evaluations are intentionally reported separately.",
        "3. The history-pair and insertion-sphere generators return the same exact ML result. A reduction in generated hypotheses is useful only if it survives end-to-end overhead.",
        "4. Exhaustive and branch-and-bound timings are code/implementation baselines, not claims of instance-optimality against every specialized decoder.",
        "5. Best-path disagreement is reported separately from strict disjointness of the best-path and aggregate-ML tie sets.",
        "",
        "## Finite-length theorem table",
        "",
        _table(finite, theory_columns),
        "## Decision gates",
        "",
        f"- Exact correctness: **{_fmt(decision['execution_correctness_pass'])}**.",
        f"- Repeated n=32 query/score savings: **{_fmt(decision['query_complexity_gate_pass'])}**.",
        f"- Exact exhaustive wall-clock calibration: **{_fmt(decision['exact_exhaustive_speed_gate_pass'])}**.",
        f"- Deduplicated-generation wall-clock gate: **{_fmt(decision['deduplicated_generation_speed_gate_pass'])}**.",
        f"- Natural-channel completion gate: **{_fmt(decision['natural_censor_gate_pass'])}**.",
        "",
        "## Scope discipline",
        "",
        "The expensive alignment-consistent `U_AC` certificate was already narrowed to a mathematical result in Phase 2B-R1. Phase 2C evaluates only the baseline shell-certified exact decoder, a classical insertion-sphere deduplication, best-path behavior, exhaustive codeword ML where feasible, and a generic exact branch-and-bound comparator. Multiple deletions, insertions, soft information, general transducers, code design, and hardware remain outside Paper I.",
        "",
        "## Required review before writing claims",
        "",
        "- independent proof review of the theorem source;",
        "- updated novelty review against GRAND complexity theory, deletion-channel exact search, and correlated/threshold aggregation;",
        "- claim-by-claim distinction between oracle/query complexity and wall-clock complexity.",
        "",
        "## Files",
        "",
        "- `theory/FIBER_GRAND_Phase2C_Baseline_Exact_Decoder_Theorems.tex`",
        "- `theory/THEORY_CHECKS.json`",
        "- `campaign/TRIAL_RESULTS.csv`",
        "- `campaign/CELL_SUMMARY.csv`",
        "- `campaign/STRESS_SUMMARY.csv`",
        "- `campaign/VALIDATION_VIOLATIONS.json`",
        "- `SCIENTIFIC_DECISION.json`",
    ]
    markdown = "\n".join(lines).replace("\n\n|", "\n\n|") + "\n"
    (output_dir / "PHASE2C_REPORT.md").write_text(markdown, encoding="utf-8", newline="\n")

    report = {
        "created_utc": utc_now_iso(),
        "status": "PASS" if theory["status"] == "PASS" and build["status"] == "PASS" and campaign["summary"]["status"] == "PASS" else "FAIL",
        "decision": decision,
        "theory": theory,
        "build": build,
        "campaign_summary": campaign["summary"],
        "n32_cells": n32,
        "finite_length_theory": finite,
    }
    write_json(output_dir / "PHASE2C_REPORT.json", report)
    write_json(output_dir / "SCIENTIFIC_DECISION.json", decision)
    return report
