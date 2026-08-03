from __future__ import annotations

import random
import unittest

from fiber_phase2a.bounds import chain_relaxed_bruteforce_int, chain_relaxed_dp_int, independent_bound_int, uac_bruteforce_int, uac_dp_optimized_int, uac_dp_reference_int
from fiber_phase2a.codes import crc_systematic_code, random_systematic_code
from fiber_phase2a.model import delete_bit, insert_bit, mismatch_vector_direct, mismatch_vector_recurrence, scaled_score_int
from fiber_phase2a.search import decode_exact_search


class CoreTests(unittest.TestCase):
    def test_insert_delete_inverse(self) -> None:
        for n in range(2, 9):
            for y in range(1 << (n - 1)):
                for j in range(n):
                    for b in (0, 1):
                        self.assertEqual(delete_bit(insert_bit(y, j, b), j), y)

    def test_recurrence(self) -> None:
        rng = random.Random(7)
        for n in range(2, 12):
            for _ in range(100):
                x = rng.randrange(1 << n)
                y = rng.randrange(1 << (n - 1))
                self.assertEqual(mismatch_vector_direct(x, y, n), mismatch_vector_recurrence(x, y, n))

    def test_uac_three_ways(self) -> None:
        for n in range(2, 7):
            for y in range(1 << (n - 1)):
                r = tuple((j + y) % min(3, n) for j in range(n))
                values = (
                    uac_bruteforce_int(y, r, n, 4),
                    uac_dp_reference_int(y, r, n, 4),
                    uac_dp_optimized_int(y, r, n, 4),
                )
                chain_values = (
                    chain_relaxed_bruteforce_int(y, r, n, 4),
                    chain_relaxed_dp_int(y, r, n, 4),
                )
                self.assertEqual(values[0], values[1])
                self.assertEqual(values[1], values[2])
                self.assertEqual(chain_values[0], chain_values[1])
                self.assertLessEqual(values[2], chain_values[1])
                self.assertLessEqual(chain_values[1], independent_bound_int(r, n, 4))

    def test_code_interfaces(self) -> None:
        for code in (random_systematic_code(16, 11, 9), crc_systematic_code(16, 11)):
            for message in range(1 << code.k):
                self.assertTrue(code.is_codeword(code.encode(message)))

    def test_decoder_modes_agree_small(self) -> None:
        code = random_systematic_code(8, 5, 11)
        for alignment_schedule in ("forward", "even_odd"):
            for message in range(1 << code.k):
                x = code.encode(message)
                y = delete_bit(x, message % 8)
                common = {
                    "y": y, "code": code, "odds_denominator": 19,
                    "max_histories": 100000, "alignment_schedule": alignment_schedule,
                }
                ind = decode_exact_search(bound_mode="independent", **common)
                cr = decode_exact_search(bound_mode="chain_relaxed", **common)
                ac = decode_exact_search(bound_mode="alignment_consistent", **common)
                self.assertTrue(ind.complete)
                self.assertTrue(cr.complete)
                self.assertTrue(ac.complete)
                self.assertEqual((ind.incumbent_score, ind.tie_words), (cr.incumbent_score, cr.tie_words))
                self.assertEqual((ind.incumbent_score, ind.tie_words), (ac.incumbent_score, ac.tie_words))
                self.assertLessEqual(ac.q_hist, cr.q_hist)
                self.assertLessEqual(cr.q_hist, ind.q_hist)

    def test_chain_schedule_geometry(self) -> None:
        # Forward prefix frontiers attain the independent relaxation.
        for n in range(3, 9):
            m = n - 1
            for y in range(1 << m):
                for s in range(m):
                    for k in range(n + 1):
                        r = tuple([s + 1] * k + [s] * (n - k))
                        self.assertEqual(chain_relaxed_dp_int(y, r, n, 4), independent_bound_int(r, n, 4))
        # A valid equal-weight nonmonotone frontier is strictly tighter.
        n, y, r = 3, 1, (1, 0, 1)
        ind = independent_bound_int(r, n, 4)
        cr = chain_relaxed_dp_int(y, r, n, 4)
        ac = uac_dp_optimized_int(y, r, n, 4)
        self.assertEqual(ac, cr)
        self.assertLess(cr, ind)


if __name__ == "__main__":
    unittest.main()
