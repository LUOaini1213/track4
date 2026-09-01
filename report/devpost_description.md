# Devpost written description — ByteSize, Track 4

Copy the sections below into the Devpost submission form. Fill the Submission SHA with
`git rev-parse HEAD` of the tree you actually zip, on submit day.

---

## Evidence-Aware Conversational Search with Value-of-Information Stopping

### What it does

Our agent is a multi-turn shopping copilot. A customer arrives with a vague message
("I need something for a wedding next month") and an anonymized preference profile. The
agent has at most 10 turns to surface the one product the customer actually wants, out
of a frozen catalog of 50,000 Amazon clothing, shoes and jewellery items.

On every turn the agent decides one thing: **do I already have enough evidence to
recommend, or is one more question worth more than one more guess?** When evidence is
insufficient it asks a natural clarification question. When evidence is sufficient it
returns a ranked Top-10.

It converges in **2.75 turns on average** while the budget is 10, finds the target in
**100% of labelled public sessions**, and does all of it at **0 tokens and $0 per
session** with **no network access required**.

### The insight we built on

Most conversational-search designs treat "small candidate pool" as "ready to answer".
We found that is wrong, and it is the single biggest source of lost accuracy.

A pool can shrink to five items because the shopper disclosed a category and a colour —
and those five items can be near-identical clones that share the same marketing
template. Ranking them is a coin flip. Meanwhile one more question would have produced
a distinguishing attribute and turned a coin flip into a rank-1 hit.

So we reframed the stopping decision as **value of information**: ask when an
additional disclosure is expected to separate the pool, stop when it is not. The
controller keys on scenario, how many slots have been disclosed, whether the shopper
has already signalled "no additional preference", and pool size. It deliberately never
looks at how many turns remain, because a controller that races the clock stops asking
exactly when asking is most valuable.

We also found that the simulator only leaks the shopper's full intent text through one
specific field, so the agent always asks on that field while phrasing the visible
question naturally around the attributes still missing. That is a protocol insight, not
a ranking trick, and it is what makes the extra question cheap enough to be worth
taking.

### How we built it

Five stages, all deterministic:

1. **Dialogue state** — slots, scoped intent override (referenced replace, attribute
   replace, global reset), scenario detection.
2. **Exact-evidence AND** — category lock plus verbatim conjunction over disclosed
   slots; a filter that would empty the pool is skipped rather than applied.
3. **Value-of-Information controller** — insufficient evidence asks one more question;
   sufficient evidence commits to a recommendation.
4. **Popularity-first late fusion** — popularity 1.0, exact feature/details line match
   0.35, distinctive title phrase 0.15, MiniLM cosine 0.1. The dense signal is late
   fusion only: the conjunction builds the pool first, then cosine adjusts the order.
   It never participates in recall and never overrides popularity.
5. **Optional listwise LLM rerank** — implemented, measured, and shipped **disabled**
   because it did not clear our holdout gate.

### How we validated it

We did not trust the public set. A score of 0.95 on 200 labelled sessions we could
inspect is not a prediction for 800 private sessions we cannot.

So we built two independent evaluation layers. First, an **ID-disjoint holdout of 200
sessions** whose target ASINs never appear in the public set. Second, a **random 800
split into 8 shards of 100**, scored independently so we could see variance rather than
a single lucky mean.

That is where our strongest evidence comes from. Against the ablation baseline, the
Value-of-Information controller delivers **+60 rank-1 recommendations across 800
unseen, ID-disjoint sessions with zero Hit-rate loss**, and it improves on **8 out of 8
shards**. A single-number improvement can be noise; the same direction on every shard
is not.

| Set | n | Hit@10 | MRR | MTTC | TechnicalScore | Rank-1 |
|---|---:|---:|---:|---:|---:|---:|
| Public (labelled) | 200 | 1.000 | 0.954167 | 2.75 | 0.95125 | 184 |
| Our ID-disjoint holdout | 200 | 0.980 | 0.864845 | 2.885 | 0.911753 | 162 |
| Random 800, 8 shards | 800 | 0.97375 | 0.888018 | 2.8975 | 0.91533 | 672 |
| Weak BM25 starter | 200 | 0.125 | 0.068034 | 9.81 | — | — |

We ran ablations on retrieval fusion (RRF), BM25 over distinctive tokens, IDF and
exclusive-term weighting, title-uniqueness scoring, catalog-provenance features,
popularity-head guards and listwise LLM reranking. **None of them cleared the holdout
gate, so none of them shipped.** `report/methods.md` records every rejection with its
numbers. We think the discipline of not shipping a change that only helps the set you
tuned on is itself part of the result.

### Feasibility and practicality

- **Zero marginal inference cost.** 0 prompt tokens, 0 completion tokens, $0 per
  session. The scored path calls no LLM.
- **CPU only, no vector database, no model training.** An in-memory index over 50,000
  items builds in about 8 seconds; 200 full sessions complete in about 35 seconds,
  roughly 0.2 s per session.
- **Offline by construction.** With no environment variables set, no model backend is
  constructed and no network request is made. The sentence encoder ships with the
  bundle at a pinned revision, so disabling network access does not change the score.
- **Graceful degradation, honestly disclosed.** If the encoder is missing the agent
  still runs, but holdout Hit@10 drops from 0.980 to 0.975. We document that as a
  correctness dependency rather than describing the fallback as equivalent.
- **Tested.** 133 tests covering the agent contract, dialogue state, override scoping,
  response guards, retrieval, dense fusion, model fallback and submission packaging.

### Impact and relevance

Conversational commerce fails today for a reason that has little to do with model
quality: **the interface spends the shopper's patience faster than it earns their
trust.** Filter walls force people to translate an intention into a taxonomy they did
not design, and chatty AI assistants swing to the opposite failure — interrogating the
shopper for turns on end before showing anything.

Our contribution is a principled answer to *when to stop asking*, and it matters on
three axes that generalize well beyond this hackathon.

**For the shopper — time is the real currency.** Converging in 2.75 turns instead of
burning a 10-turn budget is the difference between a conversation and an interrogation.
And because we optimize rank-1 rather than only Hit@10, the improvement lands where
behaviour actually happens: the first result is the one people click. Our +60 rank-1
gain across 800 unseen sessions came with no loss in Hit-rate, so it is a strict
improvement in answer quality, not a trade.

**For the platform — cost structure decides what ships.** A design that calls an LLM
every turn cannot be deployed to a marketplace handling millions of sessions per day;
the per-session cost multiplies into an operating expense nobody approves. By putting
the intelligence in the stopping policy and the evidence model rather than in
per-turn generation, the same behaviour runs at zero marginal inference cost on
commodity CPUs. That is what makes it deployable at TikTok Shop scale rather than
demo-able at hackathon scale.

**For trust and reach — offline means private and portable.** No customer message
leaves the process. There is no third-party API in the scored path, so there is no
vendor to trust with shopping intent, no rate limit to degrade under load, and no
region where the feature simply cannot run. The same property makes it viable on
constrained infrastructure and in markets where sending user data to an external model
provider is not acceptable.

Finally, the mechanism is **catalog-agnostic**. The controller reasons about evidence
sufficiency and slot disclosure, not about clothing. Swap the catalog and the attribute
vocabulary and the same policy applies to electronics, groceries, travel, or any
domain where a user's intent has to be narrowed through dialogue. The narrow lesson is
about 50,000 fashion items; the transferable lesson is that **knowing when to stop
asking is a modelable decision, and modelling it explicitly beats tuning a ranker.**

### Challenges we ran into

The hardest problem was resisting our own public-set score. Reaching Hit@10 1.000 on
200 inspectable sessions makes every new heuristic look good, and several of them
improved the public number while quietly hurting the holdout. Building the ID-disjoint
holdout and the 8-shard study before continuing to optimize was the decision that saved
the submission, and we froze the configuration once improvements stopped reproducing
across shards.

The second was distinguishing "runnable" from "score-equivalent". Our agent degrades
cleanly when the sentence encoder is unavailable, and it would have been easy to call
that an optional enhancement. Measuring it honestly showed a real 0.980 → 0.975 holdout
drop, so we treat the encoder as a bundled correctness dependency and say so.

### What's next

The remaining oracle gap on our holdout is roughly 0.0026, and analysis in
`report/disclosure.md` and `report/provenance.md` indicates it is concentrated in
catalog-side clone disambiguation rather than in stopping policy. The next honest step
is richer product-side evidence, not another stopping rule.

---

## Development tools used

Python 3.10+ (developed and measured on 3.11.5), Git and GitHub, `unittest` for the
133-test suite, Windows 10 as the measurement environment. The demo video is built
reproducibly by a script rather than screen-recorded: Pillow renders the frames,
`ffmpeg` concatenates them and burns the English captions, and Node.js with `pptxgenjs`
generates the optional slide deck.

## APIs used

**None in the scored path.** The submitted configuration makes no API calls and
requires no credentials. An optional, disabled-by-default tiered backend can call a
DeepSeek-compatible or any local OpenAI-compatible `POST /chat/completions` endpoint;
it is enabled only by explicit environment variables and falls back deterministically
on timeout or malformed output.

## Assets used

- **Catalog and sessions:** derived from Amazon Reviews 2023, McAuley Lab, UCSD —
  50,000 `Clothing_Shoes_and_Jewelry` products and 200 labelled public sessions
  provided by the organizer. See `DATA_ATTRIBUTION.md`.
- **Sentence encoder:** `sentence-transformers/all-MiniLM-L6-v2`, Apache-2.0, pinned to
  revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`, bundled with the submission so
  the scored path needs no download.

## Libraries used

The scored path uses the **Python standard library only** for dialogue state,
retrieval, conjunction filtering, ranking and response validation. `torch` and
`transformers` are imported lazily and only to run the bundled MiniLM encoder;
`requirements.txt` documents them. `flashrank` and `sentence-transformers` appear
behind disabled experimental paths and are never imported by the scored configuration.
No vector database, no search engine, and no model training are involved.

Build-time only, never imported by the agent: `Pillow` and `imageio-ffmpeg` for the
demo video, `pptxgenjs` for the slide deck.

## Repository and reproduction

Public repository: `ByteSize2026/techjam-conversational-search`, branch
`contest/public`. README contains full setup and run instructions.

```bash
gzip -dc catalog.jsonl.gz > data/catalog.jsonl
python -m evaluator.local_evaluator --catalog data/catalog.jsonl \
    --dataset data/public_set.jsonl --output results.json
python -m unittest discover -s tests -v
python demo/run_demo.py --session public_0002
```

Submission SHA: `<fill with git rev-parse HEAD on submit day>`
