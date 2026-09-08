#!/usr/bin/env python3
"""A/B two ContestAgent configurations on one or more session files.

Builds the catalog index once, evaluates both configurations with the official
local evaluator on every dataset, and writes one JSON report with the summary
metrics per dataset plus a per-session diff (join on sample_id, compare hit /
best_rank / first_hit_turn). Nothing here touches the scored PUBLIC path or the
committed result files.

    python scripts/ab_variants.py --a PUBLIC --b SHELF \
        --datasets data/public_set.jsonl holdout/holdout_200.jsonl holdout/shards/shard_*.jsonl \
        --out holdout/ab_public_vs_shelf.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl  # noqa: E402
from starter.shopping_agent import contest_config  # noqa: E402
from starter.shopping_agent.contest_agent import ContestAgent  # noqa: E402
from starter.shopping_agent.contest_index import ContestIndex  # noqa: E402

SUMMARY_KEYS = ("hit_rate_at_10", "mrr", "mttc", "efficiency", "recommended_technical_score")


def _row(session: dict) -> dict:
    return {
        "hit": bool(session.get("hit")),
        "best_rank": session.get("best_rank"),
        "first_hit_turn": session.get("first_hit_turn"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--datasets", nargs="+", required=True)
    parser.add_argument("--a", default="PUBLIC", help="config constant in contest_config")
    parser.add_argument("--b", default="SHELF", help="config constant in contest_config")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    configs = {name: getattr(contest_config, name) for name in (args.a, args.b)}
    catalog_ids, categories, products = catalog_index(args.catalog)
    started = time.perf_counter()
    index = ContestIndex(args.catalog)
    print(f"index {len(index)} rows in {time.perf_counter() - started:.1f}s", flush=True)

    report = {"a": args.a, "b": args.b, "catalog": args.catalog, "datasets": []}
    for dataset in args.datasets:
        samples = load_jsonl(dataset)
        runs: dict[str, dict] = {}
        for name, config in configs.items():
            agent = ContestAgent(args.catalog, config=config, index=index)
            t0 = time.perf_counter()
            payload = evaluate(agent, samples, catalog_ids, categories, products)
            runs[name] = {
                "summary": {key: payload[key] for key in SUMMARY_KEYS},
                "scenario_metrics": payload.get("scenario_metrics"),
                "tokens": payload.get("reported_token_usage"),
                "seconds": round(time.perf_counter() - t0, 1),
                "sessions": {row["sample_id"]: row for row in payload["sessions"]},
            }
        a, b = runs[args.a], runs[args.b]
        changed = []
        for sample_id, sa in a["sessions"].items():
            sb = b["sessions"][sample_id]
            if _row(sa) != _row(sb):
                changed.append(
                    {
                        "sample_id": sample_id,
                        "scenario": sa.get("scenario_type"),
                        args.a: _row(sa),
                        args.b: _row(sb),
                    }
                )
        rank1 = {
            name: sum(1 for row in run["sessions"].values() if row.get("best_rank") == 1)
            for name, run in runs.items()
        }
        entry = {
            "dataset": dataset,
            "n": len(samples),
            args.a: a["summary"],
            args.b: b["summary"],
            "scenario_metrics": {args.a: a["scenario_metrics"], args.b: b["scenario_metrics"]},
            "tokens": {args.a: a["tokens"], args.b: b["tokens"]},
            "rank1": rank1,
            "delta_score": round(
                b["summary"]["recommended_technical_score"] - a["summary"]["recommended_technical_score"], 6
            ),
            "changed_sessions": changed,
        }
        report["datasets"].append(entry)
        sa, sb = a["summary"], b["summary"]
        print(
            f"{dataset}: n={len(samples)} | {args.a} Hit {sa['hit_rate_at_10']:.4f} MRR {sa['mrr']:.4f} "
            f"MTTC {sa['mttc']:.3f} score {sa['recommended_technical_score']:.5f} rank1 {rank1[args.a]} | "
            f"{args.b} Hit {sb['hit_rate_at_10']:.4f} MRR {sb['mrr']:.4f} MTTC {sb['mttc']:.3f} "
            f"score {sb['recommended_technical_score']:.5f} rank1 {rank1[args.b]} | "
            f"delta {entry['delta_score']:+.5f} | changed {len(changed)}",
            flush=True,
        )
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")

    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
