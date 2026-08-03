from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class LinearCodeSpec:
    n: int
    k: int
    family: str
    construction: str
    generator_rows: tuple[int, ...]
    parity_check_rows: tuple[int, ...]
    code_seed: int

    def __post_init__(self) -> None:
        if not 1 <= self.k < self.n <= 63:
            raise ValueError("require 1<=k<n<=63")
        if len(self.generator_rows) != self.k:
            raise ValueError("generator row count mismatch")
        if len(self.parity_check_rows) != self.n - self.k:
            raise ValueError("parity-check row count mismatch")
        limit = 1 << self.n
        if any(row < 0 or row >= limit for row in self.generator_rows + self.parity_check_rows):
            raise ValueError("row outside blocklength")
        if self.rank(self.generator_rows, self.n) != self.k:
            raise ValueError("generator rows are not independent")
        if self.rank(self.parity_check_rows, self.n) != self.n - self.k:
            raise ValueError("parity-check rows are not independent")
        for grow in self.generator_rows:
            if any(((grow & hrow).bit_count() & 1) for hrow in self.parity_check_rows):
                raise ValueError("G H^T != 0")

    @staticmethod
    def rank(rows: Sequence[int], n: int) -> int:
        work = [int(x) for x in rows if x]
        rank = 0
        for col in range(n - 1, -1, -1):
            pivot = next((i for i in range(rank, len(work)) if (work[i] >> col) & 1), None)
            if pivot is None:
                continue
            work[rank], work[pivot] = work[pivot], work[rank]
            for i in range(len(work)):
                if i != rank and ((work[i] >> col) & 1):
                    work[i] ^= work[rank]
            rank += 1
            if rank == len(work):
                break
        return rank

    def encode(self, message: int) -> int:
        if message < 0 or message >= (1 << self.k):
            raise ValueError("message outside range")
        out = 0
        m = message
        i = 0
        while m:
            if m & 1:
                out ^= self.generator_rows[i]
            i += 1
            m >>= 1
        return out

    def is_codeword(self, word: int) -> bool:
        if word < 0 or word >= (1 << self.n):
            return False
        return all(((word & row).bit_count() & 1) == 0 for row in self.parity_check_rows)

    def metadata(self) -> dict[str, object]:
        return {
            "n": self.n,
            "k": self.k,
            "rate": self.k / self.n,
            "family": self.family,
            "construction": self.construction,
            "code_seed": self.code_seed,
            "generator_rows_hex": [hex(x) for x in self.generator_rows],
            "parity_check_rows_hex": [hex(x) for x in self.parity_check_rows],
        }


def _systematic_from_parity_map(
    *, n: int, k: int, parity_rows_on_message: Sequence[int], family: str, construction: str, seed: int
) -> LinearCodeSpec:
    r = n - k
    if len(parity_rows_on_message) != r:
        raise ValueError("parity row count mismatch")
    if any(row < 0 or row >= (1 << k) for row in parity_rows_on_message):
        raise ValueError("parity row outside message range")

    # Each check is <row_i, message> + parity_i = 0.
    hrows = tuple(int(row) | (1 << (k + i)) for i, row in enumerate(parity_rows_on_message))
    grows: list[int] = []
    for message_index in range(k):
        row = 1 << message_index
        for parity_index, mask in enumerate(parity_rows_on_message):
            if (mask >> message_index) & 1:
                row |= 1 << (k + parity_index)
        grows.append(row)
    return LinearCodeSpec(
        n=n,
        k=k,
        family=family,
        construction=construction,
        generator_rows=tuple(grows),
        parity_check_rows=hrows,
        code_seed=seed,
    )


def random_systematic_code(n: int, k: int, seed: int) -> LinearCodeSpec:
    rng = random.Random(seed)
    rows: list[int] = []
    for i in range(n - k):
        mask = rng.getrandbits(k)
        if mask == 0:
            mask = 1 << (i % k)
        rows.append(mask)
    return _systematic_from_parity_map(
        n=n,
        k=k,
        parity_rows_on_message=rows,
        family="random_systematic_linear",
        construction=f"dense systematic parity map; seed={seed}",
        seed=seed,
    )


CRC_POLYNOMIALS: dict[int, int] = {
    4: (1 << 4) | (1 << 1) | 1,               # x^4+x+1
    5: (1 << 5) | (1 << 2) | 1,               # x^5+x^2+1
    6: (1 << 6) | (1 << 1) | 1,               # x^6+x+1
    8: (1 << 8) | (1 << 2) | (1 << 1) | 1,    # x^8+x^2+x+1
    11: (1 << 11) | (1 << 2) | 1,             # x^11+x^2+1
}


def _poly_mod(value: int, polynomial: int) -> int:
    degree = polynomial.bit_length() - 1
    while value and value.bit_length() - 1 >= degree:
        value ^= polynomial << ((value.bit_length() - 1) - degree)
    return value


def crc_systematic_code(n: int, k: int) -> LinearCodeSpec:
    r = n - k
    if r not in CRC_POLYNOMIALS:
        raise ValueError(f"no frozen CRC polynomial for redundancy {r}")
    poly = CRC_POLYNOMIALS[r]
    parity_rows = [0] * r
    for message_index in range(k):
        shifted = (1 << message_index) << r
        remainder = _poly_mod(shifted, poly)
        for parity_index in range(r):
            if (remainder >> parity_index) & 1:
                parity_rows[parity_index] |= 1 << message_index
    return _systematic_from_parity_map(
        n=n,
        k=k,
        parity_rows_on_message=parity_rows,
        family="crc_defined_linear",
        construction=f"systematic cyclic code from degree-{r} polynomial {hex(poly)}",
        seed=0,
    )


def _solve_binary_square(columns: Sequence[int], rhs: int, dimension: int) -> int:
    """Solve A x = rhs, where columns[j] is column j of A as a bit vector."""
    # Convert to augmented row equations.
    rows: list[int] = []
    for equation in range(dimension):
        coeff = 0
        for j, col in enumerate(columns):
            if (col >> equation) & 1:
                coeff |= 1 << j
        rows.append(coeff | (((rhs >> equation) & 1) << dimension))

    pivot_row = 0
    for col in range(dimension):
        pivot = next((r for r in range(pivot_row, dimension) if (rows[r] >> col) & 1), None)
        if pivot is None:
            raise ValueError("singular binary system")
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(dimension):
            if r != pivot_row and ((rows[r] >> col) & 1):
                rows[r] ^= rows[pivot_row]
        pivot_row += 1

    solution = 0
    for row in rows:
        coeff = row & ((1 << dimension) - 1)
        pivot_col = (coeff & -coeff).bit_length() - 1
        if (row >> dimension) & 1:
            solution |= 1 << pivot_col
    return solution


def extended_hamming_code(n: int) -> LinearCodeSpec:
    if n not in (16, 32):
        raise ValueError("Phase 2C freezes extended Hamming to n=16 or n=32")
    r = int(math.log2(n))
    if 1 << r != n:
        raise ValueError("n must be a power of two")
    k = n - r - 1

    # Standard extended-Hamming parity-check columns: (binary index, 1).
    columns = [index | (1 << r) for index in range(n)]
    parity_positions = [0] + [1 << i for i in range(r)]
    data_positions = [i for i in range(n) if i not in set(parity_positions)]
    if len(data_positions) != k:
        raise AssertionError("bad extended-Hamming partition")
    parity_columns = [columns[p] for p in parity_positions]

    generator_rows: list[int] = []
    for pos in data_positions:
        rhs = columns[pos]  # parity contribution must equal the data column over GF(2)
        coeffs = _solve_binary_square(parity_columns, rhs, r + 1)
        word = 1 << pos
        for j, parity_pos in enumerate(parity_positions):
            if (coeffs >> j) & 1:
                word |= 1 << parity_pos
        generator_rows.append(word)

    hrows: list[int] = []
    for equation in range(r + 1):
        row = 0
        for pos, col in enumerate(columns):
            if (col >> equation) & 1:
                row |= 1 << pos
        hrows.append(row)

    code = LinearCodeSpec(
        n=n,
        k=k,
        family="extended_hamming",
        construction=f"standard extended Hamming [{n},{k},4] with systematic data-position basis",
        generator_rows=tuple(generator_rows),
        parity_check_rows=tuple(hrows),
        code_seed=0,
    )

    # Verify the advertised minimum distance by basis/small combinations where feasible.
    minimum = n + 1
    if k <= 16:
        for message in range(1, 1 << k):
            minimum = min(minimum, code.encode(message).bit_count())
    else:
        # The standard construction has d=4; still check all generator rows and all pairs.
        for i, row in enumerate(code.generator_rows):
            minimum = min(minimum, row.bit_count())
            for row2 in code.generator_rows[i + 1 :]:
                minimum = min(minimum, (row ^ row2).bit_count())
    if minimum < 4:
        raise AssertionError(f"extended Hamming minimum-distance check failed: {minimum}")
    return code


def build_code(family: str, n: int, k: int, seed: int) -> LinearCodeSpec:
    if family == "random_systematic_linear":
        return random_systematic_code(n, k, seed)
    if family == "crc_defined_linear":
        return crc_systematic_code(n, k)
    if family == "extended_hamming":
        code = extended_hamming_code(n)
        if code.k != k:
            raise ValueError(f"extended Hamming n={n} has frozen k={code.k}, not requested k={k}")
        return code
    raise ValueError(f"unknown code family {family!r}")
