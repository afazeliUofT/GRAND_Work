from __future__ import annotations

import concurrent.futures
import functools
import math
import os
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from .bounds import chain_relaxed_dp_int, independent_bound_int, uac_dp_optimized_int
from .codes import SystematicParityCode, build_code
from .model import delete_bit, scaled_score_int
from .search import decode_exact_search
from .util import median, percentile_nearest_rank, stable_seed, utc_now_iso, write_csv, write_json


@functools.lru_cache(maxsize=None)
def _cached_code(family: str, n: int, k: int, seed: int) -> SystematicParityCode:
    return build_code(family, n, k, seed)


def _sample_error_mask(rng: random.Random, m: int, p_num: int, p_den: int, forced_weight: int | None) -> int:
    if forced_weight is not None:
        if not 0 <= forced_weight <= m:
            raise ValueError("forced error weight outside range")
        positions = rng.sample(range(m), forced_weight)
        mask = 0
        for pos in positions:
            mask |= 1 << pos
        return mask
    p = p_num / p_den
    mask = 0
    for pos in range(m):
        if rng.random() < p:
            mask |= 1 << pos
    return mask


def _exhaustive_codeword_ml(code: SystematicParityCode, y: int, a: int) -> tuple[int, tuple[int, ...], int]:
    started = time.perf_counter_ns()
    best = -1
    ties: list[int] = []
    for message in range(1 << code.k):
        x = code.encode(message)
        score = scaled_score_int(x, y, code.n, a)
        if score > best:
            best = score
            ties = [x]
        elif score == best:
            ties.append(x)
    return best, tuple(sorted(ties)), time.perf_counter_ns() - started


def _run_trial(spec: dict[str, Any]) -> dict[str, Any]:
    n = int(spec["n"])
    k = int(spec["k"])
    family = str(spec["family"])
    p_num = int(spec["p_num"])
    p_den = int(spec["p_den"])
    a = (p_den - p_num) // p_num
    if p_num != 1 or p_den not in (20, 100):
        raise ValueError("Phase-2A exact integer pilot is frozen to p=1/20 or 1/100")
    seed = int(spec["trial_seed"])
    rng = random.Random(seed)
    code_seed = int(spec["code_seed"])
    code = _cached_code(family, n, k, code_seed)
    message = rng.randrange(1 << k)
    transmitted = code.encode(message)
    deletion_position = rng.randrange(n)
    m = n - 1
    forced_weight = spec.get("forced_error_weight")
    error_mask = _sample_error_mask(rng, m, p_num, p_den, forced_weight)
    y = delete_bit(transmitted, deletion_position) ^ error_mask

    common = {
        "y": y,
        "code": code,
        "odds_denominator": a,
        "max_histories": int(spec["max_histories"]),
        "alignment_schedule": str(spec["alignment_schedule"]),
    }
    # Rotate order to reduce systematic cache/thermal bias in three-way timing.
    modes = ["independent", "chain_relaxed", "alignment_consistent"]
    shift = int(spec["trial_index"]) % len(modes)
    modes = modes[shift:] + modes[:shift]
    decoded: dict[str, Any] = {}
    for mode in modes:
        decoded[mode] = decode_exact_search(bound_mode=mode, **common)

    ind = decoded["independent"]
    cr = decoded["chain_relaxed"]
    ac = decoded["alignment_consistent"]
    disagreement = False
    disagreement_reason = ""
    complete_results = [result for result in (ind, cr, ac) if result.complete]
    if len(complete_results) == 3:
        signatures = {(r.incumbent_score, r.tie_words, r.decoded_word) for r in complete_results}
        if len(signatures) != 1:
            disagreement = True
            disagreement_reason = "bound modes returned different exact results"
        if not (ac.q_hist <= cr.q_hist <= ind.q_hist):
            disagreement = True
            disagreement_reason = "stopping-work ordering U_AC <= U_CR <= U_ind was violated"

    exhaustive_status = "NOT_RUN"
    exhaustive_time_ns = 0
    exhaustive_score = None
    exhaustive_ties: tuple[int, ...] = ()
    if bool(spec.get("run_exhaustive_ml", False)):
        exhaustive_score, exhaustive_ties, exhaustive_time_ns = _exhaustive_codeword_ml(code, y, a)
        exhaustive_status = "PASS"
        for result in (ind, cr, ac):
            if result.complete and (result.incumbent_score != exhaustive_score or result.tie_words != exhaustive_ties):
                exhaustive_status = "FAIL"
                disagreement = True
                disagreement_reason = f"{result.bound_mode} disagrees with exhaustive codeword ML"

    row: dict[str, Any] = {
        "trial_kind": spec["trial_kind"],
        "trial_index": spec["trial_index"],
        "trial_seed": seed,
        "code_seed": code_seed,
        "family": family,
        "alignment_schedule": spec["alignment_schedule"],
        "n": n,
        "k": k,
        "rate": k / n,
        "rate_label": spec["rate_label"],
        "p_num": p_num,
        "p_den": p_den,
        "p_s": p_num / p_den,
        "odds_denominator": a,
        "forced_error_weight": forced_weight if forced_weight is not None else "",
        "observed_error_weight": error_mask.bit_count(),
        "deletion_position": deletion_position,
        "transmitted_word_hex": hex(transmitted),
        "observation_hex": hex(y),
        "max_histories": spec["max_histories"],
        "exhaustive_status": exhaustive_status,
        "exhaustive_time_ns": exhaustive_time_ns,
        "exhaustive_score": exhaustive_score if exhaustive_score is not None else "",
        "exhaustive_tie_count": len(exhaustive_ties),
        "disagreement": disagreement,
        "disagreement_reason": disagreement_reason,
    }
    for prefix, result in (("ind", ind), ("cr", cr), ("ac", ac)):
        for key, value in result.to_dict().items():
            if key == "tie_words":
                row[f"{prefix}_tie_count"] = len(value)  # type: ignore[arg-type]
                row[f"{prefix}_tie_words_hex"] = " ".join(hex(int(x)) for x in value)  # type: ignore[arg-type]
            elif key == "decoded_word":
                row[f"{prefix}_decoded_word_hex"] = "" if value is None else hex(int(value))
            else:
                row[f"{prefix}_{key}"] = value
    for suffix, result in (("cr", cr), ("ac", ac)):
        row[f"q_hist_improvement_ind_over_{suffix}"] = (ind.q_hist / result.q_hist) if ind.q_hist > 0 and result.q_hist > 0 else ""
        row[f"q_code_improvement_ind_over_{suffix}"] = (ind.q_code / result.q_code) if ind.q_code > 0 and result.q_code > 0 else ""
        row[f"walltime_improvement_ind_over_{suffix}"] = (ind.total_time_ns / result.total_time_ns) if ind.total_time_ns > 0 and result.total_time_ns > 0 else ""
    return row


def _rate_to_k(n: int, rate_label: str, target_rate: float) -> int:
    k = int(round(n * target_rate))
    if not 1 <= k < n:
        raise ValueError("invalid dimension")
    return k


def build_trial_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    master_seed = int(config["master_seed"])
    specs: list[dict[str, Any]] = []
    natural_trials = int(config["pilot"]["natural_trials_per_cell"])
    natural_cap = int(config["pilot"]["natural_max_histories"])
    stress_cap = int(config["pilot"]["stress_max_histories"])
    families = list(config["pilot"]["code_families"])
    p_points = list(config["pilot"]["p_points"])
    rates = list(config["pilot"]["rates"])
    schedules = list(config["pilot"].get("alignment_schedules", ["forward"]))

    for n in config["pilot"]["blocklengths"]:
        n = int(n)
        for rate in rates:
            rate_label = str(rate["label"])
            k = _rate_to_k(n, rate_label, float(rate["target"]))
            for family in families:
                code_seed = stable_seed(master_seed, "code", family, n, k)
                for p in p_points:
                    p_num, p_den = int(p["num"]), int(p["den"])
                    for alignment_schedule in schedules:
                        for trial_index in range(natural_trials):
                            specs.append(
                                {
                                    "trial_kind": "natural",
                                    "trial_index": trial_index,
                                    "trial_seed": stable_seed(master_seed, "natural", family, n, k, p_num, p_den, trial_index),
                                    "code_seed": code_seed,
                                    "family": family,
                                    "alignment_schedule": alignment_schedule,
                                    "n": n,
                                    "k": k,
                                    "rate_label": rate_label,
                                    "p_num": p_num,
                                    "p_den": p_den,
                                    "forced_error_weight": None,
                                    "max_histories": natural_cap,
                                    "run_exhaustive_ml": n <= int(config["pilot"]["exhaustive_ml_max_n"]),
                                }
                            )

    stress = config["pilot"].get("stress", {})
    if stress.get("enabled", True):
        reps = int(stress.get("repetitions_per_weight", 1))
        weight_map = stress["weights_by_n_and_p"]
        stress_rate_labels = set(str(x) for x in stress.get("rate_labels", [r["label"] for r in rates]))
        stress_families = set(str(x) for x in stress.get("code_families", families))
        for n_text, p_map in weight_map.items():
            n = int(n_text)
            for p_key, weights in p_map.items():
                p_num, p_den = (int(x) for x in p_key.split("/"))
                for rate in rates:
                    rate_label = str(rate["label"])
                    if rate_label not in stress_rate_labels:
                        continue
                    k = _rate_to_k(n, rate_label, float(rate["target"]))
                    for family in families:
                        if family not in stress_families:
                            continue
                        code_seed = stable_seed(master_seed, "code", family, n, k)
                        stress_schedules = list(stress.get("alignment_schedules", schedules))
                        for alignment_schedule in stress_schedules:
                            for weight in weights:
                                for rep in range(reps):
                                    trial_index = int(weight) * reps + rep
                                    specs.append(
                                        {
                                            "trial_kind": "stress",
                                            "trial_index": trial_index,
                                            "trial_seed": stable_seed(master_seed, "stress", family, n, k, p_num, p_den, weight, rep),
                                            "code_seed": code_seed,
                                            "family": family,
                                            "alignment_schedule": alignment_schedule,
                                            "n": n,
                                            "k": k,
                                            "rate_label": rate_label,
                                            "p_num": p_num,
                                            "p_den": p_den,
                                            "forced_error_weight": int(weight),
                                            "max_histories": stress_cap,
                                            "run_exhaustive_ml": n <= int(config["pilot"]["exhaustive_ml_max_n"]),
                                        }
                                    )
    return specs


def run_bound_scan(config: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    scan_cfg = config["bound_scan"]
    master_seed = int(config["master_seed"])
    rows: list[dict[str, Any]] = []
    for n in scan_cfg["blocklengths"]:
        n = int(n)
        m = n - 1
        for p in scan_cfg["p_points"]:
            p_num, p_den = int(p["num"]), int(p["den"])
            if p_num != 1:
                raise ValueError("bound scan expects p numerator one")
            a = p_den - 1
            rng = random.Random(stable_seed(master_seed, "bound_scan", n, p_num, p_den))
            observations = [0, (1 << m) - 1]
            observations += [rng.getrandbits(m) for _ in range(int(scan_cfg["random_observations"]))]
            observations = list(dict.fromkeys(observations))
            schedules = list(scan_cfg.get("alignment_schedules", ["forward"]))
            for obs_index, y in enumerate(observations):
                for shell in scan_cfg["shells"]:
                    shell = int(shell)
                    if shell > m:
                        continue
                    for fraction in scan_cfg["advanced_fractions"]:
                        count = int(round(float(fraction) * n))
                        for alignment_schedule in schedules:
                            if alignment_schedule == "forward":
                                order = tuple(range(n))
                            elif alignment_schedule == "even_odd":
                                order = tuple(range(0, n, 2)) + tuple(range(1, n, 2))
                            else:
                                raise ValueError(f"unknown scan schedule {alignment_schedule}")
                            r = [shell] * n
                            for j in order[:min(count, n)]:
                                r[j] = min(n, shell + 1)
                            ind = independent_bound_int(r, n, a)
                            chain_started = time.perf_counter_ns()
                            chain = chain_relaxed_dp_int(y, r, n, a)
                            chain_elapsed = time.perf_counter_ns() - chain_started
                            started = time.perf_counter_ns()
                            ac = uac_dp_optimized_int(y, r, n, a)
                            elapsed = time.perf_counter_ns() - started
                            ratio = float("inf") if ac == 0 and ind > 0 else (ind / ac if ac > 0 else 1.0)
                            chain_ratio = float("inf") if chain == 0 and ind > 0 else (ind / chain if chain > 0 else 1.0)
                            rows.append(
                                {
                                    "n": n,
                                    "p_num": p_num,
                                    "p_den": p_den,
                                    "p_s": p_num / p_den,
                                    "alignment_schedule": alignment_schedule,
                                    "observation_index": obs_index,
                                    "observation_hex": hex(y),
                                    "shell": shell,
                                    "advanced_fraction": fraction,
                                    "advanced_count": count,
                                    "frontier": " ".join(str(v) for v in r),
                                    "independent_bound": ind,
                                    "chain_relaxed_bound": chain,
                                    "uac_bound": ac,
                                    "bound_ratio_ind_over_chain": chain_ratio,
                                    "bound_ratio_ind_over_ac": ratio,
                                    "bound_ratio_chain_over_ac": (chain / ac if ac > 0 else (float("inf") if chain > 0 else 1.0)),
                                    "chain_elapsed_ns": chain_elapsed,
                                    "uac_elapsed_ns": elapsed,
                                }
                            )
    write_csv(output_dir / "bound_scan.csv", rows)
    return rows


def run_pilot(config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = build_trial_specs(config)
    workers_cfg = int(config["pilot"].get("workers", 0))
    workers = workers_cfg if workers_cfg > 0 else max(1, min(4, (os.cpu_count() or 2) - 1))
    print(f"[pilot] paired trial count={len(specs)}; workers={workers}", flush=True)
    started = time.perf_counter_ns()
    rows: list[dict[str, Any]] = []

    if workers == 1:
        for idx, spec in enumerate(specs, start=1):
            rows.append(_run_trial(spec))
            if idx == 1 or idx % 20 == 0 or idx == len(specs):
                print(f"[pilot] completed {idx}/{len(specs)} paired trials", flush=True)
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_run_trial, spec): spec for spec in specs}
            for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                rows.append(future.result())
                if idx == 1 or idx % 20 == 0 or idx == len(specs):
                    print(f"[pilot] completed {idx}/{len(specs)} paired trials", flush=True)

    rows.sort(key=lambda row: (
        row["trial_kind"], int(row["n"]), str(row["rate_label"]), str(row["family"]), str(row["alignment_schedule"]),
        float(row["p_s"]), int(row["observed_error_weight"]), int(row["trial_index"])
    ))
    write_csv(output_dir / "paired_trials.csv", rows)
    print("[pilot] running alignment-bound structural scan", flush=True)
    bound_rows = run_bound_scan(config, output_dir)

    summary = {
        "phase": "Phase 2A bounded decoder pilot",
        "created_utc": utc_now_iso(),
        "status": "PASS" if not any(bool(row["disagreement"]) for row in rows) else "FAIL",
        "paired_trials": len(rows),
        "natural_trials": sum(row["trial_kind"] == "natural" for row in rows),
        "stress_trials": sum(row["trial_kind"] == "stress" for row in rows),
        "disagreements": sum(bool(row["disagreement"]) for row in rows),
        "independent_censored": sum(not bool(row["ind_complete"]) for row in rows),
        "chain_relaxed_censored": sum(not bool(row["cr_complete"]) for row in rows),
        "alignment_consistent_censored": sum(not bool(row["ac_complete"]) for row in rows),
        "exhaustive_ml_checks": sum(row["exhaustive_status"] != "NOT_RUN" for row in rows),
        "exhaustive_ml_failures": sum(row["exhaustive_status"] == "FAIL" for row in rows),
        "bound_scan_cases": len(bound_rows),
        "elapsed_ns": time.perf_counter_ns() - started,
        "workers": workers,
        "note": "This is a bounded Phase-2A screening pilot, not the final conference 99.9th-percentile campaign.",
    }
    write_json(output_dir / "pilot_summary.json", summary)
    return {"summary": summary, "rows": rows, "bound_rows": bound_rows}
