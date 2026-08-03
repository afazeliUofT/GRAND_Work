from __future__ import annotations

import random
import time
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Sequence

from .bounds import (
    chain_relaxed_bruteforce_int,
    chain_relaxed_dp_int,
    independent_bound_int,
    uac_bruteforce_int,
    uac_dp_optimized_int,
    uac_dp_reference_int,
)
from .codes import SetCode
from .model import (
    direct_best_path_scaled,
    likelihood_exhaustive_fraction,
    likelihood_fraction,
    mismatch_vector_direct,
    mismatch_vector_recurrence,
    scaled_score_int,
    strict_reversal_words,
)
from .search import masks_of_weight
from .model import insert_bit
from .util import stable_seed, utc_now_iso, write_json


@dataclass
class ValidationRecord:
    name: str
    status: str
    cases: int
    elapsed_ns: int
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "cases": self.cases,
            "elapsed_ns": self.elapsed_ns,
            "detail": self.detail,
        }


def _structured_frontiers(n: int, rng: random.Random, random_count: int) -> list[tuple[int, ...]]:
    m = n - 1
    vectors: list[tuple[int, ...]] = [
        (0,) * n,
        (1,) * n,
        (m,) * n,
        (n,) * n,
        tuple(i % min(3, n) for i in range(n)),
        tuple((i + 1) % min(3, n) for i in range(n)),
        tuple(1 if i % 2 else 0 for i in range(n)),
        tuple(min(m, i // max(1, n // 3)) for i in range(n)),
    ]
    for _ in range(random_count):
        vectors.append(tuple(rng.randrange(0, n + 1) for _ in range(n)))
    # Deduplicate while preserving order.
    return list(dict.fromkeys(vectors))


def validate_likelihood_and_recurrence() -> ValidationRecord:
    started = time.perf_counter_ns()
    cases = 0
    p = Fraction(1, 5)
    for n in range(2, 7):
        q = [Fraction(1, n)] * n
        for x in range(1 << n):
            for y in range(1 << (n - 1)):
                direct = mismatch_vector_direct(x, y, n)
                recurrence = mismatch_vector_recurrence(x, y, n)
                if direct != recurrence:
                    raise AssertionError(("recurrence", n, x, y, direct, recurrence))
                formula = likelihood_fraction(x, y, n, p, q)
                exhaustive = likelihood_exhaustive_fraction(x, y, n, p, q)
                if formula != exhaustive:
                    raise AssertionError(("likelihood", n, x, y, formula, exhaustive))
                cases += 1
    return ValidationRecord(
        name="likelihood_recurrence_vs_explicit_channel",
        status="PASS",
        cases=cases,
        elapsed_ns=time.perf_counter_ns() - started,
        detail={"arithmetic": "fractions.Fraction", "p": "1/5", "n": "2..6"},
    )


def validate_strict_reversal() -> ValidationRecord:
    started = time.perf_counter_ns()
    cases = 0
    a_values = [3, 4, 9, 19, 49, 99]  # p=1/(a+1)
    for a in a_values:
        p = Fraction(1, a + 1)
        for n in range(4, 181):
            y, x_a, x_b = strict_reversal_words(n)
            d_a = mismatch_vector_recurrence(x_a, y, n)
            d_b = mismatch_vector_recurrence(x_b, y, n)
            expected_a = (3,) * (n - 3) + (2, 1, 0)
            if d_a != expected_a or d_b != (1,) * n:
                raise AssertionError(("strict_family_multiplicity", a, n, d_a, d_b))
            score_a = scaled_score_int(x_a, y, n, a)
            score_b = scaled_score_int(x_b, y, n, a)
            path_a = direct_best_path_scaled(x_a, y, n, a)
            path_b = direct_best_path_scaled(x_b, y, n, a)
            if not path_a > path_b:
                raise AssertionError(("best_path_not_strict", a, n, path_a, path_b))
            condition = n * p > 1 + 2 * p * p
            if (score_b > score_a) != condition:
                raise AssertionError(("aggregate_condition", a, n, score_a, score_b, condition))
            cases += 1
    return ValidationRecord(
        name="strict_reversal_family",
        status="PASS",
        cases=cases,
        elapsed_ns=time.perf_counter_ns() - started,
        detail={"a_values": a_values, "n": "4..180", "condition": "n p > 1+2p^2"},
    )


def validate_uac_dps(master_seed: int) -> ValidationRecord:
    started = time.perf_counter_ns()
    rng = random.Random(stable_seed(master_seed, "uac_validation"))
    cases = 0
    by_n: dict[str, int] = {}

    # Every observation through n=8, with structured and random frontier vectors.
    for n in range(2, 9):
        weights = tuple(range(1, n + 1))  # nonuniform positive deletion weights
        vectors = _structured_frontiers(n, rng, random_count=6)
        count_n = 0
        for y in range(1 << (n - 1)):
            for r in vectors:
                brute = uac_bruteforce_int(y, r, n, 4, weights)
                reference = uac_dp_reference_int(y, r, n, 4, weights)
                optimized = uac_dp_optimized_int(y, r, n, 4, weights)
                chain_brute = chain_relaxed_bruteforce_int(y, r, n, 4, weights)
                chain = chain_relaxed_dp_int(y, r, n, 4, weights)
                independent = independent_bound_int(r, n, 4, weights)
                if not (brute == reference == optimized):
                    raise AssertionError(("uac_disagreement", n, y, r, brute, reference, optimized))
                if chain_brute != chain:
                    raise AssertionError(("chain_disagreement", n, y, r, chain_brute, chain))
                if not optimized <= chain <= independent:
                    raise AssertionError(("bound_hierarchy", n, y, r, optimized, chain, independent))
                cases += 1
                count_n += 1
        by_n[str(n)] = count_n

    # n=9,10: broad deterministic sample, including all-zero/all-one observations.
    for n in (9, 10):
        weights = tuple(1 + ((3 * j + 1) % 7) for j in range(n))
        y_space = list(range(1 << (n - 1)))
        chosen = {0, (1 << (n - 1)) - 1}
        sample_count = min(48, len(y_space))
        chosen.update(rng.sample(y_space, sample_count))
        vectors = _structured_frontiers(n, rng, random_count=10)
        count_n = 0
        for y in sorted(chosen):
            for r in vectors:
                brute = uac_bruteforce_int(y, r, n, 19, weights)
                reference = uac_dp_reference_int(y, r, n, 19, weights)
                optimized = uac_dp_optimized_int(y, r, n, 19, weights)
                chain_brute = chain_relaxed_bruteforce_int(y, r, n, 19, weights)
                chain = chain_relaxed_dp_int(y, r, n, 19, weights)
                independent = independent_bound_int(r, n, 19, weights)
                if not (brute == reference == optimized):
                    raise AssertionError(("uac_disagreement", n, y, r, brute, reference, optimized))
                if chain_brute != chain:
                    raise AssertionError(("chain_disagreement", n, y, r, chain_brute, chain))
                if not optimized <= chain <= independent:
                    raise AssertionError(("bound_hierarchy", n, y, r, optimized, chain, independent))
                cases += 1
                count_n += 1
        by_n[str(n)] = count_n

    return ValidationRecord(
        name="uac_and_chain_bounds_vs_independent_references",
        status="PASS",
        cases=cases,
        elapsed_ns=time.perf_counter_ns() - started,
        detail={
            "all_observations": "n=2..8",
            "sampled_observations": "n=9,10 (at least 48 plus extremes)",
            "deletion_weights": "nonuniform positive integers",
            "reference_dp": "four-coordinate O(n^4)",
            "optimized_dp": "three-coordinate O(n^3)",
            "chain_relaxation": "brute force versus O(n^2) DP; U_AC <= U_CR <= U_ind",
            "cases_by_n": by_n,
        },
    )


def _small_world_events(
    n: int, y: int, a: int, alignment_schedule: str
) -> tuple[list[tuple[str, int | tuple[int, ...]]], dict[int, int], dict[tuple[int, ...], tuple[int, int, int]]]:
    """Complete event trace and precomputed bounds for n<=4 validation."""
    if alignment_schedule == "forward":
        alignment_order = tuple(range(n))
    elif alignment_schedule == "even_odd":
        alignment_order = tuple(range(0, n, 2)) + tuple(range(1, n, 2))
    else:
        raise ValueError("unknown alignment schedule")
    m = n - 1
    frontier = [0] * n
    seen: set[int] = set()
    events: list[tuple[str, int | tuple[int, ...]]] = []
    frontier_states: set[tuple[int, ...]] = {tuple(frontier)}
    scores = {x: scaled_score_int(x, y, n, a) for x in range(1 << n)}

    for shell in range(m + 1):
        masks = masks_of_weight(m, shell)
        last_index = len(masks) - 1
        for mask_index, error_mask in enumerate(masks):
            altered = y ^ error_mask
            for b in (0, 1):
                last_local = mask_index == last_index and b == 1
                for j in alignment_order:
                    x = insert_bit(altered, j, b)
                    if x not in seen:
                        seen.add(x)
                        events.append(("candidate", x))
                    if last_local:
                        frontier[j] = shell + 1
                        state = tuple(frontier)
                        frontier_states.add(state)
                        events.append(("frontier", state))
    if len(seen) != 1 << n:
        raise AssertionError(("incomplete_small_world_trace", n, y, len(seen)))
    bounds = {
        state: (
            independent_bound_int(state, n, a),
            chain_relaxed_dp_int(y, state, n, a),
            uac_dp_optimized_int(y, state, n, a),
        )
        for state in frontier_states
    }
    return events, scores, bounds


def _simulate_codebook_mask(
    codebook_mask: int,
    events: Sequence[tuple[str, int | tuple[int, ...]]],
    scores: dict[int, int],
    bounds: dict[tuple[int, ...], tuple[int, int, int]],
    n: int,
    mode_index: int,
) -> tuple[int, int]:
    frontier = (0,) * n
    incumbent = -1
    tie_mask = 0
    for kind, payload in events:
        if kind == "candidate":
            x = int(payload)
            if (codebook_mask >> x) & 1:
                score = scores[x]
                if score > incumbent:
                    incumbent = score
                    tie_mask = 1 << x
                elif score == incumbent:
                    tie_mask |= 1 << x
                if incumbent > bounds[frontier][mode_index]:
                    return incumbent, tie_mask
        else:
            frontier = tuple(payload)  # type: ignore[arg-type]
            if incumbent >= 0 and incumbent > bounds[frontier][mode_index]:
                return incumbent, tie_mask
    return incumbent, tie_mask


def validate_all_codebooks_n_le_4() -> ValidationRecord:
    started = time.perf_counter_ns()
    cases = 0
    a = 4  # p=1/5
    by_n: dict[str, int] = {}
    for n in range(2, 5):
        words = 1 << n
        count_n = 0
        for y in range(1 << (n - 1)):
            for alignment_schedule in ("forward", "even_odd"):
                events, scores, bounds = _small_world_events(n, y, a, alignment_schedule)
                for codebook_mask in range(1, 1 << words):
                    best = max(scores[x] for x in range(words) if (codebook_mask >> x) & 1)
                    expected_ties = 0
                    for x in range(words):
                        if ((codebook_mask >> x) & 1) and scores[x] == best:
                            expected_ties |= 1 << x
                    for mode_index in (0, 1, 2):
                        got_score, got_ties = _simulate_codebook_mask(
                            codebook_mask, events, scores, bounds, n, mode_index
                        )
                        if got_score != best or got_ties != expected_ties:
                            raise AssertionError(
                                ("small_world_decoder", alignment_schedule, n, y, codebook_mask, mode_index, best, expected_ties, got_score, got_ties)
                            )
                    cases += 1
                    count_n += 1
        by_n[str(n)] = count_n
    return ValidationRecord(
        name="all_nonempty_codebooks_n_le_4_all_observations",
        status="PASS",
        cases=cases,
        elapsed_ns=time.perf_counter_ns() - started,
        detail={
            "a": a, "p": "1/5", "cases_by_n": by_n,
            "bound_modes": ["independent", "chain_relaxed", "alignment_consistent"],
            "alignment_schedules": ["forward", "even_odd"],
        },
    )


def run_validation(output_dir: Path, master_seed: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter_ns()
    records: list[ValidationRecord] = []
    checks = [
        validate_likelihood_and_recurrence,
        validate_strict_reversal,
        lambda: validate_uac_dps(master_seed),
        validate_all_codebooks_n_le_4,
    ]
    try:
        for check in checks:
            record = check()
            records.append(record)
            print(f"[validation] {record.name}: {record.status} ({record.cases} cases)", flush=True)
        status = "PASS"
        error = None
    except Exception as exc:
        status = "FAIL"
        error = repr(exc)
        records.append(
            ValidationRecord(
                name=getattr(check, "__name__", "unknown_check"),
                status="FAIL",
                cases=0,
                elapsed_ns=0,
                detail={"exception": repr(exc)},
            )
        )

    summary = {
        "phase": "Phase 2A exact validation",
        "status": status,
        "created_utc": utc_now_iso(),
        "master_seed": master_seed,
        "elapsed_ns": time.perf_counter_ns() - started,
        "records": [record.to_dict() for record in records],
        "error": error,
        "scope_note": "This closes the Phase-2A arithmetic/DP gate and all codebooks through n=4; it is not the final full Gate-P3 campaign through n=16.",
    }
    write_json(output_dir / "exact_validation_summary.json", summary)
    log_lines = [
        f"PHASE2A_EXACT_VALIDATION={status}",
        f"MASTER_SEED={master_seed}",
        f"TOTAL_ELAPSED_NS={summary['elapsed_ns']}",
    ]
    for record in records:
        log_lines.append(f"{record.name.upper()}={record.status};CASES={record.cases};ELAPSED_NS={record.elapsed_ns}")
    if error:
        log_lines.append(f"ERROR={error}")
    (output_dir / "exact_validation.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return summary
