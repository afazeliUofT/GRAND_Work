# Pre-delivery validation (development environment only)

Before packaging, the source passed:

- five Python unit tests;
- the C++17 exact-kernel self-test with `-O3 -DNDEBUG -std=c++17 -Wall -Wextra -pedantic`;
- 198 deterministic compiled-versus-Python bound comparisons using irregular/exhausted frontiers and zero/nonuniform weights;
- exact replay of 3,360 Phase-2A structural-bound rows and 214 paired decoder rows, with zero bound, stopping, score, final-bound, decoded-word, or tie-set mismatches;
- two-pass LaTeX compilation of the seven-page proof-closure source.

These checks validate package construction. They do not replace the WSL run against the committed Phase-2A artifacts, independent human proof review, or novelty review. Runtime gates are deliberately remeasured on the user's WSL machine.
