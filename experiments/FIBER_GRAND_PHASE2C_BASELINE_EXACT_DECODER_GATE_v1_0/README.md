# FIBER-GRAND Paper I — Phase 2C baseline exact-decoder gate

This package executes the single bounded follow-up authorized after Phase 2B-R1 narrowed the expensive alignment-consistent certificate `U_AC` to a mathematical result.

Phase 2C does **not** optimize `U_AC` and does not broaden the channel model. It evaluates the baseline exact shell-certified inverse-alignment decoder for:

- exactly one uniformly located deletion;
- independent binary substitutions with `p_s=0.05`;
- arbitrary binary linear codes exposed through membership checks;
- blocklengths 16, 24, and 32;
- random systematic, CRC-defined, and extended-Hamming families.

The package contains the completed internal theorem source, exact theorem-support checks, an exact C++17 implementation, exhaustive codeword-ML calibration, a generic exact branch-and-bound comparator, a history-pair comparator, and a preregistered bounded campaign.

## Canonical invocation

The companion wrapper runs this package from `/home/afazeli2006/GRAND_Work`, creates its environment and compiled cache outside Git, and commits/pushes only auditable source and result files.

Do not execute package modules manually and do not launch a larger campaign after this run. The scientific decision in `SCIENTIFIC_DECISION.json` must be reviewed first.
