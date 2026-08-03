from __future__ import annotations
import json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from fiber_phase2d.checks import check_claims
from fiber_phase2d.generate import generate
class Phase2DTests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads((ROOT/'config'/'phase2d_default.json').read_text())
        self.exp=json.loads((ROOT/'frozen_expected'/'EXPECTED_PHASE2C_EVIDENCE.json').read_text())
    def test_no_simulation_contract(self):
        self.assertTrue(self.cfg['no_new_simulation'])
    def test_expected_five_n32_cells(self):
        self.assertEqual(len(self.exp['n32_cells']),5)
    def test_query_savings_thresholds(self):
        for r in self.exp['n32_cells']:
            self.assertGreaterEqual(r['score_savings'],100000)
            self.assertGreaterEqual(r['membership_ratio'],100)
    def test_main_claim_discipline(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            result=check_claims(self.cfg,ROOT/'manuscript'/'FIBER_GRAND_Paper_I_Conference_Candidate.tex',ROOT/'supplement'/'FIBER_GRAND_Paper_I_Proof_Supplement.tex',out)
            self.assertEqual(result['status'],'PASS')
if __name__=='__main__':unittest.main()
