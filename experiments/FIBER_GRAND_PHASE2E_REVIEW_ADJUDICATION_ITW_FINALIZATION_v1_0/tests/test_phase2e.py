from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase2e_runner", ROOT / "run_phase2e.py")
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class Phase2ETests(unittest.TestCase):
    def test_exact_review_repairs(self) -> None:
        report = mod.exact_regression_checks()
        self.assertEqual(report["status"], "PASS")
        names = {item["name"] for item in report["checks"]}
        self.assertIn("strict_complete_tie_witness", names)
        self.assertIn("strict_reversal_grid", names)
        self.assertIn("uniform_code_occupancy", names)

    def test_claim_discipline(self) -> None:
        report = mod.static_claim_checks()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["standalone_tex"])

    def test_four_source_reviews_present(self) -> None:
        files = [p for p in (ROOT / "reviews" / "source_reviews").iterdir() if p.is_file()]
        self.assertEqual(len(files), 4)
        self.assertEqual(sum(p.suffix.lower() == ".pdf" for p in files), 2)
        self.assertEqual(sum(p.suffix.lower() == ".md" for p in files), 2)

    def test_no_simulation_contract(self) -> None:
        cfg = json.loads((ROOT / "config" / "phase2e_default.json").read_text(encoding="utf-8"))
        self.assertFalse(cfg["new_simulations_authorized"])
        self.assertEqual(cfg["phase2e_decision"], "ITW_READY_AFTER_REVIEW_REPAIR")

    def test_precompiled_pdfs_exist(self) -> None:
        for name in (
            "FIBER_GRAND_Paper_I_ITW_Candidate_Phase2E.pdf",
            "FIBER_GRAND_Paper_I_Proof_Supplement_Phase2E.pdf",
        ):
            p = ROOT / "precompiled" / name
            self.assertTrue(p.is_file())
            self.assertGreater(p.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
