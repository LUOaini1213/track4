# Competition Data

## `public_set.jsonl`

Contains 200 labeled development sessions: 80 Buying, 80 Browsing, 30 Intent Override, and 10 Boundary sessions.

Each session contains a safe aggregate `user_profile` and public labels for local development. Direct user identifiers, timestamps, free-text reviews, raw purchase history, hidden intent cards, and simulator-policy internals are not shipped in this participant file.

## `catalog.jsonl`

The full catalog is not redistributed in this repository or its Releases. Obtain
the original competition file from the organizer or an existing participant kit.
It contains 50,000 unique `parent_asin` values; all 200 public targets belong to it.

From the repository root, import either original format without additional packages:

```bash
python -S scripts/import_catalog.py "/path/to/original/catalog.jsonl.gz"
# Read-only verification of an already restored file:
python -S scripts/import_catalog.py data/catalog.jsonl --check-only
```

The importer verifies the decompressed bytes, row count, unique IDs and public
target membership before writing `data/catalog.jsonl`. It refuses a different
existing destination and leaves the source untouched. Expected SHA256 values:

| Original artifact | SHA256 |
|---|---|
| `catalog.jsonl` | `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67` |
| Original `catalog.jsonl.gz` | `07fd142631fd6b03e2b4d09988c3eb7d53720e9d57010c79db48eeaada50a8f8` |

The gzip hash is from the original participant manifest; recompressing identical
JSONL may produce a different gzip hash, so the importer checks decompressed bytes.
Do not regenerate, reduce or edit this frozen catalog to obtain a passing score.

The source is [Amazon Reviews 2023](https://amazon-reviews-2023.github.io/), Clothing,
Shoes and Jewelry metadata. See `DATA_ATTRIBUTION.md` and the upstream terms; this
project does not grant rights to redistribute upstream data. For a runnable example
without that data, use `python -S demo/fixture.py` from the repository root.

## `catalog.mini.jsonl`

A committed 1,631-row slice of the frozen catalog, about 2.2 MB, so that
`demo/run_demo.py` and the test suite replay a real labelled session on a bare
clone. `scripts/make_mini_catalog.py` builds it and keeps two things:

- every row on the shelf — the coarse category exactly as `evaluator/local_evaluator.py`
  derives it — of the four sessions `demo.run_demo.SCENARIO_DEFAULTS` points at
  (`public_0001`, `public_0002`, `public_0007`, `public_0035`). Each of those
  shelves holds more rows than `min_candidates`, so the candidate pool is never
  padded from the rest of the catalog and those four sessions replay turn for
  turn as they do on all 50,000 items;
- the target row of all 200 public sessions, so `--session public_XXXX` always
  resolves. Those other sessions are not pool-equivalent, and `run_demo.py` says
  so before replaying one.

It is a demo and test convenience. Scores are only ever computed on
`catalog.jsonl`; a score computed on the slice means nothing.

Never place API keys, private evaluation data, or participant outputs in this directory.
