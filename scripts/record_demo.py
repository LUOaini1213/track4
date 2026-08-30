#!/usr/bin/env python3
"""Warm MiniLM, then replay public_0002 slowly for the 3-minute demo video.

Run this *before* hitting record once, so the first on-camera run is fast.
Then record:

    python scripts/record_demo.py --pause 2.5
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

from demo.run_demo import catalog_index, pick_sample, run_session  # noqa: E402
from starter.agent import Agent  # noqa: E402
from starter.shopping_agent.contest_dense import get_encoder  # noqa: E402


def _pause(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default="public_0002")
    parser.add_argument("--pause", type=float, default=2.5)
    parser.add_argument("--catalog", default=str(ROOT / "data" / "catalog.jsonl"))
    parser.add_argument("--dataset", default=str(ROOT / "data" / "public_set.jsonl"))
    parser.add_argument("--warmup-only", action="store_true")
    args = parser.parse_args()

    print("warming MiniLM…", flush=True)
    encoder = get_encoder()
    ready = encoder.available()
    print(f"minilm_available={ready}", flush=True)
    if ready:
        encoder.vector("leather belt")
        print("minilm_warmed", flush=True)
    if args.warmup_only:
        return

    samples = [
        json.loads(line)
        for line in Path(args.dataset).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sample = pick_sample(samples, args.session, None)
    started = time.perf_counter()
    agent = Agent(args.catalog)
    _, categories, products = catalog_index(args.catalog)
    print(f"index_seconds={time.perf_counter() - started:.2f}", flush=True)
    _pause(args.pause)
    original_respond = agent.respond

    def slow_respond(*pargs, **kwargs):
        response = original_respond(*pargs, **kwargs)
        _pause(args.pause)
        return response

    agent.respond = slow_respond  # type: ignore[method-assign]
    run_session(agent, sample, products, categories)


if __name__ == "__main__":
    main()
