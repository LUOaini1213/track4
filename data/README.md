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

Never place API keys, private evaluation data, or participant outputs in this directory.
