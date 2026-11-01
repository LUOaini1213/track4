from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from demo.run_demo import (
    MINI_CATALOG,
    POOL_EQUIVALENT_ON_MINI,
    SCENARIO_DEFAULTS,
    pick_sample,
    run_session,
)
from starter.agent import Agent
from starter.shopping_agent.contest_config import PUBLIC
from evaluator.local_evaluator import coarse_category


class DemoReplayTests(unittest.TestCase):
    def test_fixture_cli_runs_without_site_packages_or_a_local_catalog(self) -> None:
        script = Path(__file__).resolve().parents[1] / "demo" / "fixture.py"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-S", "-X", "utf8", str(script)], cwd=directory, text=True, encoding="utf-8", capture_output=True, timeout=30)
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Synthetic 2-product runtime demo", result.stdout)
        self.assertIn("HIT turn=1 rank=1", result.stdout)
        self.assertIn("usage prompt=0 completion=0", result.stdout)

    def test_pick_sample_uses_stable_scenario_defaults(self) -> None:
        samples = [
            {"sample_id": "public_0001", "scenario_type": "buying"},
            {"sample_id": "public_0002", "scenario_type": "intent_override"},
            {"sample_id": "public_0006", "scenario_type": "browsing"},
            {"sample_id": "public_0007", "scenario_type": "browsing"},
            {"sample_id": "public_0035", "scenario_type": "boundary"},
        ]
        self.assertEqual(pick_sample(samples, "public_0002", None)["sample_id"], "public_0002")
        # public_0006 comes first in the list, so this also pins that --scenario
        # browsing follows SCENARIO_DEFAULTS rather than "first of that type".
        self.assertEqual(pick_sample(samples, None, "browsing")["sample_id"], "public_0007")
        self.assertEqual(pick_sample(samples, None, "intent_override")["sample_id"], "public_0002")
        self.assertEqual(tuple(sorted(SCENARIO_DEFAULTS.values())), POOL_EQUIVALENT_ON_MINI)

    def test_run_session_hits_buying_target_and_reports_zero_tokens(self) -> None:
        rows = [
            {
                "parent_asin": "TARGET",
                "title": "Blue cotton running shirt",
                "features": ["cotton", "machine wash"],
                "description": ["lightweight"],
                "categories": ["Clothing", "Shirts"],
                "details": {"department": "womens"},
                "store": "Alpha",
                "price": 29.0,
                "average_rating": 4.8,
                "rating_number": 100,
            },
            {
                "parent_asin": "OTHER",
                "title": "Black leather boot",
                "features": ["leather"],
                "description": ["boot"],
                "categories": ["Clothing", "Boots"],
                "details": {"department": "mens"},
                "store": "Beta",
                "price": 89.0,
                "average_rating": 4.0,
                "rating_number": 10,
            },
        ]
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        path = Path(tempdir.name) / "catalog.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        sample = {
            "sample_id": "demo_buy",
            "scenario_type": "buying",
            "user_profile": {
                "purchase_frequency": "3-4 prior purchases",
                "average_prior_rating": 5.0,
                "rating_style": "usually positive",
                "preference_tags": ["comfort"],
                "summary": "Prior purchases emphasize comfort.",
            },
            "ground_truth": {"parent_asin": "TARGET"},
        }
        products = {row["parent_asin"]: row for row in rows}
        categories = {row["parent_asin"]: row["categories"] for row in rows}
        agent = Agent(path)
        outcome = run_session(agent, sample, products, categories)
        self.assertTrue(outcome["hit"])
        self.assertEqual(outcome["tokens"], 0)
        self.assertEqual(outcome["rank"], 1)
        self.assertGreaterEqual(int(outcome["turn"] or 0), 1)


class MiniCatalogFallbackTests(unittest.TestCase):
    """The one demo command a reader runs first must work on a bare clone.

    ``data/catalog.jsonl`` is the organizer's frozen 50,000-item file and is
    git-ignored, so ``demo/run_demo.py`` falls back to the committed slice
    ``data/catalog.mini.jsonl``. These tests keep that path working and keep
    the slice honest about which sessions replay like the full catalog.
    """

    root = Path(__file__).resolve().parents[1]

    def _mini_rows(self) -> list[dict]:
        # Split on "\n" only: product text contains U+2028-style separators
        # that str.splitlines() would treat as line breaks.
        with MINI_CATALOG.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _public_samples(self) -> list[dict]:
        path = self.root / "data" / "public_set.jsonl"
        with path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_every_public_target_is_in_the_slice_so_any_session_resolves(self) -> None:
        rows = self._mini_rows()
        present = {row["parent_asin"] for row in rows}
        targets = {str(s["ground_truth"]["parent_asin"]) for s in self._public_samples()}
        self.assertEqual(len(targets), 200)
        self.assertEqual(sorted(targets - present), [])

    def test_documented_demo_sessions_need_no_padding_from_the_full_catalog(self) -> None:
        """Pool equivalence, checked without the 60 MB file.

        A shelf at or above ``min_candidates`` is never padded from the rest of
        the catalog, and ``scripts/make_mini_catalog.py`` keeps these shelves
        whole, so the replay sees exactly the pool it sees on the full catalog.
        """
        rows = self._mini_rows()
        by_asin = {row["parent_asin"]: row for row in rows}
        samples = {s["sample_id"]: s for s in self._public_samples()}
        shelf_sizes: dict[str, int] = {}
        for row in rows:
            shelf = coarse_category(row.get("categories") or [])
            shelf_sizes[shelf] = shelf_sizes.get(shelf, 0) + 1
        for sample_id in POOL_EQUIVALENT_ON_MINI:
            with self.subTest(session=sample_id):
                self.assertIn(sample_id, samples)
                target = str(samples[sample_id]["ground_truth"]["parent_asin"])
                self.assertIn(target, by_asin)
                shelf = coarse_category(by_asin[target].get("categories") or [])
                self.assertGreaterEqual(shelf_sizes[shelf], PUBLIC.min_candidates)

    def test_run_demo_replays_a_session_with_no_catalog_installed(self) -> None:
        script = self.root / "demo" / "run_demo.py"
        missing = self.root / "data" / "catalog.absent-on-purpose.jsonl"
        self.assertFalse(missing.exists())
        result = subprocess.run(
            [sys.executable, "-S", "-X", "utf8", str(script),
             "--session", "public_0002", "--catalog", str(missing)],
            text=True, encoding="utf-8", capture_output=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("catalog.mini.jsonl", result.stdout)
        self.assertIn("is pool-equivalent on the slice: True", result.stdout)
        self.assertIn("<= TARGET", result.stdout)
        self.assertRegex(result.stdout, r"HIT turn=\d+ rank=\d+")
        self.assertIn("usage prompt=0 completion=0", result.stdout)
