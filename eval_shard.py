#!/usr/bin/env python3
"""Evaluate ContestAgent on one JSONL shard. Used by parallel workers.

``--arm e123`` (default) is the frozen PUBLIC configuration. ``--arm A`` is
the comparison arm of ``holdout/shards/a_vs_e123.json``: the same agent with
``ambiguity_defer="a"`` and the E1/E2/E3 progress deferral switched off.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.shopping_agent.contest_agent import ContestAgent
from starter.shopping_agent.contest_config import PUBLIC
from starter.shopping_agent.contest_index import ContestIndex

ARMS = {
    "e123": PUBLIC,
    "A": replace(PUBLIC, ambiguity_defer="a", progress_defer=""),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--arm", choices=sorted(ARMS), default="e123")
    args = parser.parse_args()
    catalog_ids, categories, products = catalog_index(args.catalog)
    samples = load_jsonl(args.dataset)
    index = ContestIndex(args.catalog)
    agent = ContestAgent(args.catalog, config=ARMS[args.arm], index=index)
    payload = evaluate(agent, samples, catalog_ids, categories, products)
    payload["arm"] = args.arm
    # Ties in the agent's ranking follow str-hash order, so a run is only
    # repeatable under a fixed PYTHONHASHSEED; record which one was used.
    payload["pythonhashseed"] = os.environ.get("PYTHONHASHSEED")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "arm": args.arm,
                "n": payload["sample_count"],
                "hit_rate_at_10": payload["hit_rate_at_10"],
                "mrr": payload["mrr"],
                "mttc": payload["mttc"],
                "recommended_technical_score": payload["recommended_technical_score"],
                "misses": [s["sample_id"] for s in payload["sessions"] if not s.get("hit")],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
