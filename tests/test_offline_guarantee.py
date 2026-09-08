"""The headline operational claim, executed: the scored agent runs whole
sessions with the network physically unavailable and reports 0 tokens.

Every socket constructor is patched to raise for the duration of the test, so
any attempt to reach a model API or the Hugging Face Hub fails loudly instead
of silently succeeding on a developer machine that happens to be online. The
sessions are the four documented demo sessions replayed on the committed mini
catalog, which keeps their whole shelves, so their outcomes are the ones in
report/demo_*.txt.
"""

from __future__ import annotations

import os
import socket
import unittest
from pathlib import Path
from unittest import mock

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "data" / "catalog.mini.jsonl"
PUBLIC_SET = ROOT / "data" / "public_set.jsonl"
DOCUMENTED = ("public_0001", "public_0002", "public_0007", "public_0035")
# From report/demo_buying.txt and demo_override.txt. The boundary session
# (public_0035) hits at rank 1 too, but the simulator draws its boundary turn
# from an RNG, so only the hit is asserted for it.
EXPECTED_HIT_TURN = {"public_0001": 2, "public_0002": 4}
EXPECTED_RANK1 = ("public_0001", "public_0002", "public_0035")


def _no_network(*_args, **_kwargs):
    raise AssertionError("network access attempted during an offline session")


class OfflineZeroTokenGuarantee(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not MINI.exists() or not PUBLIC_SET.exists():
            raise unittest.SkipTest("data/catalog.mini.jsonl or data/public_set.jsonl missing")
        cls.samples = [s for s in load_jsonl(PUBLIC_SET) if s["sample_id"] in DOCUMENTED]

    def test_documented_sessions_complete_with_sockets_disabled_and_zero_tokens(self) -> None:
        self.assertEqual(len(self.samples), len(DOCUMENTED))
        env = {"TECHJAM_DENSE_OFFLINE": "1"}
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(socket, "socket", side_effect=_no_network), \
                mock.patch.object(socket, "create_connection", side_effect=_no_network), \
                mock.patch.object(socket, "getaddrinfo", side_effect=_no_network):
            catalog_ids, categories, products = catalog_index(MINI)
            agent = Agent(MINI)
            payload = evaluate(agent, self.samples, catalog_ids, categories, products)

        self.assertEqual(payload["sample_count"], len(DOCUMENTED))
        self.assertEqual(payload["reported_token_usage"],
                         {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        by_id = {s["sample_id"]: s for s in payload["sessions"]}
        for sample_id in EXPECTED_RANK1:
            with self.subTest(sample=sample_id):
                self.assertTrue(by_id[sample_id]["hit"], f"{sample_id} missed on the mini catalog")
                self.assertEqual(by_id[sample_id]["best_rank"], 1)
        for sample_id, turn in EXPECTED_HIT_TURN.items():
            with self.subTest(sample=sample_id, turn=turn):
                self.assertEqual(by_id[sample_id]["first_hit_turn"], turn)

    def test_every_turn_reports_zero_usage(self) -> None:
        agent = Agent(MINI)
        agent.reset("s", {})
        with mock.patch.object(socket, "socket", side_effect=_no_network):
            for turn, message in enumerate(
                ["I'm looking for Accessories Belts. Buckle closure",
                 "For that, what matters is: leather; 100% Leather.",
                 "I don't have an additional preference for other."], start=1):
                response = agent.respond("s", message, turn, 10)
                usage = response["usage"]
                self.assertEqual((usage["prompt_tokens"], usage["completion_tokens"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
