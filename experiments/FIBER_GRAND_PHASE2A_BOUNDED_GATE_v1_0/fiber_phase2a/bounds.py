from __future__ import annotations

from itertools import product
from typing import Sequence

from .model import bit_at, mismatch_vector_recurrence


def _validate_inputs(y: int, r: Sequence[int], n: int, a: int, weights: Sequence[int]) -> None:
    if n < 2:
        raise ValueError("n must be at least 2")
    if len(r) != n or len(weights) != n:
        raise ValueError("r/weights length mismatch")
    if a <= 1:
        raise ValueError("a must exceed 1")
    if y < 0 or y >= (1 << (n - 1)):
        raise ValueError("y is outside its n-1 bit range")
    if any(v < 0 or v > n for v in r):
        raise ValueError("each frontier shell must lie in 0..n")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be nonnegative")


def independent_bound_int(
    r: Sequence[int], n: int, a: int, weights: Sequence[int] | None = None
) -> int:
    if weights is None:
        weights = (1,) * n
    _validate_inputs(0, r, n, a, weights)
    m = n - 1
    return sum(int(weights[j]) * pow(a, m - rj) for j, rj in enumerate(r) if rj <= m)


def uac_bruteforce_int(
    y: int,
    r: Sequence[int],
    n: int,
    a: int,
    weights: Sequence[int] | None = None,
) -> int:
    """Independent exhaustive reference over all 2^n candidate words."""
    if weights is None:
        weights = (1,) * n
    _validate_inputs(y, r, n, a, weights)
    m = n - 1
    powers = [pow(a, m - d) for d in range(m + 1)]
    best = 0
    feasible = False
    for x in range(1 << n):
        dvec = mismatch_vector_recurrence(x, y, n)
        if all(dvec[j] >= r[j] for j in range(n)):
            feasible = True
            score = sum(int(weights[j]) * powers[dvec[j]] for j in range(n))
            if score > best:
                best = score
    return best if feasible else 0


def uac_dp_reference_int(
    y: int,
    r: Sequence[int],
    n: int,
    a: int,
    weights: Sequence[int] | None = None,
) -> int:
    """Literal four-coordinate O(n^4) reference DP from the Phase-1 audit.

    State (initial_d1, current_bit, current_d, accumulated_suffix_mismatches).
    It is intentionally kept structurally distinct from the optimized DP.
    """
    if weights is None:
        weights = (1,) * n
    _validate_inputs(y, r, n, a, weights)
    m = n - 1
    powers = [pow(a, m - d) for d in range(m + 1)]
    states: dict[tuple[int, int, int, int], int] = {}
    for initial in range(m + 1):
        if initial < r[0]:
            continue
        for b in (0, 1):
            states[(initial, b, initial, 0)] = int(weights[0]) * powers[initial]

    for j in range(n - 1):
        yj = bit_at(y, j)
        nxt: dict[tuple[int, int, int, int], int] = {}
        for (initial, b, d, h), score in states.items():
            for c in (0, 1):
                suffix_inc = int(c != yj)
                h2 = h + suffix_inc
                d2 = d - suffix_inc + int(b != yj)
                if not (0 <= d2 <= m) or d2 < r[j + 1]:
                    continue
                key = (initial, c, d2, h2)
                value = score + int(weights[j + 1]) * powers[d2]
                old = nxt.get(key)
                if old is None or value > old:
                    nxt[key] = value
        states = nxt
        if not states:
            return 0

    best = 0
    for (initial, _b, _d, h), score in states.items():
        if h == initial and score > best:
            best = score
    return best


def uac_dp_optimized_int(
    y: int,
    r: Sequence[int],
    n: int,
    a: int,
    weights: Sequence[int] | None = None,
) -> int:
    """Exact O(n^3)-time, O(n^2)-memory alignment-consistent DP.

    State (current_bit, current_d, remaining_suffix_mismatches).  At stage 1,
    both current_d and remaining equal the guessed d_1.  On selecting the next
    bit, remaining is decremented by its mismatch against the corresponding y
    coordinate.  The terminal condition remaining=0 enforces that the initial
    guess equals the actual suffix mismatch count.  The dropped initial-d_1
    coordinate is therefore redundant, improving the Phase-1 O(n^4) bound.
    """
    if weights is None:
        weights = (1,) * n
    _validate_inputs(y, r, n, a, weights)
    m = n - 1
    powers = [pow(a, m - d) for d in range(m + 1)]
    states: dict[tuple[int, int, int], int] = {}
    for initial in range(m + 1):
        if initial < r[0]:
            continue
        value = int(weights[0]) * powers[initial]
        states[(0, initial, initial)] = value
        states[(1, initial, initial)] = value

    for j in range(n - 1):
        yj = bit_at(y, j)
        nxt: dict[tuple[int, int, int], int] = {}
        for (b, d, remaining), score in states.items():
            for c in (0, 1):
                suffix_inc = int(c != yj)
                if suffix_inc > remaining:
                    continue
                remaining2 = remaining - suffix_inc
                d2 = d - suffix_inc + int(b != yj)
                if not (0 <= d2 <= m) or d2 < r[j + 1]:
                    continue
                key = (c, d2, remaining2)
                value = score + int(weights[j + 1]) * powers[d2]
                old = nxt.get(key)
                if old is None or value > old:
                    nxt[key] = value
        states = nxt
        if not states:
            return 0

    return max((score for (_b, _d, remaining), score in states.items() if remaining == 0), default=0)


def chain_relaxed_bruteforce_int(
    y: int,
    r: Sequence[int],
    n: int,
    a: int,
    weights: Sequence[int] | None = None,
) -> int:
    """Exhaustive reference for the recurrence-only relaxation.

    It enumerates x and an arbitrary initial mismatch count d_1 but does not
    enforce that this count equals the actual suffix mismatch count of x.
    """
    if weights is None:
        weights = (1,) * n
    _validate_inputs(y, r, n, a, weights)
    m = n - 1
    powers = [pow(a, m - d) for d in range(m + 1)]
    best = 0
    for x in range(1 << n):
        for initial in range(m + 1):
            if initial < r[0]:
                continue
            d = initial
            score = int(weights[0]) * powers[d]
            feasible = True
            for j in range(n - 1):
                yj = bit_at(y, j)
                d = d - int(bit_at(x, j + 1) != yj) + int(bit_at(x, j) != yj)
                if not (0 <= d <= m) or d < r[j + 1]:
                    feasible = False
                    break
                score += int(weights[j + 1]) * powers[d]
            if feasible and score > best:
                best = score
    return best


def chain_relaxed_dp_int(
    y: int,
    r: Sequence[int],
    n: int,
    a: int,
    weights: Sequence[int] | None = None,
) -> int:
    """Exact O(n^2)-time, O(n)-memory recurrence-only upper bound.

    This drops only the global closure condition linking the guessed d_1 to the
    actual suffix mismatches. Every real candidate remains feasible, hence the
    result upper-bounds U_AC. It is no larger than U_ind because every retained
    component respects its shell threshold.
    """
    if weights is None:
        weights = (1,) * n
    _validate_inputs(y, r, n, a, weights)
    m = n - 1
    powers = [pow(a, m - d) for d in range(m + 1)]
    # key=(current_bit,current_d)
    states: dict[tuple[int, int], int] = {}
    for d in range(m + 1):
        if d < r[0]:
            continue
        value = int(weights[0]) * powers[d]
        states[(0, d)] = value
        states[(1, d)] = value
    for j in range(n - 1):
        yj = bit_at(y, j)
        nxt: dict[tuple[int, int], int] = {}
        for (b, d), score in states.items():
            for c in (0, 1):
                d2 = d - int(c != yj) + int(b != yj)
                if not (0 <= d2 <= m) or d2 < r[j + 1]:
                    continue
                key = (c, d2)
                value = score + int(weights[j + 1]) * powers[d2]
                old = nxt.get(key)
                if old is None or value > old:
                    nxt[key] = value
        states = nxt
        if not states:
            return 0
    return max(states.values(), default=0)
