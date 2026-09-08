# Reports (ContestAgent PUBLIC)

The scored implementation is `starter/shopping_agent/contest_*.py`; the `starter.agent.Agent` the evaluator loads is exactly that. A teammate's Qwen experiments live on branch `legacy/qwen`.

## Current scores

| Set | n | Hit@10 | MRR | MTTC | TechnicalScore | Notes |
|---|---:|---:|---:|---:|---:|---|
| Public 200 | 200 | 1.000 | 0.9542 | 2.75 | **0.95125** | `results_contest_public.json`, 0 tokens |
| ID-disjoint holdout 200 | 200 | 0.980 | 0.8648 | 2.885 | **0.9118** | public-set ASINs excluded; this is *not* the organizers' private 800 |
| Random 800, 8 × 100 shards | 800 | 0.97375 | 0.8880 | 2.8975 | **0.91533** | pooled mean of the shards; the frozen PUBLIC (e123), `holdout/shards/a_vs_e123.json` and `out_0..7.json` (regenerated 2026-09-02 with the frozen config) |

TechnicalScore = `0.50 × Hit@10 + 0.30 × MRR + 0.20 × Efficiency`. **E123 is frozen as the submission** (`report/freeze.md`). The next gate above 0.911753 **accepts only a correctness bug fix or a new source of information**; PUBLIC is not changed for a heuristic worth +0.0005 on the holdout.

## Which file to read

| File | Contents |
|---|---|
| [methods.md](methods.md) | Ablations on the public 200: what stayed and what was rejected (title coverage, FlashRank, gate 8–10, RRF, …) |
| [holdout.md](holdout.md) | What the holdout 200 is, and the comparison with a classmate's agent |
| [optimize.md](optimize.md) | Where further gains could come from (not from tuning on the public set again) |
| [optimize_kb.md](optimize_kb.md) | **Do not build a new knowledge base**; hard-pool IDF / BM25 come first |
| [architecture.md](architecture.md) | Data flow of value-of-information stopping; override scoping; the response guard |
| [attribution.md](attribution.md) | Additive contribution of E1 / E2 / E3 to ΔMRR, ΔMTTC and rank-1 |
| [robustness.md](robustness.md) | 8 × 100 ID-disjoint shards: e123 vs A, same direction on 8 of 8 |
| [freeze.md](freeze.md) | **Submission freeze**: algorithm SHA, no hard-coded HEAD in the video, MiniLM is a correctness dependency |
| [../SUBMISSION_CHECKLIST.md](../SUBMISSION_CHECKLIST.md) | The final ZIP must carry the MiniLM sidecar; git keeps the research evidence |
| [complete_agent.md](complete_agent.md) | The five-stage agent in full: measured RRF, LLM blend, gating, why not LambdaMART |
| [provenance.md](provenance.md) | Catalog-side oracle (feature / details / clone / store) — **never enters `rank()`** |
| [disclosure.md](disclosure.md) | Turn / disclosure oracle: the expected value of one more `other`; the next cut is not narrowing A |
| [submit.md](submit.md) | Reproduction commands, 0 tokens / $0, latency, limitations, contributions |
| [rubric_4_6.md](rubric_4_6.md) | Self-assessment against the five rubric axes; IDF / exclusive rare tokens / small-pool MiniLM on generic constraints did not enter PUBLIC |
| [shelf.md](shelf.md) | The post-deadline SHELF variant (`pad_small_shelf=False`): measured, not shipped |

Demo transcripts (official simulator replays): [buying](demo_buying.txt) · [browsing](demo_browsing.txt) · [override](demo_override.txt) · [boundary](demo_boundary.txt).

## Reproduce

```bash
python eval_contest.py --only public
python eval_holdout.py --skip-generate
python demo/run_demo.py --session public_0002
python -m unittest discover -s tests -v
```

The protocol skeleton, which is not re-tuned for the public set: always ask `other`; verbatim conjunction; `gate_size=5`; no recommendation before an override can score; `dump_slots=4`. With three slots and a flat field score, ask one more round (`ambiguity_defer=a`). In Buying / Browsing, when the pool is at most 5 but the slots are not exhausted, or with three slots and a leftover, ask one more round, once (`progress_defer=e123`). MiniLM runs only on a hard pool that has a distinctive constraint. Exact hard-pool field lines weigh `w_field=0.35`, title phrases `w_phrase=0.15`. Without the MiniLM weights the dense term is 0 (holdout Hit 0.975 — runnable, not the champion path).
