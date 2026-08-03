# Phase 2A manifest repair — Phase 2B-R1

This is a closed-world integrity reconciliation of the frozen Phase-2A commit.
No Phase-2A computation is rerun or modified.

- Preregistered CSV normalizations established: `5`.
- Verified post-manifest console append: `1`.
- Worktree content mismatches: `0`.
- Canonical replay inputs exported from the frozen commit: `2`.
- Unexplained or policy-blocking differences: `0`.

The console append is accepted only when:

1. the old manifest hash equals a strict newline-boundary prefix of the committed log;
2. that prefix ends at the frozen structural-scan line;
3. the suffix is exactly the four final Phase-2A status lines;
4. the printed status equals `RUN_STATUS.json`;
5. the printed return-ZIP digest equals the committed sidecar; and
6. a local return ZIP, when present, has the same digest.

Repair status: **PASS**.

Any other byte difference remains fatal.
