from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Iterable, Sequence


def bit_at(word: int, index: int) -> int:
    return (word >> index) & 1


def delete_bit(word: int, index: int) -> int:
    low_mask = (1 << index) - 1
    low = word & low_mask
    high = word >> (index + 1)
    return low | (high << index)


def insert_bit(word: int, index: int, bit: int) -> int:
    if bit not in (0, 1):
        raise ValueError("bit must be 0 or 1")
    low_mask = (1 << index) - 1
    low = word & low_mask
    high = word >> index
    return low | (bit << index) | (high << (index + 1))


def mismatch_vector_direct(x: int, y: int, n: int) -> tuple[int, ...]:
    if n < 2:
        raise ValueError("n must be at least 2")
    return tuple((delete_bit(x, j) ^ y).bit_count() for j in range(n))


def mismatch_vector_recurrence(x: int, y: int, n: int) -> tuple[int, ...]:
    if n < 2:
        raise ValueError("n must be at least 2")
    d = ((x >> 1) ^ y).bit_count()  # delete coordinate 0
    out = [d]
    for j in range(n - 1):
        yj = bit_at(y, j)
        d = d - (bit_at(x, j + 1) != yj) + (bit_at(x, j) != yj)
        out.append(int(d))
    return tuple(out)


def scaled_score_int(
    x: int,
    y: int,
    n: int,
    odds_denominator: int,
    weights: Sequence[int] | None = None,
) -> int:
    """Exact positive integer proportional to W(y|x).

    For p=1/(a+1), a=odds_denominator, and deletion weights q_j
    proportional to positive integers weights[j], the true likelihood is a
    common positive factor times sum_j weights[j] * a^(n-1-d_j).
    """
    if odds_denominator <= 1:
        raise ValueError("odds_denominator must exceed one (p<1/2)")
    if weights is None:
        weights = (1,) * n
    if len(weights) != n:
        raise ValueError("weights length mismatch")
    m = n - 1
    dvec = mismatch_vector_recurrence(x, y, n)
    return sum(int(weights[j]) * pow(odds_denominator, m - dvec[j]) for j in range(n))


def likelihood_fraction(
    x: int,
    y: int,
    n: int,
    p: Fraction,
    q: Sequence[Fraction] | None = None,
) -> Fraction:
    if q is None:
        q = [Fraction(1, n)] * n
    one = Fraction(1)
    m = n - 1
    return sum(q[j] * p ** d * (one - p) ** (m - d) for j, d in enumerate(mismatch_vector_recurrence(x, y, n)))


def likelihood_exhaustive_fraction(
    x: int,
    y: int,
    n: int,
    p: Fraction,
    q: Sequence[Fraction] | None = None,
) -> Fraction:
    if q is None:
        q = [Fraction(1, n)] * n
    one = Fraction(1)
    total = Fraction(0)
    for error_word in range(1 << n):
        wt = error_word.bit_count()
        prob = p ** wt * (one - p) ** (n - wt)
        corrupted = x ^ error_word
        for j in range(n):
            if delete_bit(corrupted, j) == y:
                total += q[j] * prob
    return total


def word_to_bits(word: int, n: int) -> str:
    """Coordinates 0..n-1 are displayed left to right."""
    return "".join(str(bit_at(word, i)) for i in range(n))


def bits_to_word(bits: str) -> int:
    out = 0
    for i, ch in enumerate(bits.strip()):
        if ch not in "01":
            raise ValueError("bits must contain only 0/1")
        out |= (int(ch) << i)
    return out


def strict_reversal_words(n: int) -> tuple[int, int, int]:
    """Return y, x_A, x_B using coordinate order displayed left-to-right."""
    if n < 4:
        raise ValueError("strict family requires n>=4")
    y = bits_to_word("0" * (n - 3) + "10")
    x_a = bits_to_word("0" * (n - 3) + "101")
    x_b = 0
    return y, x_a, x_b


def direct_best_path_scaled(x: int, y: int, n: int, a: int, weights: Sequence[int] | None = None) -> int:
    if weights is None:
        weights = (1,) * n
    m = n - 1
    return max(int(weights[j]) * pow(a, m - d) for j, d in enumerate(mismatch_vector_recurrence(x, y, n)))
