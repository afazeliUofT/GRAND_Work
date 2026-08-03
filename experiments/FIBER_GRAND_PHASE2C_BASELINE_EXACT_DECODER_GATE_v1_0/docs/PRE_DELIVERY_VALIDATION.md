# Pre-delivery validation

Before packaging, the source was checked in a separate development directory by:

- compiling the theorem source twice with `pdflatex` without a fatal error;
- compiling the C++17 implementation with `-O3 -DNDEBUG -std=c++17 -Wall -Wextra -pedantic`;
- passing the compiled insertion-sphere/large-integer self-test;
- passing the Python unit suite;
- completing the smoke campaign with zero exact disagreements;
- completing a full construction pretest of the preregistered campaign with zero validation violations.

These are package-construction checks. The user’s WSL run against the canonical Git repository is the authoritative evidence for the project decision.
