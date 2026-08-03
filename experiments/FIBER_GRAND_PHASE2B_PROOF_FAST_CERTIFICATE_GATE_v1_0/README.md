# FIBER-GRAND Paper I — Phase 2B

This package implements the bounded **proof closure and cheap-certificate kill gate** authorized after Phase 2A.

It does not rerun Phase 2A. It first repairs the Phase 2A manifest at the metadata level, compiles an independent C++17 exact-integer implementation, cross-checks it on 198 deterministic nonuniform/zero-weight cases, replays the frozen 3,360 bound cases and 214 decoder trials, and permits the preregistered 1,024-trial targeted pilot only if the replay acceleration gate passes.

The package uses no third-party Python dependencies. A C++17 compiler is required. Compiled binaries and the virtual environment live outside the Git repository.

Run only through `RUN_FIBER_GRAND_PHASE2B.py` from `/home/afazeli2006/GRAND_Work`.

The automated decision is deliberately conservative. It never declares a paper-level novelty PASS, never authorizes a broad campaign, and never replaces independent mathematical review.
