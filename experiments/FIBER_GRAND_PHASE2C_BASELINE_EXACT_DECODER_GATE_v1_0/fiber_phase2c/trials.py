from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .codes import LinearCodeSpec, build_code
from .theory import delete_bit, realization_shell_cap, stopping_offset_uniform
from .util import stable_seed, write_csv


@dataclass(frozen=True)
class TrialSpec:
    trial_id: int
    trial_kind: str
    cell_id: str
    trial_index: int
    trial_seed: int
    code_instance: int
    code_seed: int
    family: str
    rate_label: str
    n: int
    k: int
    p_num: int
    p_den: int
    transmitted_word: int
    observation: int
    deletion_position: int
    observed_error_weight: int
    forced_error_weight: int | None
    theorem_offset: int
    theorem_stop_shell_cap: int
    max_generated_attempts: int
    run_exhaustive: bool
    run_branch: bool
    branch_node_cap: int
    branch_time_ms: int
    code: LinearCodeSpec

    def metadata_row(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "trial_kind": self.trial_kind,
            "cell_id": self.cell_id,
            "trial_index": self.trial_index,
            "trial_seed": self.trial_seed,
            "code_instance": self.code_instance,
            "code_seed": self.code_seed,
            "family": self.family,
            "rate_label": self.rate_label,
            "n": self.n,
            "k": self.k,
            "rate": self.k / self.n,
            "p_num": self.p_num,
            "p_den": self.p_den,
            "p_s": self.p_num / self.p_den,
            "transmitted_word_hex": hex(self.transmitted_word),
            "observation_hex": hex(self.observation),
            "deletion_position": self.deletion_position,
            "observed_error_weight": self.observed_error_weight,
            "forced_error_weight": "" if self.forced_error_weight is None else self.forced_error_weight,
            "theorem_offset": self.theorem_offset,
            "theorem_stop_shell_cap": self.theorem_stop_shell_cap,
            "max_generated_attempts": self.max_generated_attempts,
            "run_exhaustive": self.run_exhaustive,
            "run_branch": self.run_branch,
            "branch_node_cap": self.branch_node_cap,
            "branch_time_ms": self.branch_time_ms,
            "code_size": 1 << self.k,
            "generator_rows_hex": ",".join(hex(x) for x in self.code.generator_rows),
            "parity_check_rows_hex": ",".join(hex(x) for x in self.code.parity_check_rows),
            "code_construction": self.code.construction,
        }

    def cpp_input_row(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "n": self.n,
            "k": self.k,
            "a": (self.p_den - self.p_num) // self.p_num,
            "y": hex(self.observation),
            "tx": hex(self.transmitted_word),
            "generator_rows": ",".join(hex(x) for x in self.code.generator_rows),
            "parity_check_rows": ",".join(hex(x) for x in self.code.parity_check_rows),
            "max_generated_attempts": self.max_generated_attempts,
            "run_exhaustive": int(self.run_exhaustive),
            "run_branch": int(self.run_branch),
            "branch_node_cap": self.branch_node_cap,
            "branch_time_ms": self.branch_time_ms,
        }


def _sample_error_mask(rng: random.Random, m: int, p_num: int, p_den: int, forced_weight: int | None) -> int:
    if forced_weight is not None:
        if not 0 <= forced_weight <= m:
            raise ValueError("forced error weight outside range")
        positions = rng.sample(range(m), forced_weight)
    else:
        p = p_num / p_den
        positions = [i for i in range(m) if rng.random() < p]
    mask = 0
    for pos in positions:
        mask |= 1 << pos
    return mask


def _cell_id(cell: dict[str, Any]) -> str:
    return f"n{int(cell['n'])}_k{int(cell['k'])}_{cell['family']}_{cell['rate_label']}"


def _baseline_flags(config: dict[str, Any], *, n: int, k: int, trial_index: int) -> tuple[bool, bool]:
    base = config["baselines"]
    if n <= int(base["exhaustive_all_n_le"]):
        run_exhaustive = True
    elif n == 24:
        run_exhaustive = trial_index < int(base["exhaustive_calibration_per_cell_n24"])
    elif n == 32 and k <= 21:
        run_exhaustive = trial_index < int(base["exhaustive_calibration_per_cell_n32_k_le_21"])
    else:
        run_exhaustive = False

    if n <= int(base["branch_all_n_le"]):
        run_branch = True
    elif n == 24:
        run_branch = trial_index < int(base["branch_calibration_per_cell_n24"])
    elif n == 32:
        run_branch = trial_index < int(base["branch_calibration_per_cell_n32"])
    else:
        run_branch = False
    return run_exhaustive, run_branch


def build_trial_specs(config: dict[str, Any]) -> list[TrialSpec]:
    master = int(config["master_seed"])
    p_num = int(config["channel"]["p_num"])
    p_den = int(config["channel"]["p_den"])
    if p_num != 1 or p_den not in (10, 20, 50, 100):
        raise ValueError("Phase 2C compiled exact score is frozen to p=1/d with d in {10,20,50,100}")
    natural_trials = int(config["natural_campaign"]["trials_per_cell"])
    random_instances = max(1, int(config["natural_campaign"].get("random_code_instances", 1)))
    max_attempts = int(config["limits"]["max_generated_attempts"])
    branch_node_cap = int(config["limits"]["branch_node_cap"])
    branch_time_ms = int(config["limits"]["branch_time_ms"])

    specs: list[TrialSpec] = []
    next_id = 0
    cells = list(config["natural_campaign"]["cells"])

    def build_one(cell: dict[str, Any], trial_kind: str, trial_index: int, forced_weight: int | None) -> TrialSpec:
        nonlocal next_id
        n, k = int(cell["n"]), int(cell["k"])
        family, rate_label = str(cell["family"]), str(cell["rate_label"])
        cell_id = _cell_id(cell)
        if family == "random_systematic_linear":
            # Spread trials as evenly as possible over frozen independent code instances.
            code_instance = trial_index % random_instances
            code_seed = stable_seed(master, "code", cell_id, code_instance)
        else:
            code_instance = 0
            code_seed = 0
        code = build_code(family, n, k, code_seed)
        trial_seed = stable_seed(master, trial_kind, cell_id, trial_index, forced_weight)
        rng = random.Random(trial_seed)
        message = rng.randrange(1 << k)
        transmitted = code.encode(message)
        deletion_position = rng.randrange(n)
        error_mask = _sample_error_mask(rng, n - 1, p_num, p_den, forced_weight)
        observation = delete_bit(transmitted, deletion_position) ^ error_mask
        run_exhaustive, run_branch = _baseline_flags(config, n=n, k=k, trial_index=trial_index)
        spec = TrialSpec(
            trial_id=next_id,
            trial_kind=trial_kind,
            cell_id=cell_id,
            trial_index=trial_index,
            trial_seed=trial_seed,
            code_instance=code_instance,
            code_seed=code_seed,
            family=family,
            rate_label=rate_label,
            n=n,
            k=k,
            p_num=p_num,
            p_den=p_den,
            transmitted_word=transmitted,
            observation=observation,
            deletion_position=deletion_position,
            observed_error_weight=error_mask.bit_count(),
            forced_error_weight=forced_weight,
            theorem_offset=stopping_offset_uniform(n, p_num, p_den),
            theorem_stop_shell_cap=realization_shell_cap(n, p_num, p_den, error_mask.bit_count()),
            max_generated_attempts=max_attempts,
            run_exhaustive=run_exhaustive,
            run_branch=run_branch,
            branch_node_cap=branch_node_cap,
            branch_time_ms=branch_time_ms,
            code=code,
        )
        next_id += 1
        return spec

    for cell in cells:
        for trial_index in range(natural_trials):
            specs.append(build_one(cell, "natural", trial_index, None))

    stress = config.get("stress_campaign", {})
    if bool(stress.get("enabled", False)):
        stress_n = int(stress["n"])
        reps = int(stress["trials_per_weight_per_cell"])
        for cell in cells:
            if int(cell["n"]) != stress_n:
                continue
            for weight in stress["weights"]:
                weight = int(weight)
                for rep in range(reps):
                    # Give each weight a disjoint trial-index range while preserving code-instance rotation.
                    trial_index = weight * reps + rep
                    specs.append(build_one(cell, "stress", trial_index, weight))
    return specs


def write_trial_inputs(specs: list[TrialSpec], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "TRIAL_SPECS.csv"
    cpp_path = output_dir / "CPP_INPUT.tsv"
    write_csv(metadata_path, [spec.metadata_row() for spec in specs])
    fieldnames = [
        "trial_id", "n", "k", "a", "y", "tx", "generator_rows", "parity_check_rows",
        "max_generated_attempts", "run_exhaustive", "run_branch", "branch_node_cap", "branch_time_ms",
    ]
    rows = [spec.cpp_input_row() for spec in specs]
    cpp_path.parent.mkdir(parents=True, exist_ok=True)
    with cpp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\t".join(fieldnames) + "\n")
        for row in rows:
            handle.write("\t".join(str(row[name]) for name in fieldnames) + "\n")
    return metadata_path, cpp_path
