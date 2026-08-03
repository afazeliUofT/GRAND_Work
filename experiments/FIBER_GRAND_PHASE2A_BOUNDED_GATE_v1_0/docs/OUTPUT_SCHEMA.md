# Output files

- `RUN_METADATA.json`: package, Python, platform, command, and environment.
- `CONFIG_USED.json`: immutable configuration copied into the run.
- `validation/exact_validation_summary.json`: exact gate with case counts.
- `validation/exact_validation.log`: compact machine-readable PASS/FAIL record.
- `pilot/paired_trials.csv`: one row per channel realization and alignment schedule, containing all three certificate modes.
- `pilot/pilot_summary.json`: disagreement, censoring, and exhaustive-ML counts.
- `pilot/cell_summary.csv`: natural-channel cell medians and sample-size-qualified tails.
- `pilot/stress_summary.csv`: forced-error-weight results.
- `pilot/schedule_summary.csv`: forward versus even/odd comparisons on identical realizations.
- `pilot/bound_scan.csv`: code-independent frontier-state tightening measurements.
- `pilot/bound_scan_summary.json`: aggregate and per-schedule structural-bound statistics.
- `pilot/SCREENING_DECISION.json`: conservative automated label; human review is mandatory.
- `PHASE2A_REPORT.md`: concise review report.
- `MANIFEST.sha256`: hashes of returned files, excluding the self-containing return ZIP.
- `FIBER_GRAND_PHASE2A_RETURN_<run>.zip`: local compact bundle for independent review; the wrapper does not stage this duplicate ZIP in Git.
