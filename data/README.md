# Competition data

## `public_set.jsonl`

200 labelled development sessions: 80 Buying, 80 Browsing, 30 Intent Override and 10 Boundary. Each session carries a safe aggregate `user_profile` and public labels for local development. Direct user identifiers, timestamps, free-text reviews, raw purchase history, hidden intent cards and simulator-policy internals are not shipped in this participant file.

## `catalog.jsonl`

The frozen 50,000-item catalog. Download `catalog.jsonl.gz` from the GitHub Release of this repository (https://github.com/LUOaini1213/track4/releases) and decompress it here:

```bash
gzip -dc catalog.jsonl.gz > data/catalog.jsonl
```

Expected: 50,000 rows; `sha256sum catalog.jsonl.gz` = `07fd142631fd6b03e2b4d09988c3eb7d53720e9d57010c79db48eeaada50a8f8` (the same digest the release publishes in its `SHA256SUMS`). Never place API keys, private evaluation data or participant outputs in this directory.

## `catalog.mini.jsonl`

A 2.2 MB slice, committed. It keeps the complete shelf of the four documented demo sessions (`public_0001`, `public_0002`, `public_0007`, `public_0035`), so `demo/run_demo.py` and `tests/test_offline_guarantee.py` replay them identically without the download. Other sessions run on it but are not pool-equivalent, and no score computed on the slice means anything. Rebuild it with `scripts/make_mini_catalog.py`.
