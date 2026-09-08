from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from starter.shopping_agent.contest_config import PUBLIC, SHELF
from starter.shopping_agent.contest_index import ContestIndex
from starter.shopping_agent.contest_rank import candidate_pool
from starter.shopping_agent.contest_slots import ContestState


def _row(asin: str, title: str, leaf: str, rating_number: int) -> dict:
    return {
        "parent_asin": asin,
        "title": title,
        "features": ["cotton"],
        "description": ["everyday wear"],
        "categories": ["Clothing", leaf],
        "details": {"department": "womens"},
        "store": "Store",
        "price": 20.0,
        "average_rating": 4.5,
        "rating_number": rating_number,
    }


class ShelfPoolTests(unittest.TestCase):
    """PUBLIC pads a small shelf with catalog-wide lexical hits; SHELF keeps it."""

    def setUp(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        rows = [
            _row("S1", "Blue cotton shirt", "Shirts", 300),
            _row("S2", "Red cotton shirt", "Shirts", 200),
            _row("S3", "Green cotton shirt", "Shirts", 100),
        ]
        # Decoys on other shelves that share the query vocabulary ("cotton").
        rows += [_row(f"D{i}", f"Cotton boot {i}", "Boots", 50 + i) for i in range(60)]
        path = Path(tempdir.name) / "catalog.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        self.index = ContestIndex(path)

    def _state(self) -> ContestState:
        state = ContestState(session_id="s")
        state.category = "Shirts"
        state.add_constraints(["cotton"], turn=1)
        return state

    def test_public_pads_a_small_shelf_with_lexical_hits(self) -> None:
        self.assertTrue(PUBLIC.pad_small_shelf)
        pool = candidate_pool(self.index, self._state(), PUBLIC)
        ids = [self.index.ids[idx] for idx in pool]
        self.assertEqual(ids[:3], ["S1", "S2", "S3"])
        self.assertGreater(len(ids), 3, "a 3-row shelf is below min_candidates and gets padded")
        self.assertTrue(any(asin.startswith("D") for asin in ids))

    def test_shelf_keeps_the_resolved_shelf_only(self) -> None:
        self.assertFalse(SHELF.pad_small_shelf)
        pool = candidate_pool(self.index, self._state(), SHELF)
        self.assertEqual([self.index.ids[idx] for idx in pool], ["S1", "S2", "S3"])

    def test_shelf_still_falls_back_when_no_shelf_resolves(self) -> None:
        state = ContestState(session_id="s")
        state.category = None
        state.add_constraints(["cotton"], turn=1)
        pool = candidate_pool(self.index, state, SHELF)
        self.assertGreater(len(pool), 0)

    def test_shelf_differs_from_public_by_one_flag_only(self) -> None:
        self.assertEqual(replace(PUBLIC, pad_small_shelf=False), SHELF)


if __name__ == "__main__":
    unittest.main()
