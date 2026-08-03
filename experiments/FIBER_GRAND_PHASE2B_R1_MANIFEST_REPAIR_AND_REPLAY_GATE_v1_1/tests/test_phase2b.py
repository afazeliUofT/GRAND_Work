from __future__ import annotations

import random
import unittest
from fractions import Fraction

from fiber_phase2b.reference import (
    build_code,
    chain_bound,
    independent_bound,
    mismatch_vector,
    scaled_score,
    uac_bound,
)
from fiber_phase2b.util import stable_seed


class Phase2BTests(unittest.TestCase):
    def test_bound_hierarchy(self) -> None:
        rng = random.Random(7)
        for n in range(2, 9):
            for _ in range(20):
                y = rng.randrange(1 << (n - 1))
                r = tuple(rng.randrange(n + 1) for _ in range(n))
                w = tuple(rng.randrange(5) for _ in range(n))
                self.assertLessEqual(uac_bound(y, r, n, 4, w), chain_bound(y, r, n, 4, w))
                self.assertLessEqual(chain_bound(y, r, n, 4, w), independent_bound(r, n, 4, w))

    def test_strict_reversal(self) -> None:
        def bits(text: str) -> int:
            return sum((character == "1") << index for index, character in enumerate(text))

        for n in range(4, 80):
            y = bits("0" * (n - 3) + "10")
            x_a = bits("0" * (n - 3) + "101")
            x_b = 0
            a = 19
            self.assertEqual(mismatch_vector(x_a, y, n), (3,) * (n - 3) + (2, 1, 0))
            p = Fraction(1, a + 1)
            self.assertEqual(
                scaled_score(x_b, y, n, a) > scaled_score(x_a, y, n, a),
                n * p > 1 + 2 * p * p,
            )

    def test_code_reproducibility(self) -> None:
        for family in ("random_systematic_linear", "crc_defined_linear"):
            first = build_code(family, 32, 21, 123)
            second = build_code(family, 32, 21, 123)
            self.assertEqual(first.rows, second.rows)
            for message in (0, 1, 17, (1 << 21) - 1):
                self.assertEqual(first.encode(message), second.encode(message))

    def test_boundaries_and_zero_weights(self) -> None:
        for n in range(2, 9):
            y = (1 << (n - 1)) - 1
            zero = (0,) * n
            self.assertEqual(independent_bound((0,) * n, n, 4, zero), 0)
            self.assertEqual(chain_bound(y, (0,) * n, n, 4, zero), 0)
            self.assertEqual(uac_bound(y, (0,) * n, n, 4, zero), 0)
            self.assertEqual(uac_bound(y, (n,) * n, n, 4, (1,) * n), 0)

    def test_stable_seed(self) -> None:
        self.assertEqual(stable_seed(1, "x", 3), stable_seed(1, "x", 3))
        self.assertNotEqual(stable_seed(1, "x", 3), stable_seed(1, "x", 4))



if __name__ == "__main__":
    unittest.main()
