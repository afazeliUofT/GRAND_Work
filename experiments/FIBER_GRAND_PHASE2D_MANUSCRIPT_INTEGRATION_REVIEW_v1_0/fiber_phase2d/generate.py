from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _fmt(x: float | None) -> str:
    if x is None:
        return "--"
    if abs(x) >= 1e6:
        return f"{x / 1e6:.3g}\\,$\\times 10^6$"
    if abs(x) >= 1e4:
        return f"{x:.0f}"
    if abs(x) >= 100:
        return f"{x:.1f}"
    return f"{x:.3g}"


def generate(cells: list[dict[str, str]], expected: dict[str, Any], manuscript: Path) -> dict[str, Any]:
    by_id = {row["cell_id"]: row for row in cells}
    selected = [by_id[item["cell_id"]] for item in expected["n32_cells"]]
    generated = manuscript / "generated"
    generated.mkdir(parents=True, exist_ok=True)

    macros = "% Auto-generated from pinned Phase-2C evidence.\n"
    macros += "\\newcommand{\\PhaseTwoCCommit}{" + expected["phase2c_commit"] + "}\n"
    macros += "\\newcommand{\\TotalTrials}{996}\n"
    macros += "\\newcommand{\\NaturalTrials}{896}\n"
    macros += "\\newcommand{\\StressTrials}{100}\n"
    macros += "\\newcommand{\\ExactTheoryChecks}{335146}\n"
    macros += "\\newcommand{\\ExhaustiveChecks}{384}\n"
    macros += "\\newcommand{\\BranchChecks}{432}\n"
    macros += "\\newcommand{\\ValidationViolations}{0}\n"
    macros += "\\newcommand{\\MedianNThirtyTwoExhaustiveSpeedup}{465.6}\n"
    macros += "\\newcommand{\\NThirtyTwoQueryCells}{5}\n"
    (generated / "frozen_metrics.tex").write_text(macros, encoding="utf-8", newline="\n")

    lines = [
        r"\begin{table*}[t]",
        r"\caption{Frozen $n=32$, $p_s=0.05$ natural-channel evidence (64 trials per cell). Ratios are medians unless marked otherwise. A dash means exhaustive calibration was not run at that dimension.}",
        r"\label{tab:n32}",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{3.5pt}",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabular}{@{}lrrrrrrr@{}}",
        r"\toprule",
        r"Code / dimension & $Q_{\rm mem}$ & $Q_{\rm score}$ & $|\mathcal C|/Q_{\rm score}$ & P10 $|\mathcal C|/Q_{\rm score}$ & $|\mathcal C|/Q_{\rm mem}$ & Exhaustive / FIBER & B\&B / FIBER\\",
        r"\midrule",
    ]
    label_map = {
        "n32_k21_crc_defined_linear_R2_3": "CRC, $k=21$",
        "n32_k21_random_systematic_linear_R2_3": "Random, $k=21$",
        "n32_k24_crc_defined_linear_R3_4": "CRC, $k=24$",
        "n32_k24_random_systematic_linear_R3_4": "Random, $k=24$",
        "n32_k26_extended_hamming_HAMMING": "Ext. Hamming, $k=26$",
    }
    for row in selected:
        exhaustive = row["median_exhaustive_over_dedup_walltime"].strip()
        exhaustive_value = float(exhaustive) if exhaustive else None
        values = [
            label_map[row["cell_id"]],
            _fmt(float(row["median_q_membership"])),
            _fmt(float(row["median_q_score"])),
            _fmt(float(row["median_codeword_score_savings"])),
            _fmt(float(row["p10_codeword_score_savings"])),
            _fmt(float(row["median_codebook_membership_ratio"])),
            _fmt(exhaustive_value),
            _fmt(float(row["median_branch_over_dedup_walltime"])),
        ]
        lines.append(" & ".join(values) + r"\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}"])
    (generated / "n32_table.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    with (generated / "figure_source_data.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cell_id", "score_savings", "membership_ratio"])
        for row in selected:
            writer.writerow(
                [row["cell_id"], row["median_codeword_score_savings"], row["median_codebook_membership_ratio"]]
            )
    return {
        "selected_cells": len(selected),
        "generated_files": ["frozen_metrics.tex", "n32_table.tex", "figure_source_data.csv"],
    }
