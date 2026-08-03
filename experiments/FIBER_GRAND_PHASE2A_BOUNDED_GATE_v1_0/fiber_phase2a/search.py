from __future__ import annotations

import functools
import itertools
import time
from dataclasses import asdict, dataclass
from typing import Sequence

from .bounds import chain_relaxed_dp_int, independent_bound_int, uac_dp_optimized_int
from .codes import BinaryCode
from .model import insert_bit, scaled_score_int


@functools.lru_cache(maxsize=None)
def masks_of_weight(length: int, weight: int) -> tuple[int, ...]:
    if weight < 0 or weight > length:
        return ()
    masks: list[int] = []
    for positions in itertools.combinations(range(length), weight):
        mask = 0
        for pos in positions:
            mask |= 1 << pos
        masks.append(mask)
    return tuple(masks)


@dataclass
class DecodeResult:
    bound_mode: str
    alignment_schedule: str
    status: str
    decoded_word: int | None
    tie_words: tuple[int, ...]
    incumbent_score: int
    final_bound: int
    stopping_margin: int
    q_hist: int
    q_disc: int
    q_code: int
    q_score: int
    duplicate_count: int
    duplicate_fraction: float
    frontier_updates: int
    bound_calls: int
    independent_bound_calls: int
    chain_dp_calls: int
    chain_skipped_proven_equal: int
    uac_dp_calls: int
    chain_cache_hits: int
    uac_cache_hits: int
    bound_time_ns: int
    independent_bound_time_ns: int
    chain_dp_time_ns: int
    uac_dp_time_ns: int
    membership_time_ns: int
    scoring_time_ns: int
    total_time_ns: int
    stop_min_shell: int
    stop_max_shell: int
    max_shell_entered: int
    max_histories: int
    complete: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def decode_exact_search(
    *,
    y: int,
    code: BinaryCode,
    odds_denominator: int,
    bound_mode: str,
    max_histories: int,
    alignment_weights: Sequence[int] | None = None,
    alignment_schedule: str = "forward",
) -> DecodeResult:
    """Run deterministic exact inverse-alignment search.

    Bound hierarchy:
      independent: U_ind only;
      chain_relaxed: U_ind, then the O(n^2) recurrence-only U_CR;
      alignment_consistent: U_ind, then U_CR, then the exact O(n^3) U_AC.

    Each stronger bound is evaluated lazily only when an incumbent exists and all
    cheaper bounds fail. Since U_AC <= U_CR <= U_ind, the hierarchy preserves the
    earliest exact certificate available to the selected mode while avoiding
    unnecessary DP work.

    Coordinate 0 is the least-significant bit. Within each mismatch shell,
    substitution masks are lexicographic by coordinate tuple, then deleted bit
    b=0,1, then the selected alignment tie order. Every bound mode in a paired
    trial uses the identical schedule.
    """
    allowed = {"independent", "chain_relaxed", "alignment_consistent"}
    if bound_mode not in allowed:
        raise ValueError(f"bound_mode must be one of {sorted(allowed)}")
    n = code.n
    if alignment_schedule == "forward":
        alignment_order = tuple(range(n))
    elif alignment_schedule == "even_odd":
        alignment_order = tuple(range(0, n, 2)) + tuple(range(1, n, 2))
    else:
        raise ValueError("alignment_schedule must be forward or even_odd")
    m = n - 1
    if alignment_weights is None:
        alignment_weights = (1,) * n
    if len(alignment_weights) != n:
        raise ValueError("alignment weight length mismatch")

    start_ns = time.perf_counter_ns()
    seen: set[int] = set()
    tie_words: set[int] = set()
    incumbent_score = -1
    frontier = [0] * n
    current_ind_bound = independent_bound_int(frontier, n, odds_denominator, alignment_weights)
    current_bound = current_ind_bound
    chain_cache: dict[tuple[int, ...], int] = {}
    uac_cache: dict[tuple[int, ...], int] = {}

    q_hist = q_disc = q_code = q_score = 0
    frontier_updates = 0
    bound_calls = independent_bound_calls = chain_dp_calls = uac_dp_calls = 0
    chain_skipped_proven_equal = 0
    chain_cache_hits = uac_cache_hits = 0
    bound_time_ns = independent_bound_time_ns = chain_dp_time_ns = uac_dp_time_ns = 0
    membership_time_ns = scoring_time_ns = 0
    max_shell_entered = 0

    def refresh_independent_bound() -> int:
        nonlocal current_ind_bound, independent_bound_calls
        nonlocal independent_bound_time_ns, bound_time_ns
        independent_bound_calls += 1
        t0 = time.perf_counter_ns()
        current_ind_bound = independent_bound_int(tuple(frontier), n, odds_denominator, alignment_weights)
        elapsed = time.perf_counter_ns() - t0
        independent_bound_time_ns += elapsed
        bound_time_ns += elapsed
        return current_ind_bound

    def get_chain_bound(key: tuple[int, ...]) -> int:
        nonlocal chain_dp_calls, chain_cache_hits, chain_dp_time_ns, bound_time_ns
        cached = chain_cache.get(key)
        if cached is not None:
            chain_cache_hits += 1
            return cached
        chain_dp_calls += 1
        t0 = time.perf_counter_ns()
        value = chain_relaxed_dp_int(y, key, n, odds_denominator, alignment_weights)
        elapsed = time.perf_counter_ns() - t0
        chain_dp_time_ns += elapsed
        bound_time_ns += elapsed
        chain_cache[key] = value
        return value


    def chain_equals_independent_by_forward_prefix(key: tuple[int, ...]) -> bool:
        """Recognize the frontier family covered by the exact degeneracy theorem."""
        low = min(key)
        high = max(key)
        if high > m:
            return False
        if high == low:
            return True
        if high != low + 1:
            return False
        seen_low = False
        for value in key:
            if value == low:
                seen_low = True
            elif value == high:
                if seen_low:
                    return False
            else:
                return False
        return True

    def get_uac_bound(key: tuple[int, ...]) -> int:
        nonlocal uac_dp_calls, uac_cache_hits, uac_dp_time_ns, bound_time_ns
        cached = uac_cache.get(key)
        if cached is not None:
            uac_cache_hits += 1
            return cached
        uac_dp_calls += 1
        t0 = time.perf_counter_ns()
        value = uac_dp_optimized_int(y, key, n, odds_denominator, alignment_weights)
        elapsed = time.perf_counter_ns() - t0
        uac_dp_time_ns += elapsed
        bound_time_ns += elapsed
        uac_cache[key] = value
        return value

    def try_certificate(ind_bound_is_current: bool) -> bool:
        """Return True only under a strict exact certificate."""
        nonlocal current_bound, bound_calls
        if incumbent_score < 0:
            return False
        bound_calls += 1
        ind = current_ind_bound if ind_bound_is_current else refresh_independent_bound()
        current_bound = ind
        if incumbent_score > ind:
            return True
        if bound_mode == "independent":
            return False

        key = tuple(frontier)
        nonlocal chain_skipped_proven_equal
        if chain_equals_independent_by_forward_prefix(key):
            chain = ind
            chain_skipped_proven_equal += 1
        else:
            chain = get_chain_bound(key)
        current_bound = chain
        if incumbent_score > chain:
            return True
        if bound_mode == "chain_relaxed":
            return False

        uac = get_uac_bound(key)
        current_bound = uac
        return incumbent_score > uac

    def finish(status: str, complete: bool, q_hist_value: int | None = None) -> DecodeResult:
        elapsed = time.perf_counter_ns() - start_ns
        qh = q_hist if q_hist_value is None else q_hist_value
        score = max(incumbent_score, 0)
        return DecodeResult(
            bound_mode=bound_mode,
            alignment_schedule=alignment_schedule,
            status=status,
            decoded_word=min(tie_words) if tie_words else None,
            tie_words=tuple(sorted(tie_words)),
            incumbent_score=score,
            final_bound=current_bound,
            stopping_margin=(incumbent_score - current_bound) if incumbent_score >= 0 else -current_bound,
            q_hist=qh,
            q_disc=q_disc,
            q_code=q_code,
            q_score=q_score,
            duplicate_count=qh - q_disc,
            duplicate_fraction=(qh - q_disc) / qh if qh else 0.0,
            frontier_updates=frontier_updates,
            bound_calls=bound_calls,
            independent_bound_calls=independent_bound_calls,
            chain_dp_calls=chain_dp_calls,
            chain_skipped_proven_equal=chain_skipped_proven_equal,
            uac_dp_calls=uac_dp_calls,
            chain_cache_hits=chain_cache_hits,
            uac_cache_hits=uac_cache_hits,
            bound_time_ns=bound_time_ns,
            independent_bound_time_ns=independent_bound_time_ns,
            chain_dp_time_ns=chain_dp_time_ns,
            uac_dp_time_ns=uac_dp_time_ns,
            membership_time_ns=membership_time_ns,
            scoring_time_ns=scoring_time_ns,
            total_time_ns=elapsed,
            stop_min_shell=min(frontier),
            stop_max_shell=max(frontier),
            max_shell_entered=max_shell_entered,
            max_histories=max_histories,
            complete=complete,
        )

    for shell in range(m + 1):
        max_shell_entered = shell
        shell_masks = masks_of_weight(m, shell)
        if not shell_masks:
            continue
        last_mask_index = len(shell_masks) - 1
        for mask_index, error_mask in enumerate(shell_masks):
            altered = y ^ error_mask
            for deleted_bit in (0, 1):
                final_local_component = mask_index == last_mask_index and deleted_bit == 1
                for j in alignment_order:
                    q_hist += 1
                    if q_hist > max_histories:
                        return finish("CENSORED_MAX_HISTORIES", False, q_hist - 1)

                    x = insert_bit(altered, j, deleted_bit)
                    incumbent_changed = False
                    if x not in seen:
                        seen.add(x)
                        q_disc += 1
                        q_code += 1
                        t_mem = time.perf_counter_ns()
                        is_codeword = code.is_codeword(x)
                        membership_time_ns += time.perf_counter_ns() - t_mem
                        if is_codeword:
                            q_score += 1
                            t_score = time.perf_counter_ns()
                            score = scaled_score_int(x, y, n, odds_denominator, alignment_weights)
                            scoring_time_ns += time.perf_counter_ns() - t_score
                            if score > incumbent_score:
                                incumbent_score = score
                                tie_words = {x}
                                incumbent_changed = True
                            elif score == incumbent_score and x not in tie_words:
                                tie_words.add(x)

                    if final_local_component:
                        frontier[j] = shell + 1
                        frontier_updates += 1
                        refresh_independent_bound()
                        if incumbent_score >= 0 and try_certificate(ind_bound_is_current=True):
                            return finish("CERTIFIED", True)
                    elif incumbent_changed:
                        if try_certificate(ind_bound_is_current=True):
                            return finish("CERTIFIED", True)

    current_bound = 0
    return finish("EXHAUSTED", True)
