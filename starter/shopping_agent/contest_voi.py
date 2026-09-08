"""Value-of-information stopping: ask one more ``other`` or recommend now.

This module decides *whether* to recommend on this turn; it never decides
*what* to recommend. It has no access to ``rank()``: everything it reads is
the dialogue state (scenario, disclosed slots, whether ``other`` is exhausted,
the turn index), the configuration, and the size or popularity profile of the
current pool. It never reads the intent card, the target, or the remaining
turn budget; the only use of the turn index is the floor at turn 9 (of the
10 allowed), where every function below returns "do not withhold" so the
agent recommends what it has. ``tests/test_voi_controller.py`` pins both
properties.

The functions were moved here verbatim from ``contest_rank.py``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .contest_config import ContestConfig
from .contest_index import ContestIndex
from .contest_rank import (
    _DENSE_GENERIC,
    _HEAD_EPS,
    _TITLE_SKIP,
    distinctive_slot_tokens,
    field_match_scores,
    phrase_title_scores,
    popularity_gap,
)
from .contest_slots import ContestState
from .contest_text import terms

__all__ = [
    "should_withhold",
    "defer_for_overlap",
    "min_slots_shortcut_would_fire",
    "title_top2_overlap",
    "defer_for_ambiguity",
    "defer_for_progress",
]


def should_withhold(
    state: ContestState,
    config: ContestConfig,
    soft_n: int,
    hard_n: int,
) -> bool:
    if config.gate_size <= 0:
        return False
    if state.turn >= 9:
        return False
    if "other" in state.exhausted and state.turn >= 2:
        return False
    if config.gate_before_override and state.scenario == "intent_override" and not state.override_applied:
        return True
    if config.hard_filter and hard_n == 0:
        return False
    working = hard_n if (config.hard_filter and hard_n > 0) else soft_n
    early_ok = not (config.strict_override_gate and state.scenario == "intent_override")
    if (
        early_ok
        and config.min_slots_to_recommend > 0
        and len(state.active) >= config.min_slots_to_recommend
        and 0 < working <= config.evidence_pool_cap
    ):
        return False
    if (
        early_ok
        and config.dump_slots > 0
        and len(state.active) >= config.dump_slots
        and 0 < working <= config.dump_pool_cap
    ):
        return False
    if (
        early_ok
        and config.distinctive_early_cap > 0
        and distinctive_slot_tokens(state.active)
        and 0 < working <= config.distinctive_early_cap
    ):
        return False
    return working > config.gate_size


def defer_for_overlap(
    index: ContestIndex,
    state: ContestState,
    config: ContestConfig,
    working: list[int],
) -> bool:
    """True when an early recommend should wait: top-two popularity overlap.

    Translates D2D's top-overlapping-item test to this protocol.  Does not
    fire once the working pool is already at most gate_size, after ``other``
    is exhausted, on the last turns, or before an override can score.
    """

    if config.overlap_margin <= 0 or config.gate_size <= 0:
        return False
    if state.turn >= 9:
        return False
    if "other" in state.exhausted:
        return False
    if config.gate_before_override and state.scenario == "intent_override" and not state.override_applied:
        return False
    if len(working) <= config.gate_size or len(working) < 2:
        return False
    top = sorted(working, key=lambda idx: -index.popularity(idx))[:2]
    gap = index.popularity(top[0]) - index.popularity(top[1])
    return gap < config.overlap_margin


def _scores_flat(scores: Mapping[int, float] | None) -> bool:
    if not scores:
        return True
    return max(scores.values()) - min(scores.values()) < _HEAD_EPS


def min_slots_shortcut_would_fire(
    state: ContestState,
    config: ContestConfig,
    working_n: int,
) -> bool:
    """True when recommend would happen only because of min_slots, not gate/dump."""

    if config.gate_size <= 0 or config.min_slots_to_recommend <= 0:
        return False
    if config.strict_override_gate and state.scenario == "intent_override":
        return False
    if len(state.active) < config.min_slots_to_recommend:
        return False
    if not (0 < working_n <= config.evidence_pool_cap):
        return False
    if working_n <= config.gate_size:
        return False
    if (
        config.dump_slots > 0
        and len(state.active) >= config.dump_slots
        and working_n <= config.dump_pool_cap
    ):
        return False
    if (
        config.distinctive_early_cap > 0
        and distinctive_slot_tokens(state.active)
        and 0 < working_n <= config.distinctive_early_cap
    ):
        return False
    return True


def title_top2_overlap(index: ContestIndex, pool: Sequence[int]) -> float:
    """Jaccard of distinctive title tokens of the two most popular pool items."""

    if len(pool) < 2:
        return 0.0
    skip = _TITLE_SKIP | _DENSE_GENERIC
    top = sorted(pool, key=lambda idx: (-index.popularity(idx), index.ids[idx]))[:2]

    def bag(idx: int) -> set[str]:
        return {
            token
            for token in terms(index.titles[idx])
            if token not in skip and len(token) >= 3 and not token.isdigit()
        }

    left, right = bag(top[0]), bag(top[1])
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def defer_for_ambiguity(
    index: ContestIndex,
    state: ContestState,
    config: ContestConfig,
    working: Sequence[int],
) -> bool:
    """True when the 3-slot shortcut should wait for one more ``other``.

    Uses only the current hard pool. Does not read the intent card or target.
    """

    key = (config.ambiguity_defer or "").strip().lower()
    if key not in {"a", "b", "c", "d"}:
        return False
    if state.turn >= 9:
        return False
    if "other" in state.exhausted:
        return False
    if config.gate_before_override and state.scenario == "intent_override" and not state.override_applied:
        return False
    if not min_slots_shortcut_would_fire(state, config, len(working)):
        return False
    slots = state.active
    field_map = field_match_scores(index, working, slots) if slots else {}
    if not _scores_flat(field_map):
        return False
    if key == "a":
        return True
    phrase_map = phrase_title_scores(index, working, slots) if slots else {}
    if not _scores_flat(phrase_map):
        return False
    if key == "b":
        return True
    if key == "c":
        gap = config.ambiguity_pop_gap if config.ambiguity_pop_gap > 0 else 0.04
        return popularity_gap(index, working) < gap
    overlap = config.ambiguity_title_overlap if config.ambiguity_title_overlap > 0 else 0.5
    return title_top2_overlap(index, working) >= overlap


def defer_for_progress(
    state: ContestState,
    config: ContestConfig,
    working_n: int,
) -> bool:
    """Withhold one recommend to buy the next ``other`` (card-progress EVI).

    Uses scenario, slot count, pool size, and whether ``other`` already
    returned no-additional. Does not read remain or the target.
    """

    key = (config.progress_defer or "").strip().lower()
    flags = {
        "e1": {"e1"},
        "e2": {"e2"},
        "e3": {"e3"},
        "e12": {"e1", "e2"},
        "e13": {"e1", "e3"},
        "e23": {"e2", "e3"},
        "e123": {"e1", "e2", "e3"},
    }.get(key)
    if not flags:
        return False
    if state.progress_deferred:
        return False
    if state.turn >= 9:
        return False
    if "other" in state.exhausted:
        return False
    if config.gate_before_override and state.scenario == "intent_override" and not state.override_applied:
        return False
    n_slots = len(state.active)
    gate = config.gate_size if config.gate_size > 0 else 5
    if "e1" in flags and state.scenario == "buying" and 1 <= n_slots < 4 and 2 <= working_n <= gate:
        return True
    if "e2" in flags and state.scenario == "browsing" and 1 <= n_slots < 4 and 2 <= working_n <= gate:
        return True
    if "e3" in flags and n_slots == 3 and working_n > gate:
        return True
    return False
