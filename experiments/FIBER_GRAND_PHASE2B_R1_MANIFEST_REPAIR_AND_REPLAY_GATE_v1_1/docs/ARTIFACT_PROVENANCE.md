# Artifact provenance and repair scope

Frozen Phase-2A commit:

```text
c4073f84a2e8c7f6d19281db64e862347602fa02
```

Recorded failed Phase-2B diagnostic commit:

```text
35eeebb685e50824d8ddc3e88403e1c5a9f0bd1c
```

The failed Phase-2B run stopped before proof checks, compilation, replay, or new simulations because `PACKAGE_CONSOLE.log` differed from its original manifest hash. R1 recognizes that mismatch only as a deterministic post-manifest append after verifying the exact prefix and independently reconstructing all four appended values.

The canonical committed manifest records the exact Git blobs at the frozen commit. The original manifest is preserved. The current worktree manifest is recorded separately. Replay inputs are exported from the frozen Git blobs to prevent later worktree edits from entering the replay.
