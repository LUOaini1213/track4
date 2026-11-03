"""The stopping controller knows the 10-turn cap: it stops deferring at turn 9.

README.md says the controller never reads the evaluator's remaining-turn count
or the target, but that every deferral rule switches off from turn 9 on. This
pins both halves for the frozen PUBLIC configuration: the same state that
defers at turn 8 recommends at turn 9, and the deciding functions take no
argument that could carry the remaining budget or the target.
"""

from __future__ import annotations

import inspect
import unittest

from starter.shopping_agent.contest_config import PUBLIC
from starter.shopping_agent.contest_rank import (
    defer_for_ambiguity,
    defer_for_overlap,
    defer_for_progress,
    should_withhold,
)
from starter.shopping_agent.contest_slots import ContestState

CUTOFF = 9


def buying_state(turn: int) -> ContestState:
    """One disclosed slot in a Buying session: the E1 extra-question case."""
    state = ContestState(session_id="s", scenario="buying", turn=turn)
    state.add_constraints(["cotton"], turn=1)
    return state


class TurnCutoffTests(unittest.TestCase):
    def test_public_runs_the_progress_rules(self) -> None:
        self.assertEqual(PUBLIC.progress_defer, "e123")
        self.assertEqual(PUBLIC.gate_size, 5)

    def test_progress_deferral_fires_before_the_cutoff_and_never_after(self) -> None:
        # Pool of 3 is under gate_size=5 with 1 of 4 slots disclosed: E1 asks once more.
        for turn in range(1, CUTOFF):
            with self.subTest(turn=turn):
                self.assertTrue(defer_for_progress(buying_state(turn), PUBLIC, 3))
        for turn in range(CUTOFF, 11):
            with self.subTest(turn=turn):
                self.assertFalse(defer_for_progress(buying_state(turn), PUBLIC, 3))

    def test_pool_gate_withholds_before_the_cutoff_and_never_after(self) -> None:
        # A browsing session with nothing disclosed and a pool far above gate_size.
        def state(turn: int) -> ContestState:
            return ContestState(session_id="g", scenario="browsing", turn=turn)

        for turn in range(1, CUTOFF):
            with self.subTest(turn=turn):
                self.assertTrue(should_withhold(state(turn), PUBLIC, 100, 100))
        for turn in range(CUTOFF, 11):
            with self.subTest(turn=turn):
                self.assertFalse(should_withhold(state(turn), PUBLIC, 100, 100))

    def test_deciding_functions_take_no_budget_or_target_argument(self) -> None:
        for function in (should_withhold, defer_for_progress, defer_for_ambiguity, defer_for_overlap):
            with self.subTest(function=function.__name__):
                names = set(inspect.signature(function).parameters)
                self.assertFalse(names & {"remain", "remaining", "target", "target_asin"}, names)


if __name__ == "__main__":
    unittest.main()
