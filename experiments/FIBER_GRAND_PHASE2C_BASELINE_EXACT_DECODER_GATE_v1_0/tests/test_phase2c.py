from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fiber_phase2c.codes import build_code, extended_hamming_code
from fiber_phase2c.theory import (
    discovery_shell,
    distinct_binary_supersequences,
    exact_scaled_score,
    generated_attempt_cap,
    insert_bit,
    masks_of_weight,
    realization_shell_cap,
    shell_bound_scaled,
    shell_candidate_set,
    stopping_offset_uniform,
)
from fiber_phase2c.trials import build_trial_specs
from fiber_phase2c.util import stable_seed


ROOT = Path(__file__).resolve().parents[1]


class Phase2CUnitTests(unittest.TestCase):
    def test_insertion_sphere_exact(self) -> None:
        for m in range(0, 9):
            for z in range(1 << m):
                got = set(distinct_binary_supersequences(z, m))
                expected = {insert_bit(z, j, b) for j in range(m + 1) for b in (0, 1)}
                self.assertEqual(got, expected)
                self.assertEqual(len(got), m + 2)

    def test_discovery_shell(self) -> None:
        for n in range(2, 7):
            for y in range(1 << (n - 1)):
                for s in range(n):
                    got = shell_candidate_set(y, n, s)
                    expected = {x for x in range(1 << n) if discovery_shell(x, y, n) <= s}
                    self.assertEqual(got, expected)

    def test_shell_bound(self) -> None:
        for n in range(2, 8):
            for a in (2, 4, 19):
                for y in (0, (1 << (n - 1)) - 1):
                    for s in range(n - 1):
                        discovered = shell_candidate_set(y, n, s)
                        maximum = max((exact_scaled_score(x, y, n, a) for x in range(1 << n) if x not in discovered), default=0)
                        self.assertLessEqual(maximum, shell_bound_scaled(n, a, s))

    def test_stopping_offset_examples(self) -> None:
        self.assertEqual(stopping_offset_uniform(32, 1, 20), 2)
        self.assertEqual(stopping_offset_uniform(32, 1, 100), 1)
        self.assertEqual(realization_shell_cap(32, 1, 20, 4), 5)
        self.assertEqual(generated_attempt_cap(32, 5, True), 6810144)
        self.assertEqual(generated_attempt_cap(32, 5, False), 13207552)

    def test_code_reproducibility_and_orthogonality(self) -> None:
        seed = stable_seed(20260803, "test")
        for family, n, k in (
            ("random_systematic_linear", 16, 11),
            ("crc_defined_linear", 16, 11),
            ("extended_hamming", 16, 11),
            ("extended_hamming", 32, 26),
        ):
            c1 = build_code(family, n, k, seed)
            c2 = build_code(family, n, k, seed)
            self.assertEqual(c1, c2)
            for message in range(min(64, 1 << k)):
                self.assertTrue(c1.is_codeword(c1.encode(message)))

    def test_extended_hamming_distance_small(self) -> None:
        code = extended_hamming_code(16)
        minimum = min(code.encode(message).bit_count() for message in range(1, 1 << code.k))
        self.assertEqual(minimum, 4)

    def test_default_trial_contract(self) -> None:
        config = json.loads((ROOT / "config" / "phase2c_default.json").read_text())
        specs = build_trial_specs(config)
        self.assertEqual(len(specs), 996)
        self.assertEqual(sum(s.trial_kind == "natural" for s in specs), 896)
        self.assertEqual(sum(s.trial_kind == "stress" for s in specs), 100)
        self.assertEqual(len({s.trial_id for s in specs}), len(specs))
        for spec in specs:
            self.assertTrue(spec.code.is_codeword(spec.transmitted_word))
            self.assertLess(spec.observation, 1 << (spec.n - 1))


if __name__ == "__main__":
    unittest.main()
