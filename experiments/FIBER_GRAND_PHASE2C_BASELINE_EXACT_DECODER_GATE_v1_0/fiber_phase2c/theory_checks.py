from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

from .theory import (
    delete_bit,
    discovery_shell,
    distinct_binary_supersequences,
    exact_scaled_score,
    generated_attempt_cap,
    hamming_ball_volume,
    insert_bit,
    masks_of_weight,
    mismatch_vector,
    realization_shell_cap,
    shell_bound_scaled,
    shell_candidate_set,
    stopping_offset_uniform,
)
from .util import stable_seed, utc_now_iso, write_json


def run_theory_checks(output_dir: Path, master_seed: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter_ns()
    records: list[dict[str, Any]] = []

    # 1. Exact binary single-insertion sphere cardinality and constructive enumeration.
    cases = 0
    for m in range(0, 11):
        for z in range(1 << m):
            constructive = set(distinct_binary_supersequences(z, m))
            brute = {insert_bit(z, j, b) for j in range(m + 1) for b in (0, 1)}
            if constructive != brute or len(brute) != m + 2:
                raise AssertionError(("insertion_sphere", m, z, len(constructive), len(brute)))
            cases += 1
    records.append({"name": "binary_one_insertion_sphere", "status": "PASS", "cases": cases})

    # 2. Discovery-shell characterization D_s={x:min_j d_j<=s}.
    cases = 0
    for n in range(2, 9):
        for y in range(1 << (n - 1)):
            accumulated: set[int] = set()
            for s in range(n):
                for e in masks_of_weight(n - 1, s):
                    accumulated.update(distinct_binary_supersequences(y ^ e, n - 1))
                expected = {x for x in range(1 << n) if discovery_shell(x, y, n) <= s}
                if accumulated != expected:
                    raise AssertionError(("discovery_shell", n, y, s, len(accumulated), len(expected)))
                cases += 1
    records.append({"name": "discovery_shell_characterization", "status": "PASS", "cases": cases})

    # 3. Shell threshold upper-bounds every completely undiscovered candidate.
    cases = 0
    for n in range(2, 9):
        m = n - 1
        for a in (2, 4, 9, 19, 99):
            for y in (0, (1 << m) - 1, stable_seed(master_seed, "y", n, a) & ((1 << m) - 1)):
                for s in range(m):
                    discovered = shell_candidate_set(y, n, s)
                    unseen_scores = [exact_scaled_score(x, y, n, a) for x in range(1 << n) if x not in discovered]
                    maximum = max(unseen_scores, default=0)
                    bound = shell_bound_scaled(n, a, s)
                    if maximum > bound:
                        raise AssertionError(("shell_bound", n, a, y, s, maximum, bound))
                    cases += 1
    records.append({"name": "shell_certificate_against_exhaustive_unseen_max", "status": "PASS", "cases": cases})

    # 4. Realization-dependent stopping theorem, exhaustively over small channel histories.
    cases = 0
    for n in range(2, 9):
        m = n - 1
        for p_num, p_den in ((0, 1), (1, 100), (1, 20), (1, 10), (1, 5)):
            if 2 * p_num >= p_den:
                continue
            a = 1 if p_num == 0 else (p_den - p_num) // p_num
            for x in range(1 << n):
                for j in range(n):
                    deleted = delete_bit(x, j)
                    t_values = (0,) if p_num == 0 else range(min(m, 3) + 1)
                    for t in t_values:
                        for error in masks_of_weight(m, t)[: min(8, len(masks_of_weight(m, t)))]:
                            y = deleted ^ error
                            cap = realization_shell_cap(n, p_num, p_den, t)
                            if p_num == 0:
                                # At p=0 the transmitted score is nonzero and shell-zero bound after completion is zero.
                                if cap != 0:
                                    raise AssertionError(("zero_p_cap", n, cap))
                            else:
                                incumbent = exact_scaled_score(x, y, n, a)
                                bound = shell_bound_scaled(n, a, cap)
                                if not incumbent > bound:
                                    raise AssertionError(("realization_cap", n, p_num, p_den, x, j, t, cap, incumbent, bound))
                            cases += 1
    records.append({"name": "realization_dependent_stopping_shell", "status": "PASS", "cases": cases})

    # 5. Closed-form work caps and offset arithmetic across the frozen finite-length range.
    cases = 0
    for n in range(2, 64):
        for p_num, p_den in ((0, 1), (1, 100), (1, 50), (1, 20), (1, 10)):
            if 2 * p_num >= p_den:
                continue
            ell = stopping_offset_uniform(n, p_num, p_den)
            if ell < 1:
                raise AssertionError(("bad_offset", n, p_num, p_den, ell))
            for t in range(min(n, 8)):
                cap = realization_shell_cap(n, p_num, p_den, t)
                if generated_attempt_cap(n, cap, True) > generated_attempt_cap(n, cap, False):
                    raise AssertionError(("dedup_cap", n, cap))
                if hamming_ball_volume(n - 1, cap) <= 0:
                    raise AssertionError(("ball_volume", n, cap))
                cases += 1
    records.append({"name": "finite_length_work_cap_arithmetic", "status": "PASS", "cases": cases})

    summary = {
        "phase": "Phase 2C theorem-support validation",
        "created_utc": utc_now_iso(),
        "status": "PASS",
        "exact_cases": sum(int(r["cases"]) for r in records),
        "records": records,
        "elapsed_ns": time.perf_counter_ns() - started,
        "scope_note": "These exact checks support the proof source; they do not replace an independent mathematical or novelty review.",
    }
    write_json(output_dir / "THEORY_CHECKS.json", summary)
    return summary
