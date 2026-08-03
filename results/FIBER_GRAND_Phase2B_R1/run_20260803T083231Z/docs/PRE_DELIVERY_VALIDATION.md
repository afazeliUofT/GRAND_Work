# Pre-delivery validation

The Phase-2B scientific core is unchanged from the prior package that passed development checks for:

- five original Python unit tests;
- the C++17 exact-kernel self-test under `-O3 -DNDEBUG -std=c++17 -Wall -Wextra -pedantic`;
- 198 deterministic compiled-versus-Python bound comparisons;
- exact development replay of 3,360 frozen bound rows and 214 decoder rows with zero mismatches; and
- two-pass compilation of the proof-closure LaTeX source.

The R1 delta was additionally checked by:

- four strict console-append classifier tests;
- a complete temporary-Git positive repair test reproducing five CRLF transformations plus the exact four-line append;
- a negative test proving that modified replay input fails worktree integrity;
- all original mathematical/unit tests;
- C++ self-test; and
- proof-support checks.

These construction checks do not replace the canonical WSL run, external proof review, or novelty review.

The machine-readable record is `docs/R1_DELTA_VALIDATION.json`. It also confirms the exact frozen console-prefix hash `17c91daf...`, committed full-log hash `ce71ba9e...`, and classification `EXPECTED_POST_MANIFEST_CONSOLE_APPEND`.
