# Our own test sets (not the organizers' private 800)

The organizers' private 800 sessions are unseen. Everything here is sampled from the same frozen catalog with the `data/public_set.jsonl` ASINs excluded, to measure how much the public 0.95 overstates.

## Files that matter now

| File | What it is |
|---|---|
| `holdout_200.jsonl` | ID-disjoint holdout 200: 80 / 80 / 30 / 10, seed 2026 |
| `ours_holdout.json` | the current PUBLIC (e123) on the holdout 200: Hit 0.980 / **0.911753** |
| `shards/a_vs_e123.json` | 8 × 100: A vs e123, **e123 higher on 8 of 8** |
| `shards/out_0.json` … `out_7.json` | the frozen PUBLIC's full payload per shard, **regenerated 2026-09-02** with `eval_shard.py`; their pooled mean is the e123 arm of `a_vs_e123.json` (0.91533). The snapshots they replace, in git history, came from a pre-freeze configuration and averaged 0.89989. |
| `holdout_compare.json` | ours vs a classmate's structured agent (the classmate's holdout run had no LLM) |
| `ab_public_vs_shelf.json` | 2026-09-02 A/B: PUBLIC vs SHELF (`report/shelf.md`) on the public 200, the holdout 200 and the 8 shards, with a session-level diff |
| `random_800.jsonl` | 320 / 320 / 120 / 40, seed in the generator script, disjoint from the public ASINs |
| `random800_compare.json` | 8-way merge: Hit 0.9725 / 0.89989 (**old-configuration snapshot**, kept for the record) |
| `shards/shard_0.jsonl` … `shard_7.jsonl` | 100 sessions each |

`ours_holdout.json` and `holdout_skip_floor.json` are the same round (MiniLM skipped on generic constraints + popularity locked).

## Ablation residue (not current scores)

Full payloads from trying the popularity lock / RRF / MiniLM-skip-only variants; **none** of these entered PUBLIC:

- `holdout_popfloor.json` / `public_popfloor.json` — `dense_pop_floor=10` (trades 0090 for 0122)
- `holdout_popfloor8.json` / `public_popfloor8.json` — floor = 8 (still loses 0090)
- `holdout_rrf.json` / `public_rrf.json` — `dense_rrf_k=10` (holdout Hit 0.97)
- `holdout_skipgeneric.json` / `public_skipgeneric.json` — skip on generic constraints only, no popularity lock (0122 still missed)

Generate:

```bash
python eval_holdout.py
python eval_shard.py --dataset holdout/shards/shard_0.jsonl --output holdout/shards/out_0.json
```
