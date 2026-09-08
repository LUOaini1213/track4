# v2 experiment: stop diluting a small shelf (`SHELF`)

**Status: post-deadline experiment. PUBLIC — the scored, frozen configuration —
is unchanged.** `SHELF` differs from PUBLIC by exactly one flag
(`pad_small_shelf=False`); `rank()`, the VoI controller and every other knob are
byte-identical. All numbers below were produced on 2026-09-02 with
`scripts/ab_variants.py`, both arms in the same process on the same catalog
and the same MiniLM sidecar; raw per-session rows are in
`holdout/ab_public_vs_shelf.json`.

## The bug

`candidate_pool()` (`starter/shopping_agent/contest_rank.py`) resolves the
buyer's category phrase to a *shelf* — the coarse category exactly as the
official simulator derives it — and that resolution is exact on 200/200 public
sessions. But when the shelf holds fewer than `min_candidates = 40` rows the
scored path throws the tight shelf away and pads it back up to ≥ 80 rows with
catalog-wide lexical hits. On the public set that fires on 36 of 200 sessions:
the agent had the right shelf and then buried it under decoys, which is what
made it ask one more turn.

Every earlier ablation (`methods.md`, 45 rows) touched ranking or stopping;
none touched the candidate pool. This is recall-side, which is where the
head-of-field entries win on MTTC.

## Result

`SHELF` keeps a resolved shelf as the whole candidate set, however small.

| Set | n | | Hit@10 | MRR | MTTC | TechnicalScore | Rank-1 |
|---|---:|---|---:|---:|---:|---:|---:|
| Public | 200 | PUBLIC | 1.000 | 0.9542 | 2.750 | 0.95125 | 184 |
| | | **SHELF** | 1.000 | 0.9567 | 2.700 | **0.95300** (+0.00175) | 185 |
| ID-disjoint holdout | 200 | PUBLIC | 0.980 | 0.8648 | 2.885 | 0.91175 | 162 |
| | | **SHELF** | 0.980 | 0.8682 | 2.835 | **0.91375** (+0.00200) | 163 |
| Random 800, 8 × 100 shards | 800 | PUBLIC | 0.9725 | 0.8883 | 2.904 | 0.91467 (mean) | 672 |
| | | **SHELF** | 0.9750 | 0.9018 | 2.838 | **0.92127** (mean, +0.00660) | 686 |

Per shard (TechnicalScore, PUBLIC → SHELF): 0.9006 → 0.9133, 0.9404 → 0.9504,
0.8914 → 0.8990, 0.8991 → 0.9142, 0.9179 → 0.9208, 0.9314 → 0.9323,
0.9330 → 0.9361, 0.9036 → 0.9042. **8 of 8 shards improve; Hit never drops
(two shards gain a hit); MTTC falls on every set.**

Session level, over all 1,200 sessions: 65 sessions change, **63 for the
better, 2 for the worse**. Rank-1 recommendations +18 / −2. Two sessions that
PUBLIC missed become hits (`rand800_0068`, `rand800_0328`); no hit is lost. The
typical gain is one turn (`r1 t3 → r1 t2`); the two regressions are
`rand800_0157` (rank 1 at turn 2 → rank 4 at turn 1) and `rand800_0683`
(rank 1 at turn 2 → rank 2 at turn 1): both now recommend one turn earlier from
a pool that is small but not yet ordered by the missing attribute.

Against the promotion gate in `freeze.md` (Public Hit = 1.000, holdout Hit ≥
0.980, holdout score > 0.911753, 8/8 shard direction): all four conditions
hold. The change is a correctness fix rather than a new heuristic — the
padding was contradicting the category lock it followed — which is the one
kind of change the freeze allows. It is nevertheless not promoted: the deadline
has passed, and the Devpost submission is PUBLIC.

Note on reproduction: the PUBLIC arm reproduces the frozen public (0.95125) and
holdout (0.911753) numbers exactly. On shards 2 and 7 the PUBLIC rerun is
slightly below the table in `robustness.md` (0.8914 vs 0.8900 and 0.9036 vs
0.9101; 8-shard mean 0.9147 vs 0.9153). Both arms of this comparison were run
in the same environment, so the deltas stand; the shard-level drift against the
August table is unexplained and recorded here rather than hidden.

## Reproduce

```bash
python scripts/ab_variants.py --a PUBLIC --b SHELF \
    --datasets data/public_set.jsonl holdout/holdout_200.jsonl holdout/shards/shard_0.jsonl \
               holdout/shards/shard_1.jsonl holdout/shards/shard_2.jsonl holdout/shards/shard_3.jsonl \
               holdout/shards/shard_4.jsonl holdout/shards/shard_5.jsonl holdout/shards/shard_6.jsonl \
               holdout/shards/shard_7.jsonl \
    --out holdout/ab_public_vs_shelf.json
python eval_contest.py --only shelf     # public 200, SHELF only
```

About 10 minutes on a laptop CPU for all 2 × 1,200 sessions, 0 tokens.

## What is still on the table

The head-of-field entries reach MTTC ≈ 2.2 with Hit 1.0. `SHELF` moves the
public set from 2.75 to 2.70, so most of that gap is elsewhere: the shelf
itself is large (median 181 rows on the public targets; largest 1,354), so the
next lever is ordering *inside* the shelf at turn 1 rather than recall — and
the VoI controller's thresholds (`gate_size`, `evidence_pool_cap`) were tuned
with the padded pools and have not been re-tuned for the tighter ones.
