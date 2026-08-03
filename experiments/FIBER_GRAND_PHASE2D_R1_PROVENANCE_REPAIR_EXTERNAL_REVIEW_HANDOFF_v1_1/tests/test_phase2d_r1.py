from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fiber_phase2d_r1.provenance import _find_manifest_prefix, classify_crlf_normalization
from fiber_phase2d_r1.review_bundle import REVIEW_FILES


class ProvenanceUnitTests(unittest.TestCase):
    def test_strict_prefix_accepts_empty_manifest_snapshot(self) -> None:
        data = b"[phase2d] status=PASS\n"
        self.assertEqual(_find_manifest_prefix(data, hashlib.sha256(b"").hexdigest()), 0)

    def test_strict_prefix_rejects_complete_blob(self) -> None:
        data = b"line\n"
        with self.assertRaises(RuntimeError):
            _find_manifest_prefix(data, hashlib.sha256(data).hexdigest())

    def test_crlf_normalization(self) -> None:
        lf = b"a,b\n1,2\n"
        old = hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest()
        record = classify_crlf_normalization(lf, old, "x.csv")
        self.assertEqual(record["diagnosis"], "CRLF_TO_LF_NORMALIZATION")
        self.assertEqual(record["row_count"], 2)

    def test_crlf_rejects_content_change(self) -> None:
        with self.assertRaises(RuntimeError):
            classify_crlf_normalization(b"a,b\n1,3\n", hashlib.sha256(b"a,b\r\n1,2\r\n").hexdigest(), "x.csv")

    def test_review_bundle_contract(self) -> None:
        destinations = [destination for _source, destination in REVIEW_FILES]
        self.assertEqual(len(destinations), len(set(destinations)))
        self.assertIn("01_Conference_Manuscript.pdf", destinations)
        self.assertIn("02_Proof_Supplement.pdf", destinations)
        self.assertIn("03_CLAIM_NOVELTY_MATRIX.md", destinations)


if __name__ == "__main__":
    unittest.main()
