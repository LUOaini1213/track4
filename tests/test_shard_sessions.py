"""The 8x100 A-vs-e123 comparison, recounted from per-session records.

``holdout/shards/a_vs_e123.json`` stores only per-shard aggregates of the
original run. On 2026-11-03 both arms were rerun on the frozen catalog with the
pinned MiniLM weights, once per fixed ``PYTHONHASHSEED`` (``eval_shard.py
--arm A|e123``), and every per-session payload was committed:

    holdout/shards/hashseed<s>/A/out_<i>.json
    holdout/shards/hashseed<s>/e123/out_<i>.json

Ties in the agent's ranking follow str-hash order, so the absolute Hit/MRR of
those reruns can differ from the original row in the third decimal. What the
README headline claims -- rank-1 612 -> 672, the same hit set in both arms,
e123 ahead on 8 of 8 shards -- is recounted here from the sessions of every
rerun. The README sentence quoting the reruns, and ``report/robustness.md``,
are held to the same files. Standard library only; no catalog, no model.
"""

from __future__ import annotations

import json
import re
import statistics
import unittest
from pathlib import Path

from evaluator.local_evaluator import metric_summary

ROOT = Path(__file__).resolve().parents[1]
SHARDS = ROOT / "holdout" / "shards"
ARMS = ("A", "e123")
SEEDS = ("0", "3")
PLACES = 6


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def shard_ids(i: int) -> list[str]:
    with (SHARDS / f"shard_{i}.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line)["sample_id"] for line in handle if line.strip()]


def recount(sessions: list[dict]) -> dict:
    summary = metric_summary(sessions)
    efficiency = max(0.0, min(1.0, (11.0 - summary["mttc"]) / 10.0))
    return {
        "hit": summary["hit_rate_at_10"],
        "mrr": summary["mrr"],
        "mttc": summary["mttc"],
        "score": round(
            0.50 * summary["hit_rate_at_10"] + 0.30 * summary["mrr"] + 0.20 * efficiency, PLACES
        ),
        "rank1": sum(1 for item in sessions if item.get("best_rank") == 1),
        "hits": {item["sample_id"] for item in sessions if item.get("hit")},
    }


def readme_block(marker: str) -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    return " ".join(readme.split(marker, 1)[1].split("\n\n", 1)[0].split())


class ShardSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = load(SHARDS / "a_vs_e123.json")
        cls.runs = {
            seed: {
                arm: [load(SHARDS / f"hashseed{seed}" / arm / f"out_{i}.json") for i in range(8)]
                for arm in ARMS
            }
            for seed in SEEDS
        }

    def test_each_payload_is_the_declared_arm_seed_and_shard(self) -> None:
        for seed, run in self.runs.items():
            for arm in ARMS:
                for i, payload in enumerate(run[arm]):
                    with self.subTest(seed=seed, arm=arm, shard=i):
                        self.assertEqual(payload["arm"], arm)
                        self.assertEqual(payload["pythonhashseed"], seed)
                        self.assertEqual([s["sample_id"] for s in payload["sessions"]], shard_ids(i))
                        usage = payload["reported_token_usage"]
                        self.assertEqual((usage["prompt_tokens"], usage["completion_tokens"]), (0, 0))
                        computed = recount(payload["sessions"])
                        self.assertAlmostEqual(payload["mrr"], computed["mrr"], places=PLACES)
                        self.assertAlmostEqual(
                            payload["recommended_technical_score"], computed["score"], places=PLACES
                        )

    def test_rank1_per_shard_matches_the_original_summary_in_every_rerun(self) -> None:
        for seed, run in self.runs.items():
            for arm in ARMS:
                for row, payload in zip(self.summary["rows"], run[arm]):
                    with self.subTest(seed=seed, arm=arm, shard=row["shard"]):
                        self.assertEqual(row[arm]["rank1"], recount(payload["sessions"])["rank1"])
                with self.subTest(seed=seed, arm=arm, pooled=True):
                    total = sum(recount(p["sessions"])["rank1"] for p in run[arm])
                    self.assertEqual(total, self.summary["pooled_mean_of_shards"][arm]["rank1"])

    def test_both_arms_hit_the_same_sessions_and_e123_wins_every_shard(self) -> None:
        for seed, run in self.runs.items():
            wins = 0
            for i in range(8):
                a = recount(run["A"][i]["sessions"])
                e = recount(run["e123"][i]["sessions"])
                with self.subTest(seed=seed, shard=i):
                    self.assertEqual(a["hits"], e["hits"])
                wins += e["score"] > a["score"]
            with self.subTest(seed=seed):
                self.assertEqual(wins, self.summary["e123_wins"])

    def test_readme_quotes_the_reruns_correctly(self) -> None:
        block = readme_block("The Random-800 comparison is also committed")
        quoted = re.findall(r"`PYTHONHASHSEED=(\d)`: Hit@10 ([0-9]+\.[0-9]+), MRR ([0-9]+\.[0-9]+)", block)
        self.assertEqual(sorted(seed for seed, _, _ in quoted), sorted(SEEDS))
        for seed, hit, mrr in quoted:
            payloads = self.runs[seed]["e123"]
            pooled_hit = round(statistics.fmean(p["hit_rate_at_10"] for p in payloads), PLACES)
            pooled_mrr = round(statistics.fmean(p["mrr"] for p in payloads), PLACES)
            with self.subTest(seed=seed):
                self.assertEqual(sum(len(p["sessions"]) for p in payloads), 800)
                self.assertAlmostEqual(float(hit), pooled_hit, places=PLACES)
                self.assertAlmostEqual(float(mrr), pooled_mrr, places=PLACES)

    def test_readme_headline_quotes_the_pooled_comparison(self) -> None:
        headline = readme_block("**Headline result:**")
        pooled = self.summary["pooled_mean_of_shards"]
        before, after = (int(x) for x in re.search(r"\((\d+) → (\d+)\)", headline).groups())
        self.assertEqual((before, after), (pooled["A"]["rank1"], pooled["e123"]["rank1"]))
        mttc_a, mttc_e = (float(x) for x in re.search(r"MTTC ([0-9.]+) → ([0-9.]+)", headline).groups())
        self.assertAlmostEqual(mttc_a, pooled["A"]["mttc"], places=PLACES)
        self.assertAlmostEqual(mttc_e, pooled["e123"]["mttc"], places=PLACES)


class RobustnessReportTests(unittest.TestCase):
    """report/robustness.md, rounded to 4 places, against the same summary."""

    def setUp(self) -> None:
        self.text = (ROOT / "report" / "robustness.md").read_text(encoding="utf-8")
        self.summary = load(SHARDS / "a_vs_e123.json")

    def _table(self) -> list[list[str]]:
        rows = []
        for line in self.text.splitlines():
            if line.startswith("|") and not line.startswith("|---") and "shard" not in line:
                rows.append([c.strip().replace("*", "") for c in line.strip().strip("|").split("|")])
        return rows

    def test_per_shard_rows_and_pooled_row_match(self) -> None:
        rows = self._table()
        self.assertEqual(len(rows), 9)
        expected = list(self.summary["rows"]) + [None]
        for cells, row in zip(rows, expected):
            if row is None:
                a = self.summary["pooled_mean_of_shards"]["A"]
                e = self.summary["pooled_mean_of_shards"]["e123"]
            else:
                self.assertEqual(int(cells[0]), row["shard"])
                a, e = row["A"], row["e123"]
            with self.subTest(row=cells[0]):
                values = [float(x) for x in cells[1:8]]
                wanted = [a["hit"], a["mrr"], a["score"], e["hit"], e["mrr"], e["score"],
                          e["score"] - a["score"]]
                for got, want in zip(values, wanted):
                    # A 4-place rounding of the stored value, either way at a tie.
                    self.assertLessEqual(abs(got - want), 0.5e-4 + 1e-9, (got, want))
                self.assertEqual(cells[8], f"{a['rank1']}→{e['rank1']}")

    def test_english_summary_quotes_the_pooled_numbers(self) -> None:
        block = " ".join(self.text.split("**English summary.**", 1)[1].split("\n\n", 1)[0].split())
        pooled = self.summary["pooled_mean_of_shards"]
        self.assertIn(f"{self.summary['e123_wins']} of {self.summary['shards']} shards", block)
        for label, key, places in (("MRR", "mrr", 4), ("MTTC", "mttc", 2)):
            match = re.search(rf"{label} \((?:pooled )?([0-9.]+) → ([0-9.]+)", block)
            tolerance = 0.5 * 10 ** -places + 1e-9
            with self.subTest(metric=label):
                self.assertLessEqual(abs(float(match.group(1)) - pooled["A"][key]), tolerance)
                self.assertLessEqual(abs(float(match.group(2)) - pooled["e123"][key]), tolerance)
        a, e = (int(x) for x in re.search(r"rank-1 \((\d+) → (\d+)\)", block).groups())
        self.assertEqual((a, e), (pooled["A"]["rank1"], pooled["e123"]["rank1"]))


if __name__ == "__main__":
    unittest.main()
