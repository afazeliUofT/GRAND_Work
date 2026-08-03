from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol


class BinaryCode(Protocol):
    n: int
    k: int
    name: str

    def encode(self, message: int) -> int: ...
    def is_codeword(self, word: int) -> bool: ...
    def metadata(self) -> dict[str, object]: ...


@dataclass(frozen=True)
class SystematicParityCode:
    n: int
    k: int
    row_masks: tuple[int, ...]
    name: str
    construction: str

    def __post_init__(self) -> None:
        if not 0 < self.k < self.n:
            raise ValueError("require 0<k<n")
        if len(self.row_masks) != self.n - self.k:
            raise ValueError("wrong number of parity rows")
        if any(mask < 0 or mask >= (1 << self.k) for mask in self.row_masks):
            raise ValueError("parity row outside message range")

    @property
    def redundancy(self) -> int:
        return self.n - self.k

    def parity_for_message(self, message: int) -> int:
        if message < 0 or message >= (1 << self.k):
            raise ValueError("message outside range")
        parity = 0
        for i, row in enumerate(self.row_masks):
            parity |= (((row & message).bit_count() & 1) << i)
        return parity

    def encode(self, message: int) -> int:
        return message | (self.parity_for_message(message) << self.k)

    def is_codeword(self, word: int) -> bool:
        if word < 0 or word >= (1 << self.n):
            return False
        message_mask = (1 << self.k) - 1
        message = word & message_mask
        parity = word >> self.k
        return parity == self.parity_for_message(message)

    def metadata(self) -> dict[str, object]:
        return {
            "name": self.name,
            "construction": self.construction,
            "n": self.n,
            "k": self.k,
            "rate": self.k / self.n,
            "redundancy": self.redundancy,
            "row_masks_hex": [hex(x) for x in self.row_masks],
        }


@dataclass(frozen=True)
class SetCode:
    n: int
    words: frozenset[int]
    name: str = "explicit_set"

    @property
    def k(self) -> int:
        # Only used for metadata in complete-world tests.
        return -1

    def encode(self, message: int) -> int:
        ordered = sorted(self.words)
        return ordered[message % len(ordered)]

    def is_codeword(self, word: int) -> bool:
        return word in self.words

    def metadata(self) -> dict[str, object]:
        return {"name": self.name, "n": self.n, "size": len(self.words), "words": sorted(self.words)}


def random_systematic_code(n: int, k: int, seed: int) -> SystematicParityCode:
    rng = random.Random(seed)
    rows: list[int] = []
    for i in range(n - k):
        # Nonzero, reproducible dense rows. Systematic form guarantees rank n-k.
        mask = rng.getrandbits(k)
        if mask == 0:
            mask = 1 << (i % k)
        rows.append(mask)
    return SystematicParityCode(
        n=n,
        k=k,
        row_masks=tuple(rows),
        name="random_systematic_linear",
        construction=f"systematic parity map; seed={seed}",
    )


def _poly_mod(value: int, polynomial: int) -> int:
    degree = polynomial.bit_length() - 1
    while value.bit_length() - 1 >= degree:
        shift = (value.bit_length() - 1) - degree
        value ^= polynomial << shift
    return value


CRC_POLYNOMIALS: dict[int, int] = {
    4: (1 << 4) | (1 << 1) | 1,              # x^4+x+1
    5: (1 << 5) | (1 << 2) | 1,              # x^5+x^2+1
    6: (1 << 6) | (1 << 1) | 1,              # x^6+x+1
    8: (1 << 8) | (1 << 2) | (1 << 1) | 1,   # x^8+x^2+x+1
    11: (1 << 11) | (1 << 2) | 1,            # x^11+x^2+1
}


def crc_systematic_code(n: int, k: int) -> SystematicParityCode:
    r = n - k
    if r not in CRC_POLYNOMIALS:
        raise ValueError(f"no frozen polynomial for redundancy {r}")
    poly = CRC_POLYNOMIALS[r]

    # Build an equivalent systematic parity map in the package's coordinate
    # convention: message occupies low k bits, parity occupies high r bits.
    # Each row is obtained by encoding message basis vectors under polynomial
    # division and transposing the linear remainder map.
    parity_rows = [0] * r
    for message_index in range(k):
        message = 1 << message_index
        # Standard polynomial codeword has message in high bits and remainder low.
        shifted = message << r
        remainder = _poly_mod(shifted, poly)
        for parity_index in range(r):
            if (remainder >> parity_index) & 1:
                parity_rows[parity_index] |= 1 << message_index

    return SystematicParityCode(
        n=n,
        k=k,
        row_masks=tuple(parity_rows),
        name="crc_defined_linear",
        construction=f"degree-{r} polynomial {hex(poly)} mapped to systematic parity coordinates",
    )


def build_code(family: str, n: int, k: int, seed: int) -> SystematicParityCode:
    if family == "random_systematic_linear":
        return random_systematic_code(n, k, seed)
    if family == "crc_defined_linear":
        return crc_systematic_code(n, k)
    raise ValueError(f"unknown code family: {family}")
