# Shard robustness: E123 vs A

8 × 100 sessions, split from `holdout/random_800.jsonl`. **Disjoint** from the public 200 ASINs, and the shards are **disjoint** from each other. A = `ambiguity_defer=a` with `progress_defer=""`; e123 = the current PUBLIC. Raw table: `holdout/shards/a_vs_e123.json`; the per-shard payloads of the frozen PUBLIC are `holdout/shards/out_0..7.json`.

**e123 has the higher TechnicalScore on 8 of 8 shards.** Hit is identical to A on every shard; what rises is MRR, and the tax is MTTC.

| shard | A Hit | A MRR | A score | e123 Hit | e123 MRR | e123 score | Δscore | rank-1 A → e123 |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 0.96 | 0.8255 | 0.8906 | 0.96 | 0.8726 | 0.9006 | +0.0100 | 74 → 82 |
| 1 | 1.00 | 0.8888 | 0.9366 | 1.00 | 0.9171 | 0.9405 | +0.0039 | 81 → 86 |
| 2 | 0.94 | 0.8145 | 0.8760 | 0.94 | 0.8741 | 0.8900 | +0.0141 | 74 → 84 |
| 3 | 0.96 | 0.8307 | 0.8912 | 0.96 | 0.8649 | 0.8991 | +0.0079 | 76 → 82 |
| 4 | 0.97 | 0.8423 | 0.9029 | 0.97 | 0.9070 | 0.9179 | +0.0150 | 76 → 87 |
| 5 | 0.99 | 0.8606 | 0.9216 | 0.99 | 0.9087 | 0.9314 | +0.0098 | 79 → 86 |
| 6 | 1.00 | 0.8476 | 0.9231 | 1.00 | 0.8901 | 0.9330 | +0.0100 | 75 → 83 |
| 7 | 0.97 | 0.8414 | 0.9048 | 0.97 | 0.8697 | 0.9101 | +0.0053 | 77 → 82 |
| **mean of 8** | **0.9738** | **0.8439** | **0.9058** | **0.9738** | **0.8880** | **0.9153** | **+0.0095** | **612 → 672** |

The direction is stable: the weakest gain is +0.0039 (shard 1, already near the ceiling), the strongest +0.0150. Over the random 800 that is +60 rank-1 recommendations. This is not a single point carved out on the holdout 200.

The holdout 200 and these 800 share 7 ASINs by chance, which does not affect the conclusion "outside the public set, shards disjoint from each other". The organizers' private 800 remain unseen.
