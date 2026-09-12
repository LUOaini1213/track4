#!/usr/bin/env python3
"""Run the scored Agent on two original synthetic products, without data downloads."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.run_demo import run_session  # noqa: E402
from starter.agent import Agent  # noqa: E402


def run_fixture() -> dict:
    rows = [
        {
            "parent_asin": "SYNTHETIC_SHIRT",
            "title": "Blue cotton running shirt",
            "features": ["cotton", "machine wash"],
            "description": ["lightweight"],
            "categories": ["Clothing", "Shirts"],
            "details": {"department": "womens"},
            "store": "Example Alpha",
            "price": 29.0,
            "average_rating": 4.8,
            "rating_number": 100,
        },
        {
            "parent_asin": "SYNTHETIC_BOOT",
            "title": "Black leather boot",
            "features": ["leather"],
            "description": ["boot"],
            "categories": ["Clothing", "Boots"],
            "details": {"department": "mens"},
            "store": "Example Beta",
            "price": 89.0,
            "average_rating": 4.0,
            "rating_number": 10,
        },
    ]
    sample = {
        "sample_id": "synthetic_buying",
        "scenario_type": "buying",
        "user_profile": {
            "purchase_frequency": "3-4 prior purchases",
            "average_prior_rating": 5.0,
            "rating_style": "usually positive",
            "preference_tags": ["comfort"],
            "summary": "Synthetic profile: prefers comfortable clothing.",
        },
        "ground_truth": {"parent_asin": "SYNTHETIC_SHIRT"},
    }
    print("Synthetic 2-product runtime demo; not the 50,000-product competition evaluation.")
    with tempfile.TemporaryDirectory(prefix="bytesize-demo-") as directory:
        catalog = Path(directory) / "catalog.jsonl"
        catalog.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        agent = Agent(catalog)
        return run_session(
            agent, sample,
            {row["parent_asin"]: row for row in rows},
            {row["parent_asin"]: row["categories"] for row in rows},
        )


if __name__ == "__main__":
    outcome = run_fixture()
    raise SystemExit(0 if outcome["hit"] else 1)
