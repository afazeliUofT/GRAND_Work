from __future__ import annotations

import csv
import random
import time
from pathlib import Path
from typing import Any

from .reference import build_code, chain_bound, independent_bound, uac_bound
from .util import median, read_csv, run, stable_seed, utc_now_iso, write_csv, write_json


def _write_tsv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _ties(text: str) -> tuple[int, ...]:
    if not text.strip():
        return ()
    return tuple(sorted(int(token, 0) for token in text.replace(",", " ").split()))


def _bool_text(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def _synthetic_bound_crosscheck(binary: Path, master_seed: int, output: Path) -> dict[str, Any]:
    """Cross-check the compiled bound kernels on deterministic nonuniform cases.

    Frozen Phase-2A performance rows use uniform deletion weights.  This auxiliary
    gate deliberately uses zero and nonuniform positive weights, exhausted streams,
    multiple odds ratios, and irregular frontier vectors so the compiled kernel is
    not validated only on the performance subset.
    """

    rng = random.Random(stable_seed(master_seed, "phase2b_compiled_bound_crosscheck"))
    cases: list[dict[str, Any]] = []
    for n in range(2, 13):
        m = n - 1
        structured = [
            (0,) * n,
            (1,) * n,
            (m,) * n,
            (n,) * n,
            tuple(i % min(3, n) for i in range(n)),
            tuple(1 if i % 2 else 0 for i in range(n)),
        ]
        for case_index in range(18):
            frontier = structured[case_index] if case_index < len(structured) else tuple(
                rng.randrange(0, n + 1) for _ in range(n)
            )
            weights = tuple(rng.randrange(0, 8) for _ in range(n))
            if not any(weights):
                weights = (1,) + weights[1:]
            cases.append(
                {
                    "id": len(cases),
                    "n": n,
                    "a": (3, 4, 19, 99)[case_index % 4],
                    "y": rng.randrange(1 << (n - 1)),
                    "frontier": frontier,
                    "weights": weights,
                }
            )

    input_rows = [
        [
            case["id"],
            case["n"],
            case["a"],
            hex(case["y"]),
            ",".join(str(value) for value in case["frontier"]),
            ",".join(str(value) for value in case["weights"]),
        ]
        for case in cases
    ]
    input_path = output / "SYNTHETIC_BOUNDS_INPUT.tsv"
    result_path = output / "SYNTHETIC_BOUNDS_CPP.tsv"
    _write_tsv(input_path, ["id", "n", "a", "y", "frontier", "weights"], input_rows)
    process = run([binary, "bounds-batch", input_path, result_path], log=output / "SYNTHETIC_BOUNDS_CPP.log")
    compiled = _read_tsv(result_path)

    mismatches: list[dict[str, Any]] = []
    for case, got in zip(cases, compiled):
        expected = {
            "ind": independent_bound(case["frontier"], case["n"], case["a"], case["weights"]),
            "cr": chain_bound(case["y"], case["frontier"], case["n"], case["a"], case["weights"]),
            "ac": uac_bound(case["y"], case["frontier"], case["n"], case["a"], case["weights"]),
        }
        for field, value in expected.items():
            if str(value) != str(got[field]):
                mismatches.append(
                    {
                        "case": case["id"],
                        "field": field,
                        "expected": str(value),
                        "compiled": got[field],
                        "n": case["n"],
                        "a": case["a"],
                        "y": hex(case["y"]),
                        "frontier": case["frontier"],
                        "weights": case["weights"],
                    }
                )

    report = {
        "created_utc": utc_now_iso(),
        "cases": len(cases),
        "compiled_rows": len(compiled),
        "mismatches": len(mismatches),
        "process_ns": int(getattr(process, "elapsed_ns", 0)),
        "status": "PASS" if len(compiled) == len(cases) and not mismatches else "FAIL",
    }
    write_json(output / "SYNTHETIC_BOUNDS_REPORT.json", report)
    write_json(output / "SYNTHETIC_BOUNDS_MISMATCHES.json", {"mismatches": mismatches[:200]})
    return report


def run_replay(
    repo: Path,
    binary: Path,
    config: dict[str, Any],
    output: Path,
    *,
    phase2a_pilot: Path | None = None,
) -> dict[str, Any]:
    if phase2a_pilot is None:
        phase2a_pilot = repo / config["phase2a_run_relative"] / "pilot"
    phase2a_pilot = phase2a_pilot.resolve()
    bound_rows = read_csv(phase2a_pilot / "bound_scan.csv")
    trial_rows = read_csv(phase2a_pilot / "paired_trials.csv")
    bound_limit = int(config["replay"].get("bound_limit", 0))
    trial_limit = int(config["replay"].get("trial_limit", 0))
    if bound_limit:
        bound_rows = bound_rows[:bound_limit]
    if trial_limit:
        trial_rows = trial_rows[:trial_limit]
    output.mkdir(parents=True, exist_ok=True)

    synthetic = _synthetic_bound_crosscheck(binary, int(config["master_seed"]), output)

    bound_input: list[list[Any]] = []
    for index, row in enumerate(bound_rows):
        n = int(row["n"])
        frontier = ",".join(row["frontier"].split())
        bound_input.append(
            [
                index,
                n,
                int(row["p_den"]) - 1,
                row["observation_hex"],
                frontier,
                ",".join(["1"] * n),
            ]
        )
    _write_tsv(output / "bounds_input.tsv", ["id", "n", "a", "y", "frontier", "weights"], bound_input)
    cpp_bounds_process = run(
        [binary, "bounds-batch", output / "bounds_input.tsv", output / "bounds_cpp.tsv"],
        log=output / "BOUNDS_CPP.log",
    )
    cpp_bounds = _read_tsv(output / "bounds_cpp.tsv")
    bound_mismatches: list[dict[str, Any]] = []
    for index, (source, got) in enumerate(zip(bound_rows, cpp_bounds)):
        for source_key, cpp_key in (
            ("independent_bound", "ind"),
            ("chain_relaxed_bound", "cr"),
            ("uac_bound", "ac"),
        ):
            if str(source[source_key]) != str(got[cpp_key]):
                bound_mismatches.append(
                    {"case": index, "field": source_key, "expected": source[source_key], "got": got[cpp_key]}
                )

    python_started = time.perf_counter_ns()
    for row in bound_rows:
        uac_bound(
            int(row["observation_hex"], 0),
            tuple(int(value) for value in row["frontier"].split()),
            int(row["n"]),
            int(row["p_den"]) - 1,
        )
    python_uac_ns = time.perf_counter_ns() - python_started
    cpp_uac_kernel_ns = sum(int(row["ac_ns"]) for row in cpp_bounds)
    kernel_speedup = python_uac_ns / cpp_uac_kernel_ns if cpp_uac_kernel_ns else float("inf")

    decode_input: list[list[Any]] = []
    for index, row in enumerate(trial_rows):
        code = build_code(row["family"], int(row["n"]), int(row["k"]), int(row["code_seed"]))
        decode_input.append(
            [
                index,
                code.n,
                code.k,
                int(row["p_den"]) - 1,
                row["alignment_schedule"],
                row["max_histories"],
                row["observation_hex"],
                row["transmitted_word_hex"],
                ",".join(hex(mask) for mask in code.rows),
            ]
        )
    _write_tsv(
        output / "decode_input.tsv",
        ["id", "n", "k", "a", "schedule", "max_hist", "y", "transmitted", "rows"],
        decode_input,
    )
    cpp_decode_process = run(
        [binary, "decode-batch", output / "decode_input.tsv", output / "decode_cpp.tsv"],
        log=output / "DECODE_CPP.log",
    )
    cpp_decode = _read_tsv(output / "decode_cpp.tsv")

    decode_mismatches: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    for index, (source, got) in enumerate(zip(trial_rows, cpp_decode)):
        comparison: dict[str, Any] = {
            "case": index,
            "n": int(source["n"]),
            "family": source["family"],
            "schedule": source["alignment_schedule"],
            "p_s": float(source["p_s"]),
        }
        for prefix in ("ind", "cr", "ac"):
            checks = {
                "status": source[f"{prefix}_status"] == got[f"{prefix}_status"],
                "complete": _bool_text(source[f"{prefix}_complete"]) == _bool_text(got[f"{prefix}_complete"]),
                "q_hist": str(source[f"{prefix}_q_hist"]) == str(got[f"{prefix}_q_hist"]),
                "q_disc": str(source[f"{prefix}_q_disc"]) == str(got[f"{prefix}_q_disc"]),
                "q_code": str(source[f"{prefix}_q_code"]) == str(got[f"{prefix}_q_code"]),
                "q_score": str(source[f"{prefix}_q_score"]) == str(got[f"{prefix}_q_score"]),
                "frontier_updates": str(source[f"{prefix}_frontier_updates"]) == str(got[f"{prefix}_frontier_updates"]),
                "score": str(source[f"{prefix}_incumbent_score"]) == str(got[f"{prefix}_score"]),
                "final_bound": str(source[f"{prefix}_final_bound"]) == str(got[f"{prefix}_bound"]),
                "decoded": source[f"{prefix}_decoded_word_hex"].lower() == got[f"{prefix}_decoded"].lower(),
                "ties": _ties(source[f"{prefix}_tie_words_hex"]) == _ties(got[f"{prefix}_ties"]),
            }
            for field, passed in checks.items():
                if not passed:
                    decode_mismatches.append(
                        {
                            "case": index,
                            "mode": prefix,
                            "field": field,
                            "source": source.get(f"{prefix}_{field}", ""),
                            "compiled": got.get(f"{prefix}_{field}", ""),
                        }
                    )
            comparison[f"{prefix}_q_hist"] = int(got[f"{prefix}_q_hist"])
            comparison[f"{prefix}_total_ns"] = int(got[f"{prefix}_total_ns"])

        fast_signature = (got["fast_score"], _ties(got["fast_ties"]), got["fast_decoded"].lower())
        independent_signature = (got["ind_score"], _ties(got["ind_ties"]), got["ind_decoded"].lower())
        if fast_signature != independent_signature or not _bool_text(got["fast_complete"]):
            decode_mismatches.append(
                {
                    "case": index,
                    "mode": "fast",
                    "field": "exact_output_or_completion",
                    "source": independent_signature,
                    "compiled": fast_signature,
                    "fast_complete": got["fast_complete"],
                }
            )
        comparison["fast_q_hist"] = int(got["fast_q_hist"])
        comparison["fast_total_ns"] = int(got["fast_total_ns"])
        comparison["work_ratio_ind_over_ac"] = comparison["ind_q_hist"] / comparison["ac_q_hist"]
        comparison["work_ratio_ind_over_fast"] = comparison["ind_q_hist"] / comparison["fast_q_hist"]
        comparison["time_ratio_ac_over_ind"] = comparison["ac_total_ns"] / max(1, comparison["ind_total_ns"])
        comparison["time_ratio_fast_over_ind"] = comparison["fast_total_ns"] / max(1, comparison["ind_total_ns"])
        comparison_rows.append(comparison)

    write_csv(output / "REPLAY_COMPARISON.csv", comparison_rows)
    hard_rows = [
        row
        for row in comparison_rows
        if row["work_ratio_ind_over_fast"] >= float(config["replay"]["hard_work_ratio"])
    ]
    hard_median = median([row["time_ratio_fast_over_ind"] for row in hard_rows]) if hard_rows else None

    exact_pass = (
        synthetic["status"] == "PASS"
        and not bound_mismatches
        and not decode_mismatches
        and len(cpp_bounds) == len(bound_rows)
        and len(cpp_decode) == len(trial_rows)
    )
    kernel_speed_pass = kernel_speedup >= float(config["replay"]["kernel_speedup_min"])
    hard_end_to_end_pass = (
        len(hard_rows) >= int(config["replay"]["hard_min_cases"])
        and hard_median is not None
        and hard_median <= float(config["replay"]["hard_median_fast_over_ind_max"])
    )
    targeted_authorized = exact_pass and kernel_speed_pass and hard_end_to_end_pass
    report = {
        "created_utc": utc_now_iso(),
        "synthetic_bound_cases": synthetic["cases"],
        "synthetic_bound_mismatches": synthetic["mismatches"],
        "bound_cases": len(bound_rows),
        "trial_cases": len(trial_rows),
        "bound_mismatches": len(bound_mismatches),
        "decode_mismatches": len(decode_mismatches),
        "python_uac_ns": python_uac_ns,
        "cpp_uac_kernel_ns": cpp_uac_kernel_ns,
        "cpp_bounds_process_ns": int(getattr(cpp_bounds_process, "elapsed_ns", 0)),
        "cpp_decode_process_ns": int(getattr(cpp_decode_process, "elapsed_ns", 0)),
        "kernel_speedup": kernel_speedup,
        "hard_case_count": len(hard_rows),
        "hard_case_median_fast_over_ind_time": hard_median,
        "exact_pass": exact_pass,
        "kernel_speed_pass": kernel_speed_pass,
        "hard_end_to_end_pass": hard_end_to_end_pass,
        "targeted_pilot_authorized": targeted_authorized,
        "status": "PASS" if exact_pass else "FAIL",
    }
    write_json(output / "REPLAY_REPORT.json", report)
    write_json(
        output / "REPLAY_MISMATCHES.json",
        {
            "synthetic": read_json_if_exists(output / "SYNTHETIC_BOUNDS_MISMATCHES.json"),
            "bounds": bound_mismatches[:200],
            "decode": decode_mismatches[:200],
        },
    )
    return report


def read_json_if_exists(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
