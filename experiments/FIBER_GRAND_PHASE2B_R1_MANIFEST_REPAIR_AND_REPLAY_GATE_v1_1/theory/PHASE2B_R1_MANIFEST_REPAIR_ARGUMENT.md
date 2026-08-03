# Phase 2B-R1 manifest-repair argument

## Scope

This note closes the provenance defect that blocked the first Phase-2B execution. It does not modify the channel model, decoder, theorem statements, dynamic programs, or Phase-2A numerical evidence.

## Frozen observation

Let `P` denote the bytes of `PACKAGE_CONSOLE.log` at the instant when Phase 2A generated `MANIFEST.sha256`, and let `L` denote the bytes committed to Git after the child process terminated. The original manifest contains

\[
h_P=\operatorname{SHA256}(P).
\]

The committed log satisfies

\[
L=P\,\|\,S,
\]

where `S` is alleged to contain the four final status lines printed after manifest creation.

## Acceptance proposition

The R1 repair classifies the mismatch as `EXPECTED_POST_MANIFEST_CONSOLE_APPEND` only if all of the following hold:

1. `h_P` equals the SHA-256 of a **strict prefix** of `L` ending at an LF line boundary.
2. The terminal line of that prefix is exactly

   ```text
   [pilot] running alignment-bound structural scan
   ```

3. The suffix contains exactly four LF-terminated lines and no other byte.
4. The first line reports the status stored independently in `RUN_STATUS.json`.
5. The output path equals the frozen run path derived from the repository and run identifier.
6. The return-ZIP filename equals the frozen run-derived filename.
7. The reported return-ZIP digest equals the digest stored in the committed `.zip.sha256` sidecar.
8. When the local uncommitted return ZIP is present, its independently recomputed digest also equals that sidecar.

Under these conditions, the committed log differs from the originally hashed log only by the deterministic final-status append. No earlier log byte and no numerical result file is changed within the accepted model.

## CSV normalization proposition

For each of the five preregistered CSV paths, let `C_LF` be the committed Git blob. The repair constructs `C_CRLF` by replacing each LF with CRLF after canonicalizing any existing CRLF to LF. The mismatch is accepted only when

\[
\operatorname{SHA256}(C_{\mathrm{CRLF}})
=
\text{the original manifest digest}.
\]

Thus the accepted difference is exactly the text line-ending representation. CSV field values and row order are unchanged.

## Closed-world property

The accepted path set is fixed in the configuration. A mismatch in any other path, a missing committed file, a changed Phase-2A path in a later commit, a staged Phase-2A change, a non-equivalent worktree copy, an extra console line, or a sidecar disagreement causes failure.

## Replay isolation

The two replay inputs are copied directly from the frozen Git commit into

```text
FROZEN_REPLAY_INPUTS/pilot/bound_scan.csv
FROZEN_REPLAY_INPUTS/pilot/paired_trials.csv
```

and a dedicated SHA-256 manifest is written for those exports. The compiled replay reads these immutable exports rather than mutable working-tree paths.

## Cryptographic assumption

As with the original package, integrity interpretation assumes collision resistance of SHA-256 and correct operation of the local Git and hashing implementations. This is an ordinary artifact-integrity assumption, not a mathematical theorem about the channel decoder.

## Conclusion

The R1 repair establishes a canonical, reproducible bridge from the original Phase-2A manifest to the exact committed artifacts without rerunning Phase 2A. Once this gate passes, the previously prepared proof checks, exact C++ replay, timing gate, and conditionally authorized targeted pilot may proceed unchanged.
