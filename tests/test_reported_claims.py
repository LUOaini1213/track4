"""Recompute every number README.md reports from the committed artifacts.

The rest of the suite proves the agent imports and runs with no catalog, no
keys and no third-party packages. It says nothing about whether the score table
in README.md is still the arithmetic result of the session records in this
repository -- so before this file existed, editing a digit in that table left
the CI badge green.

Each test walks the same three steps a sceptical reader would:

1. parse the claim out of README.md, anchored to its own block so the
   with-MiniLM table and the no-MiniLM table can never be confused;
2. compare it with the aggregate the result file already stores at top level;
3. recompute that aggregate from the per-session (or per-shard) records in the
   same file, through ``evaluator.local_evaluator.metric_summary`` rather than
   a second copy of the formulas, so that changing the evaluator also has to
   move the reported numbers.

Rank-1 counts are not stored as aggregates anywhere; they only ever come from
step 3. The last class checks the one non-numeric README claim that fails the
same way -- the Branches table, which used to send a reader to a branch that
does not exist. Standard library only, no catalog, no network: this runs under
``python -S`` in CI on both Linux and Windows.
"""

from __future__ import annotations

import json
import re
import statistics
import unittest
from pathlib import Path

from evaluator.local_evaluator import metric_summary

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
PLACES = 6

SCORE_TABLE_HEADER = ["Set", "n", "Hit@10", "MRR", "MTTC", "TechnicalScore", "Rank-1"]
SOURCE_TABLE_HEADER = ["Row", "Source of every number in it"]
NODENSE_TABLE_HEADER = ["Set", "With MiniLM", "Without MiniLM"]
BRANCH_TABLE_HEADER = ["Branch", "`starter.agent.Agent`", "Purpose"]
SUBMISSION_TIME_DOCS = (
    "report/freeze.md",
    "report/submit.md",
    "SUBMISSION_CHECKLIST.md",
    "report/devpost_description.md",
)


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_table(header: list[str]) -> list[list[str]]:
    """Return the body rows of the one table in README.md with this header."""
    lines = README.splitlines()
    matches = [i for i, line in enumerate(lines) if line.startswith("|") and cells(line) == header]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one table headed {header}, found {len(matches)}")
    rows = []
    for line in lines[matches[0] + 2:]:  # +2 skips the |---| separator
        if not line.startswith("|"):
            break
        rows.append(cells(line))
    return rows


def number(cell: str) -> float | None:
    """Read one score-table cell. ``—`` means the row does not report it."""
    text = cell.replace("*", "").replace(",", "").strip()
    if text in {"", "—", "-", "n/a"}:
        return None
    return float(text)


def path_in(cell: str) -> Path:
    """First `backticked` path in a source-table cell."""
    quoted = re.findall(r"`([^`]+)`", cell)
    if not quoted:
        raise AssertionError(f"no backticked source in {cell!r}")
    return ROOT / quoted[0]


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def efficiency_of(mttc: float) -> float:
    return max(0.0, min(1.0, (11.0 - float(mttc)) / 10.0))


def recompute(sessions: list[dict]) -> dict:
    """The evaluator's own aggregation, including its rounding order.

    ``metric_summary`` rounds hit/mrr/mttc to 6 places and the technical score
    is then built from those rounded values -- recomputing it from raw
    reciprocal ranks instead moves the holdout score from 0.911753 to 0.911754.
    """
    summary = metric_summary(sessions)
    efficiency = efficiency_of(summary["mttc"])
    return {
        "n": summary["sample_count"],
        "hit": summary["hit_rate_at_10"],
        "mrr": summary["mrr"],
        "mttc": summary["mttc"],
        "efficiency": round(efficiency, PLACES),
        "score": round(
            0.50 * summary["hit_rate_at_10"] + 0.30 * summary["mrr"] + 0.20 * efficiency, PLACES
        ),
        "rank1": sum(1 for item in sessions if item.get("best_rank") == 1),
    }


class ScoreTableTests(unittest.TestCase):
    """README.md's headline table, row by row, against its declared source."""

    def setUp(self) -> None:
        self.rows = {row[0]: row for row in markdown_table(SCORE_TABLE_HEADER)}
        self.sources = {row[0]: path_in(row[1]) for row in markdown_table(SOURCE_TABLE_HEADER)}

    def test_every_scored_row_declares_exactly_one_source_file(self) -> None:
        self.assertEqual(sorted(self.rows), sorted(self.sources))
        for label, path in self.sources.items():
            with self.subTest(row=label):
                self.assertTrue(path.is_file(), f"{label} points at a missing {path}")

    def _assert_row(self, label: str, source: str, computed: dict) -> None:
        self.assertEqual(self.sources[label], ROOT / source, f"{label} must be sourced from {source}")
        row = self.rows[label]
        reported = dict(zip(SCORE_TABLE_HEADER, row))
        self.assertEqual(int(number(reported["n"])), computed["n"])
        for column, key in (("Hit@10", "hit"), ("MRR", "mrr"), ("MTTC", "mttc"),
                            ("TechnicalScore", "score"), ("Rank-1", "rank1")):
            claimed = number(reported[column])
            if claimed is None:
                continue
            with self.subTest(row=label, column=column):
                self.assertAlmostEqual(claimed, computed[key], places=PLACES)

    def _assert_stored_aggregate_matches(self, payload: dict, computed: dict) -> None:
        """Step 2: the file's own top-level aggregate is the sessions' result."""
        self.assertEqual(payload["sample_count"], computed["n"])
        self.assertAlmostEqual(payload["hit_rate_at_10"], computed["hit"], places=PLACES)
        self.assertAlmostEqual(payload["mrr"], computed["mrr"], places=PLACES)
        self.assertAlmostEqual(payload["mttc"], computed["mttc"], places=PLACES)
        self.assertAlmostEqual(payload["efficiency"], computed["efficiency"], places=PLACES)
        self.assertAlmostEqual(
            payload["recommended_technical_score"], computed["score"], places=PLACES
        )

    def test_public_row_is_the_200_committed_public_sessions(self) -> None:
        source = "results_contest_public.json"
        payload = load(ROOT / source)
        computed = recompute(payload["sessions"])
        self._assert_stored_aggregate_matches(payload, computed)
        self._assert_row("Public (labelled)", source, computed)
        usage = payload["reported_token_usage"]
        self.assertEqual((usage["prompt_tokens"], usage["completion_tokens"]), (0, 0))

    def test_holdout_row_is_the_200_committed_holdout_sessions(self) -> None:
        source = "holdout/ours_holdout.json"
        payload = load(ROOT / source)
        computed = recompute(payload["sessions"])
        self._assert_stored_aggregate_matches(payload, computed)
        self._assert_row("Our ID-disjoint holdout", source, computed)

    def test_random_800_row_is_the_pooled_mean_of_the_eight_committed_shards(self) -> None:
        source = "holdout/shards/a_vs_e123.json"
        payload = load(ROOT / source)
        shards = payload["rows"]
        self.assertEqual(len(shards), 8)
        self.assertEqual(sum(shard["n"] for shard in shards), 800)
        pooled = payload["pooled_mean_of_shards"]["e123"]
        # Step 3 for a file of shard summaries: the pooled row must be the mean
        # of the eight, and Rank-1 their sum.
        for key in ("hit", "mrr", "mttc", "score"):
            with self.subTest(metric=key):
                mean = statistics.fmean(shard["e123"][key] for shard in shards)
                self.assertAlmostEqual(pooled[key], round(mean, PLACES), places=PLACES)
        self.assertEqual(pooled["rank1"], sum(shard["e123"]["rank1"] for shard in shards))
        self._assert_row("Random 800, 8×100 shards", source, {
            "n": sum(shard["n"] for shard in shards),
            "hit": pooled["hit"],
            "mrr": pooled["mrr"],
            "mttc": pooled["mttc"],
            "score": pooled["score"],
            "rank1": pooled["rank1"],
        })

    def test_bm25_reference_row_is_the_committed_baseline(self) -> None:
        source = "docs/baseline_results.json"
        payload = load(ROOT / source)
        self._assert_row("Weak BM25 starter (reference)", source, {
            "n": payload["sample_count"],
            "hit": payload["hit_rate_at_10"],
            "mrr": payload["mrr"],
            "mttc": payload["mttc"],
            "score": payload["technical_score"],
            "rank1": None,
        })
        self.assertAlmostEqual(
            payload["technical_score"],
            round(0.50 * payload["hit_rate_at_10"] + 0.30 * payload["mrr"]
                  + 0.20 * efficiency_of(payload["mttc"]), PLACES),
            places=PLACES,
        )


class HeadlineClaimTests(unittest.TestCase):
    """"+60 rank-1 ... zero Hit-rate loss ... 8 of 8" in the opening paragraph."""

    def setUp(self) -> None:
        self.payload = load(ROOT / "holdout" / "shards" / "a_vs_e123.json")
        self.headline = " ".join(README.split("**Headline result:**", 1)[1].split("\n\n", 1)[0].split())

    def test_rank1_gain_hit_parity_and_shard_sweep_match_the_shard_table(self) -> None:
        pooled = self.payload["pooled_mean_of_shards"]
        gain = int(re.search(r"\+(\d+) rank-1", self.headline).group(1))
        self.assertEqual(gain, pooled["e123"]["rank1"] - pooled["A"]["rank1"])
        # "zero Hit-rate loss" is a claim about Hit@10, not about the score.
        self.assertIn("zero Hit-rate loss", self.headline)
        self.assertAlmostEqual(pooled["e123"]["hit"], pooled["A"]["hit"], places=PLACES)
        won, total = (int(part) for part in re.search(r"\*\*(\d+) of (\d+)\*\* shards", self.headline).groups())
        rows = self.payload["rows"]
        self.assertEqual(total, len(rows))
        self.assertEqual(won, sum(1 for row in rows if row["e123_wins"]))
        self.assertEqual(won, self.payload["e123_wins"])
        for row in rows:
            with self.subTest(shard=row["shard"]):
                self.assertEqual(row["e123_wins"], row["e123"]["score"] > row["A"]["score"])
        sessions = int(re.search(r"on (\d+) unseen", self.headline).group(1))
        self.assertEqual(sessions, sum(row["n"] for row in rows))


class NoDenseFallbackTests(unittest.TestCase):
    """The without-MiniLM numbers come from report/freeze_nodense.json, not the main table."""

    def setUp(self) -> None:
        self.payload = load(ROOT / "report" / "freeze_nodense.json")
        self.rows = {row[0]: row for row in markdown_table(NODENSE_TABLE_HEADER)}

    def test_fallback_table_matches_the_frozen_no_dense_run(self) -> None:
        self.assertFalse(self.payload["encoder_available"])
        pairs = {
            "Public 200": (self.payload["public"], load(ROOT / "results_contest_public.json")),
            "Holdout 200": (self.payload["holdout"], load(ROOT / "holdout" / "ours_holdout.json")),
        }
        for label, (nodense, dense) in pairs.items():
            with self.subTest(row=label):
                claimed = dict(zip(NODENSE_TABLE_HEADER, self.rows[label]))
                with_hit, with_score = self._pair(claimed["With MiniLM"])
                without_hit, without_score = self._pair(claimed["Without MiniLM"])
                self.assertAlmostEqual(with_hit, dense["hit_rate_at_10"], places=PLACES)
                self.assertAlmostEqual(with_score, dense["recommended_technical_score"], places=PLACES)
                self.assertAlmostEqual(without_hit, nodense["hit_rate_at_10"], places=PLACES)
                self.assertAlmostEqual(without_score, nodense["recommended_technical_score"], places=PLACES)

    def test_the_standard_library_rerun_paragraph_matches_the_same_file(self) -> None:
        public = self.payload["public"]
        block = README.split("Verified again on", 1)[1].split("\n\n", 1)[0]
        claimed = {
            key: float(value)
            for key, value in re.findall(r"(Hit@10|MRR|MTTC|TechnicalScore)\s+\*\*([0-9.]+)\*\*", block)
        }
        self.assertEqual(sorted(claimed), ["Hit@10", "MRR", "MTTC", "TechnicalScore"])
        self.assertAlmostEqual(claimed["Hit@10"], public["hit_rate_at_10"], places=PLACES)
        self.assertAlmostEqual(claimed["MRR"], public["mrr"], places=PLACES)
        self.assertAlmostEqual(claimed["MTTC"], public["mttc"], places=PLACES)
        self.assertAlmostEqual(
            claimed["TechnicalScore"], public["recommended_technical_score"], places=PLACES
        )
        # The two runs must stay distinguishable: this is a different MRR from
        # the opening table's 0.954167, and the README says so.
        self.assertNotAlmostEqual(
            public["mrr"],
            load(ROOT / "results_contest_public.json")["mrr"],
            places=PLACES,
        )

    def _pair(self, cell: str) -> tuple[float, float]:
        hit, score = cell.replace("*", "").replace("Hit", "").split("/")
        return float(hit), float(score)


class SupersededSnapshotTests(unittest.TestCase):
    """The two older 800-session artifacts, and what README.md says about them."""

    def setUp(self) -> None:
        self.shards = [load(ROOT / "holdout" / "shards" / f"out_{i}.json") for i in range(8)]
        self.compare = load(ROOT / "holdout" / "random800_compare.json")
        self.paragraph = " ".join(
            README.split("Two older artifacts", 1)[1].split("\n\n", 1)[0].split()
        )

    def test_each_superseded_file_says_so_in_its_own_first_field(self) -> None:
        for name, payload in [(f"out_{i}.json", d) for i, d in enumerate(self.shards)] + [
            ("random800_compare.json", self.compare)
        ]:
            with self.subTest(artifact=name):
                self.assertIn("superseded by holdout/shards/a_vs_e123.json", payload["snapshot"])

    def test_readme_quotes_the_superseded_pool_correctly(self) -> None:
        pooled = {
            # Pooled means rounded to 6 places, through the same statistics.fmean
            # the evaluator aggregates with: a plain sum/8 lands on the other
            # side of the rounding boundary for MRR (0.824886 vs 0.824885).
            "Hit": round(statistics.fmean(s["hit_rate_at_10"] for s in self.shards), PLACES),
            "MRR": round(statistics.fmean(s["mrr"] for s in self.shards), PLACES),
            "MTTC": round(statistics.fmean(s["mttc"] for s in self.shards), PLACES),
        }
        row = self.compare["rows"]["random_800"]
        self.assertEqual(row["sample_count"], 800)
        for label, key in (("Hit", "hit_rate_at_10"), ("MRR", "mrr"), ("MTTC", "mttc")):
            with self.subTest(metric=label):
                self.assertAlmostEqual(row[key], pooled[label], places=PLACES)
                claimed = float(re.search(rf"{label} ([0-9.]+)", self.paragraph).group(1))
                self.assertAlmostEqual(claimed, row[key], places=PLACES)
        claimed_score = float(re.search(r"TechnicalScore ([0-9.]+)", self.paragraph).group(1))
        self.assertAlmostEqual(claimed_score, row["recommended_technical_score"], places=PLACES)

    def test_the_superseded_pool_really_differs_from_the_reported_row(self) -> None:
        """Why this paragraph has to exist: the numbers are visibly not the same."""
        reported = load(ROOT / "holdout" / "shards" / "a_vs_e123.json")["pooled_mean_of_shards"]["e123"]
        row = self.compare["rows"]["random_800"]
        self.assertNotAlmostEqual(row["mrr"], reported["mrr"], places=PLACES)
        self.assertNotAlmostEqual(row["recommended_technical_score"], reported["score"], places=PLACES)


class BranchTableTests(unittest.TestCase):
    """The Branches table must describe branches a reader can actually open.

    It used to list ``main`` as "Group integration" and send anyone looking for
    the scored code to ``contest/public``, which 404s: apart from pull-request
    branches this repository has only ``main`` and ``v2/shelf-recall``. The
    check is deliberately offline -- ``git branch -r`` on the shallow
    single-branch CI checkout lists only the branch being built, so it cannot
    be the source of truth here.
    """

    def setUp(self) -> None:
        self.rows = markdown_table(BRANCH_TABLE_HEADER)
        self.branches = [re.sub(r"[`\s]", "", row[0]) for row in self.rows]

    def test_the_table_never_points_at_an_unpublished_branch(self) -> None:
        self.assertNotIn("contest/public", self.branches)
        self.assertNotIn("legacy/qwen", self.branches)

    def test_main_is_the_one_row_marked_as_scored(self) -> None:
        scored = [row for row in self.rows if "scored" in row[2].lower()]
        self.assertEqual(len(scored), 1, "exactly one row may claim to be the scored branch")
        self.assertEqual(re.sub(r"[`\s]", "", scored[0][0]), "main")
        self.assertIn("ContestAgent PUBLIC", scored[0][1])

    def test_the_scored_entry_point_agrees_with_the_table(self) -> None:
        """Not only a claim in markdown: import the entry point and read its MRO."""
        from starter.agent import Agent

        self.assertIn("ContestAgent", [cls.__name__ for cls in Agent.__mro__])

    def test_documents_that_still_say_contest_public_open_with_a_note(self) -> None:
        """Kept as the submission-time record, so each has to say so up front."""
        for name in SUBMISSION_TIME_DOCS:
            with self.subTest(document=name):
                lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
                self.assertIn("contest/public", " ".join(lines))
                self.assertTrue(lines[0].startswith("# "), f"{name} must open with a title")
                note = [line for line in lines[:8] if line.startswith(">")]
                self.assertTrue(note, f"{name} must open with a note about its branch names")
                self.assertIn("main", " ".join(note))


if __name__ == "__main__":
    unittest.main()
