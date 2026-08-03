# Method

## R1 provenance repair

The repair reads the original manifest and every scientific artifact directly from the frozen Phase-2A Git commit. It accepts only:

- the five preregistered CSV CRLF-to-LF normalizations, each proved by reconstructing CRLF bytes and reproducing the original SHA-256; and
- one `EXPECTED_POST_MANIFEST_CONSOLE_APPEND` event.

The console event is accepted only if the original manifest digest equals a strict newline-boundary prefix of the committed log, the prefix ends at `[pilot] running alignment-bound structural scan`, and the remaining bytes are exactly four lines. Their status, output path, return-ZIP path, and return-ZIP digest are derived independently from `RUN_STATUS.json`, the frozen run path, and the committed SHA-256 sidecar. A local return ZIP, when present, must also match the sidecar.

The repair also verifies that the frozen Phase-2A result path has not changed in later commits and that the working-tree copies of all manifest entries are either byte-identical to the frozen Git blobs or are the authorized original CRLF CSV representation. The two replay CSVs are then exported directly from the frozen commit into `FROZEN_REPLAY_INPUTS` and replayed from there.

## Exact decoder replay

The compiled implementation reproduces the Phase-2A candidate order, code-membership interface, exact aggregate score, strict tie-set certificate, forward/even-odd alignment schedules, and all three bounds. It uses a fixed-capacity 512-bit multiword unsigned integer with explicit overflow detection. This is exact for the frozen range (`n<=32` in the experiments; implementation contract `n<=63`, odds denominator `a<=99`), so no stopping comparison uses floating point.

The C++ executable is built with `-O3 -DNDEBUG -std=c++17` into `~/.cache/fiber_grand_phase2b_r1_v1_1`; the binary is not committed. Decoder-mode timing order is rotated across trial IDs to reduce systematic order bias.

Before the frozen replay, 198 deterministic synthetic cases compare all compiled bounds with the Python exact reference using irregular frontiers, exhausted streams, zero/nonuniform deletion weights, and several odds ratios. The replay then compares status, completion, exact scores, final bounds, complete ML tie sets, decoded representatives, emitted histories, distinct candidates, membership calls, exact-score evaluations, and frontier updates against the frozen Phase-2A evidence. Timing is measured anew and is not compared byte-for-byte.

The targeted pilot uses four `n=32`, `p_s=0.05` code/rate cells and is run only if the exact replay plus acceleration gate passes. No broader channel model is added.
