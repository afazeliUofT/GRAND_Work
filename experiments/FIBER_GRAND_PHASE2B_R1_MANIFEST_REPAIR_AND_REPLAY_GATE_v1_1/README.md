# FIBER-GRAND Paper I — Phase 2B-R1

This package performs the **canonical Phase-2A manifest repair and the full frozen Phase-2B replay gate**. It replaces the first Phase-2B package only because that run stopped before scientific execution when `PACKAGE_CONSOLE.log` was incorrectly treated as an unexplained mismatch.

The package does **not** rerun Phase 2A. It accepts only the following frozen, independently verifiable transformations:

1. the five preregistered CSV files whose original CRLF bytes were normalized by Git to LF; and
2. the exact four final Phase-2A status lines appended to `PACKAGE_CONSOLE.log` after `MANIFEST.sha256` had already been written.

The console append is accepted only when the old manifest hash equals a strict newline-boundary prefix, that prefix ends at the frozen structural-scan line, and the four appended values agree with `RUN_STATUS.json` and the return-ZIP SHA-256 sidecar. Any other mismatch is fatal.

After repair, the package automatically continues the previously authorized sequence:

- exact proof-support checks;
- independent C++17 exact-integer build and self-test;
- 198 synthetic nonuniform/zero-weight bound checks;
- exact replay of all 3,360 frozen bound cases and 214 frozen decoder trials;
- compiled timing gate; and
- the preregistered 1,024-trial targeted pilot **only if** the replay gate authorizes it.

The canonical replay CSVs are exported directly from the frozen Git commit and replayed from that export, not from mutable working-tree paths.

The package uses no third-party Python dependencies. A C++17 compiler is required. The virtual environment and compiled binary remain outside the Git repository.

Run only through `RUN_FIBER_GRAND_PHASE2B_R1.py` from `/home/afazeli2006/GRAND_Work`.

The automated decision never declares worldwide novelty, paper acceptance, or a Transactions extension. Independent proof and novelty review remain mandatory.
