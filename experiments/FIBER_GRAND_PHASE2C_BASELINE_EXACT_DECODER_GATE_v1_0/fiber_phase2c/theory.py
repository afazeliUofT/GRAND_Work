from __future__ import annotations

import math
from functools import lru_cache
from itertools import combinations
from typing import Iterable


def bit_at(word: int, index: int) -> int:
    return (word >> index) & 1


def delete_bit(word: int, index: int) -> int:
    low_mask = (1 << index) - 1
    return (word & low_mask) | ((word >> (index + 1)) << index)


def insert_bit(word: int, index: int, bit: int) -> int:
    if bit not in (0, 1):
        raise ValueError("bit must be 0 or 1")
    low_mask = (1 << index) - 1
    return (word & low_mask) | (bit << index) | ((word >> index) << (index + 1))


def mismatch_vector(x: int, y: int, n: int) -> tuple[int, ...]:
    if n < 2:
        raise ValueError("n must be at least two")
    d = ((x >> 1) ^ y).bit_count()
    out = [d]
    for j in range(n - 1):
        yj = bit_at(y, j)
        d -= bit_at(x, j + 1) != yj
        d += bit_at(x, j) != yj
        out.append(int(d))
    return tuple(out)


def exact_scaled_score(x: int, y: int, n: int, odds_denominator: int) -> int:
    m = n - 1
    return sum(pow(odds_denominator, m - d) for d in mismatch_vector(x, y, n))


def distinct_binary_supersequences(z: int, m: int) -> tuple[int, ...]:
    """Exactly the m+2 distinct binary length-(m+1) one-insertion supersequences."""
    out: list[int] = []
    for b in (0, 1):
        out.append(insert_bit(z, 0, b))
        for gap in range(1, m + 1):
            if bit_at(z, gap - 1) != b:
                out.append(insert_bit(z, gap, b))
    if len(out) != m + 2 or len(set(out)) != m + 2:
        raise AssertionError("insertion-sphere generation invariant failed")
    return tuple(out)


@lru_cache(maxsize=None)
def masks_of_weight(length: int, weight: int) -> tuple[int, ...]:
    if weight < 0 or weight > length:
        return ()
    out: list[int] = []
    for positions in combinations(range(length), weight):
        mask = 0
        for pos in positions:
            mask |= 1 << pos
        out.append(mask)
    return tuple(out)


def discovery_shell(x: int, y: int, n: int) -> int:
    return min(mismatch_vector(x, y, n))


def shell_candidate_set(y: int, n: int, max_shell: int) -> set[int]:
    m = n - 1
    out: set[int] = set()
    for weight in range(min(max_shell, m) + 1):
        for error in masks_of_weight(m, weight):
            z = y ^ error
            out.update(distinct_binary_supersequences(z, m))
    return out


def hamming_ball_volume(length: int, radius: int) -> int:
    if radius < 0:
        return 0
    return sum(math.comb(length, w) for w in range(min(radius, length) + 1))


def shell_bound_scaled(n: int, odds_denominator: int, completed_shell: int) -> int:
    m = n - 1
    if completed_shell >= m:
        return 0
    return n * pow(odds_denominator, m - completed_shell - 1)


def stopping_offset_uniform(n: int, p_num: int, p_den: int) -> int:
    if not (0 <= p_num * 2 < p_den):
        raise ValueError("require 0<=p<1/2")
    if p_num == 0:
        return 1
    # rho=p/(1-p)=p_num/(p_den-p_num); find the first ell with rho^ell < 1/n.
    numerator = p_num
    denominator = p_den - p_num
    ell = 1
    while n * pow(numerator, ell) >= pow(denominator, ell):
        ell += 1
    return ell


def realization_shell_cap(n: int, p_num: int, p_den: int, surviving_error_weight: int) -> int:
    return min(n - 1, surviving_error_weight + stopping_offset_uniform(n, p_num, p_den) - 1)


def generated_attempt_cap(n: int, stop_shell: int, deduplicated: bool) -> int:
    factor = n + 1 if deduplicated else 2 * n
    return factor * hamming_ball_volume(n - 1, stop_shell)


def membership_query_cap(n: int, stop_shell: int) -> int:
    return generated_attempt_cap(n, stop_shell, True)


def binomial_pmf(m: int, p_num: int, p_den: int, t: int) -> float:
    p = p_num / p_den
    return math.comb(m, t) * p**t * (1 - p) ** (m - t)


def exact_expected_membership_cap(n: int, p_num: int, p_den: int) -> float:
    m = n - 1
    return sum(
        binomial_pmf(m, p_num, p_den, t)
        * membership_query_cap(n, realization_shell_cap(n, p_num, p_den, t))
        for t in range(m + 1)
    )


def binomial_upper_quantile(m: int, p_num: int, p_den: int, delta: float) -> int:
    """Smallest tau with P[T<=tau] >= 1-delta."""
    if not 0 < delta < 1:
        raise ValueError("delta must lie in (0,1)")
    cumulative = 0.0
    for t in range(m + 1):
        cumulative += binomial_pmf(m, p_num, p_den, t)
        if cumulative >= 1 - delta:
            return t
    return m


def binary_entropy(p: float) -> float:
    if p <= 0 or p >= 1:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)
