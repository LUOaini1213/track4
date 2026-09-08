"""The value-of-information controller: it may withhold a recommendation, it
never changes one, and it never reads the turn budget, the target or the card.

Two kinds of evidence. Behavioural: ``rank()`` returns the same list whether
the controller has run or not, and the controller leaves the state untouched.
Structural: the controller module has no path to ``rank()`` or to anything
that knows the answer, checked against its source.
"""

from __future__ import annotations

import ast
import inspect
import json
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from starter.shopping_agent import contest_voi
from starter.shopping_agent.contest_config import PUBLIC
from starter.shopping_agent.contest_index import ContestIndex
from starter.shopping_agent.contest_rank import candidate_pool, hard_pool, rank
from starter.shopping_agent.contest_slots import ContestState
from starter.shopping_agent.contest_voi import (
    defer_for_ambiguity,
    defer_for_overlap,
    defer_for_progress,
    should_withhold,
)


def _catalog_rows() -> list[dict]:
    rows = []
    materials = ["leather", "leather", "canvas", "leather", "nylon", "leather", "leather", "canvas"]
    for i, material in enumerate(materials):
        rows.append(
            {
                "parent_asin": f"BELT{i:03d}",
                "title": f"{material.title()} men's belt with buckle closure style {i}",
                "features": [f"{material}", "buckle closure", "imported"],
                "description": [f"a {material} belt"],
                "categories": ["Clothing", "Accessories", "Belts"],
                "details": {"department": "mens", "material": material},
                "store": f"Store{i % 3}",
                "price": 20.0 + i,
                "average_rating": 4.0 + (i % 5) / 10,
                "rating_number": 1000 - 100 * i,
            }
        )
    return rows


class _Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        path = Path(cls.tempdir.name) / "catalog.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in _catalog_rows()), encoding="utf-8")
        cls.index = ContestIndex(path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def _state(self, turn: int = 2, scenario: str = "buying") -> ContestState:
        state = ContestState(session_id="s", profile={})
        state.category = "Accessories Belts"
        state.scenario = scenario
        state.turn = turn
        state.add_constraints(["buckle closure", "leather"], turn=1, provisional=True)
        return state


class ControllerDoesNotTouchRanking(_Fixture):
    def test_rank_is_identical_before_and_after_the_controller_runs(self) -> None:
        state = self._state()
        pool = candidate_pool(self.index, state, PUBLIC)
        working = hard_pool(self.index, state, pool, selective=PUBLIC.hard_selective) or list(pool)
        before = rank(self.index, state, PUBLIC, working, limit=24)
        snapshot = asdict(state)
        should_withhold(state, PUBLIC, len(pool), len(working))
        defer_for_overlap(self.index, state, PUBLIC, working)
        defer_for_ambiguity(self.index, state, PUBLIC, working)
        defer_for_progress(state, PUBLIC, len(working))
        after = rank(self.index, state, PUBLIC, working, limit=24)
        self.assertEqual(before, after)
        self.assertEqual(asdict(state), snapshot, "the controller must not mutate the state")

    def test_turn_nine_is_a_floor_every_function_respects(self) -> None:
        # At turn 9 of 10 the agent recommends what it has, whatever the pool.
        state = self._state(turn=9)
        pool = candidate_pool(self.index, state, PUBLIC)
        many = list(range(len(self.index)))
        self.assertFalse(should_withhold(state, PUBLIC, len(many) * 50, len(many) * 50))
        self.assertFalse(defer_for_overlap(self.index, state, PUBLIC, many))
        self.assertFalse(defer_for_ambiguity(self.index, state, PUBLIC, many))
        self.assertFalse(defer_for_progress(state, PUBLIC, len(many)))
        self.assertTrue(pool)  # the pool itself is unaffected by the turn

    def test_a_pool_wider_than_the_gate_withholds_and_a_narrow_one_with_enough_slots_does_not(self) -> None:
        state = self._state(turn=2)
        gate = PUBLIC.gate_size
        self.assertTrue(should_withhold(state, PUBLIC, gate + 10, gate + 10))
        state.add_constraints(["brown"], turn=2, provisional=False)
        self.assertGreaterEqual(len(state.active), PUBLIC.min_slots_to_recommend)
        self.assertFalse(should_withhold(state, PUBLIC, gate, gate))

    def test_progress_deferral_fires_once_per_session(self) -> None:
        config = replace(PUBLIC, progress_defer="e123")
        state = self._state(turn=2, scenario="buying")
        self.assertTrue(defer_for_progress(state, config, 3))
        state.progress_deferred = True  # what ContestAgent records after using it
        self.assertFalse(defer_for_progress(state, config, 3))


class ControllerIsStructurallyBlind(unittest.TestCase):
    def test_module_never_references_the_ranker_the_target_or_the_budget(self) -> None:
        # Identifiers only (names, attributes, imports): docstrings are allowed
        # to say what the module does not do; the code must not do it.
        source = inspect.getsource(contest_voi)
        tree = ast.parse(source)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.alias):
                identifiers.add(node.name.split(".")[-1])
                if node.asname:
                    identifiers.add(node.asname)
        forbidden = {
            "rank": "the ranking function",
            "MAX_TURNS": "the evaluator's turn budget",
            "remaining": "any notion of turns left",
            "ground_truth": "the answer",
            "intent_card": "the hidden card",
            "target": "the answer",
        }
        for name, why in forbidden.items():
            with self.subTest(identifier=name):
                offenders = sorted(i for i in identifiers if name in i)
                self.assertEqual(offenders, [], f"contest_voi.py references {why}: {offenders}")
        self.assertIn("state.turn >= 9", source)


if __name__ == "__main__":
    unittest.main()
