#!/usr/bin/env python3
"""Build ``data/catalog.mini.jsonl``, a small catalog slice for out-of-the-box demos.

A fresh clone does not carry the 60 MB frozen catalog (it comes from the GitHub
Release). The slice lets ``python demo/run_demo.py`` run immediately:

1. every row whose shelf — the coarse category exactly as the official
   simulator derives it — is the shelf of one of the documented demo sessions
   (``demo.run_demo.SCENARIO_DEFAULTS``), so those replays see the same
   candidate pool, the same popularity order and the same conversation as on
   the full catalog;
2. the target row of every public session, so ``--session public_XXXX`` still
   resolves (those sessions are not pool-equivalent and print a notice).

It is a demo convenience only. Scores computed on the slice are meaningless;
the scored path always uses the full catalog.

    python scripts/make_mini_catalog.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from demo.run_demo import SCENARIO_DEFAULTS  # noqa: E402
from evaluator.local_evaluator import coarse_category  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    # Split on newlines only: product text contains U+2028-style separators
    # that str.splitlines() would treat as line breaks.
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", default=str(REPO / "data" / "catalog.jsonl"))
    parser.add_argument("--dataset", default=str(REPO / "data" / "public_set.jsonl"))
    parser.add_argument("--out", default=str(REPO / "data" / "catalog.mini.jsonl"))
    parser.add_argument(
        "--sessions",
        nargs="*",
        default=[],
        help="extra public session ids whose whole shelf should be kept",
    )
    args = parser.parse_args()

    rows = load_jsonl(Path(args.catalog))
    samples = load_jsonl(Path(args.dataset))
    by_asin = {row["parent_asin"]: row for row in rows}
    targets = {str(sample["ground_truth"]["parent_asin"]) for sample in samples}
    demo_ids = set(SCENARIO_DEFAULTS.values()) | set(args.sessions)
    demo_targets = {
        str(sample["ground_truth"]["parent_asin"]) for sample in samples if sample["sample_id"] in demo_ids
    }
    missing = sorted(t for t in demo_targets if t not in by_asin)
    if missing:
        raise SystemExit(f"demo targets missing from catalog: {missing}")
    shelves = {coarse_category(by_asin[t].get("categories") or []) for t in demo_targets}

    kept = [
        row
        for row in rows  # original order preserved: index order breaks popularity ties
        if coarse_category(row.get("categories") or []) in shelves or row["parent_asin"] in targets
    ]
    out = Path(args.out)
    out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept), encoding="utf-8")
    shelf_sizes = {
        shelf: sum(1 for row in kept if coarse_category(row.get("categories") or []) == shelf) for shelf in shelves
    }
    print(f"wrote {out} : {len(kept)} rows, {out.stat().st_size / 1e6:.2f} MB")
    print(f"demo sessions kept whole: {sorted(demo_ids)}")
    for shelf, size in sorted(shelf_sizes.items()):
        print(f"  shelf {shelf!r}: {size} rows")
    print(f"public targets present: {sum(1 for t in targets if t in {r['parent_asin'] for r in kept})}/{len(targets)}")


if __name__ == "__main__":
    main()
