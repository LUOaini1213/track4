#!/usr/bin/env python3
"""Replay one official public session through ContestAgent PUBLIC.

Uses the same simulator policy as ``evaluator.local_evaluator`` (intent card,
``other`` disclosures, override turn). Prints remembered slots, pool sizes,
and whether the target is in the scored Top-10.

Examples::

    python demo/run_demo.py --session public_0002
    python demo/run_demo.py --scenario buying
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from evaluator.local_evaluator import (  # noqa: E402
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    materialize_hidden_fields,
    normalize_recommendations,
)
from starter.agent import Agent  # noqa: E402

SCENARIO_DEFAULTS = {
    "buying": "public_0001",
    "intent_override": "public_0002",
    # public_0007, not public_0006: public_0007's shelf is 519 rows, above
    # min_candidates, so its candidate pool is identical on the committed
    # data/catalog.mini.jsonl. public_0006's shelf is 13 rows, gets padded
    # from the rest of the catalog, and would replay differently on the slice.
    "browsing": "public_0007",
    "boundary": "public_0035",
}
MINI_CATALOG = REPO / "data" / "catalog.mini.jsonl"
# Sessions whose whole shelf is in the slice, so the replay matches a
# full-catalog run. Kept in step with scripts/make_mini_catalog.py.
POOL_EQUIVALENT_ON_MINI = tuple(sorted(SCENARIO_DEFAULTS.values()))


def run_session(agent: Agent, sample: dict, products: dict, categories: dict) -> dict:
    catalog_ids = set(products)
    session_id = f"demo_{sample['sample_id']}"
    agent.reset(session_id, sample["user_profile"])
    target = str(sample["ground_truth"]["parent_asin"])
    card, behavior = materialize_hidden_fields(sample, products)
    effective = {**sample, "intent_card": card, "behavior": behavior}
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    user_message = initial_message(
        effective, coarse_category(categories.get(target, [])), disclosed
    )
    title = str(products.get(target, {}).get("title") or "")[:80]
    print(f"scenario={sample['scenario_type']}  sample={sample['sample_id']}")
    print(f"target={target}  {title}")
    print(f"profile={sample['user_profile'].get('summary')}")
    hit_turn: int | None = None
    best_rank: int | None = None
    turn_ms: list[float] = []
    for turn in range(1, 11):
        print(f"\n--- turn {turn} ---")
        print(f"customer: {user_message}")
        started = time.perf_counter()
        response = agent.respond(session_id, user_message, turn, 10)
        elapsed_ms = (time.perf_counter() - started) * 1000
        turn_ms.append(elapsed_ms)
        diag = getattr(agent, "last_diagnostics", {}) or {}
        print(f"agent:    {response.get('message')}")
        print(
            "ask={ask}  pool={pool}  hard={hard}  withhold={withhold}  "
            "intent={intent}  scope={scope}  {ms:.0f}ms".format(
                ask=response.get("ask_attribute"),
                pool=diag.get("pool"),
                hard=diag.get("hard_pool"),
                withhold=diag.get("withhold"),
                intent=diag.get("intent"),
                scope=diag.get("intent_scope"),
                ms=elapsed_ms,
            )
        )
        usage = response.get("usage") or {}
        print(
            f"usage prompt={usage.get('prompt_tokens', 0)} "
            f"completion={usage.get('completion_tokens', 0)}"
        )
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        for pos, pid in enumerate(ranked[:10], 1):
            mark = "  <= TARGET" if pid == target else ""
            rec_title = str(products.get(pid, {}).get("title") or "")[:64]
            print(f"  {pos:>2}. {pid}  {rec_title}{mark}")
        if override_applied and target in ranked:
            best_rank = ranked.index(target) + 1
            hit_turn = turn
            break
        if turn == 10:
            break
        override = effective.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            user_message = str(
                override.get("message", "Actually, please ignore my earlier preference.")
            )
            print("[simulator] intent override")
        else:
            user_message, boundary_used = customer_reply(
                effective, response.get("ask_attribute"), disclosed, boundary_used
            )
    print("\n--- outcome ---")
    if hit_turn:
        print(f"HIT turn={hit_turn} rank={best_rank}")
    else:
        print("MISS")
    return {
        "sample_id": sample["sample_id"],
        "scenario_type": sample["scenario_type"],
        "hit": bool(hit_turn),
        "turn": hit_turn,
        "rank": best_rank,
        "mean_turn_ms": round(sum(turn_ms) / len(turn_ms), 1) if turn_ms else 0.0,
        "tokens": 0,
    }


def pick_sample(samples: list[dict], session: str | None, scenario: str | None) -> dict:
    if session:
        for sample in samples:
            if sample.get("sample_id") == session:
                return sample
        raise SystemExit(f"unknown session {session}")
    if scenario:
        default_id = SCENARIO_DEFAULTS.get(scenario)
        if default_id:
            for sample in samples:
                if sample.get("sample_id") == default_id:
                    return sample
        for sample in samples:
            if sample.get("scenario_type") == scenario:
                return sample
        raise SystemExit(f"no sample for scenario {scenario}")
    return samples[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default=None)
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--catalog", default=str(REPO / "data" / "catalog.jsonl"))
    parser.add_argument("--dataset", default=str(REPO / "data" / "public_set.jsonl"))
    args = parser.parse_args()
    samples = [
        json.loads(line)
        for line in Path(args.dataset).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sample = pick_sample(samples, args.session, args.scenario)
    catalog = Path(args.catalog)
    if not catalog.is_file():
        if not MINI_CATALOG.is_file():
            raise SystemExit(
                f"catalog not found: {catalog}. Import the organizer's frozen file with "
                "scripts/import_catalog.py (see data/README.md), or rebuild the slice "
                "with scripts/make_mini_catalog.py."
            )
        equivalent = sample["sample_id"] in POOL_EQUIVALENT_ON_MINI
        print(
            f"[demo] {catalog.name} not found; replaying on the committed slice "
            f"{MINI_CATALOG.name} ({MINI_CATALOG.stat().st_size / 1e6:.1f} MB)."
        )
        print(
            f"[demo] {sample['sample_id']} is pool-equivalent on the slice: {equivalent}. "
            f"Pool-equivalent sessions: {', '.join(POOL_EQUIVALENT_ON_MINI)}. "
            "Other sessions run but see a different candidate pool, so any score "
            "computed on the slice is meaningless."
        )
        args.catalog = str(MINI_CATALOG)
    started = time.perf_counter()
    agent = Agent(args.catalog)
    _, categories, products = catalog_index(args.catalog)
    print(f"index_seconds={time.perf_counter() - started:.2f}")
    run_session(agent, sample, products, categories)


if __name__ == "__main__":
    main()
