# ByteSize — Evidence-Aware Conversational Search with Value-of-Information Stopping

TechJam Track 4: Conversational E-Commerce Search Challenge.

A multi-turn shopping agent that finds a customer's hidden target product inside a
frozen 50,000-item Amazon catalog. The agent decides, every turn, whether it has
**enough evidence to recommend** or should **spend one more turn asking**. It runs
fully offline at **0 tokens and $0 per session**.

**Headline result:** on 800 unseen, ID-disjoint sessions the stopping controller
produces **+60 rank-1 recommendations with zero Hit-rate loss**, improving on
**8 of 8** shards.

| Set | n | Hit@10 | MRR | MTTC | TechnicalScore | Rank-1 |
|---|---:|---:|---:|---:|---:|---:|
| Public (labelled) | 200 | **1.000** | 0.954167 | 2.75 | **0.95125** | 184 |
| Our ID-disjoint holdout | 200 | **0.980** | 0.864845 | 2.885 | **0.911753** | 162 |
| Random 800, 8×100 shards | 800 | 0.97375 | 0.888018 | 2.8975 | 0.91533 | 672 |
| Weak BM25 starter (reference) | 200 | 0.125 | 0.068034 | 9.81 | — | — |

`TechnicalScore = 0.50 × Hit@10 + 0.30 × MRR + 0.20 × Efficiency`, where
`Efficiency = clip((11 - MTTC) / 10, 0, 1)`.

Every number above was produced with `usage = 0 prompt tokens, 0 completion tokens`.
The public-set score is **not** a prediction for the organizer's private 800 sessions;
that is why we built our own ID-disjoint holdout and an 8-shard robustness study.

## Quick Start

Python 3.10 or later. Developed and measured on Python 3.11.5, Windows 10.

```bash
# 1. Get the catalog (see the GitHub Release and its SHA256SUMS)
gzip -dc catalog.jsonl.gz > data/catalog.jsonl

# 2. Run the official harness. The scored entry point is starter.agent.Agent
python -m evaluator.local_evaluator --catalog data/catalog.jsonl \
    --dataset data/public_set.jsonl --output results.json

# 3. Full test suite (133 tests)
python -m unittest discover -s tests -v

# 4. Watch one multi-turn session end to end
python demo/run_demo.py --session public_0002   # Intent Override
python demo/run_demo.py --scenario buying
```

No environment variables are required. With no variables set, no model backend is
constructed and **no network request is made**.

Additional evaluation entry points: `eval_contest.py --only public` scores the public
200 and writes `results_contest_public.json`; `eval_holdout.py` scores our own
holdout 200; `eval_shard.py` scores one shard of the random 800.

## How It Works

The scored path is `starter.agent.Agent` → `ContestAgent` + the `PUBLIC` config.
The central idea is not "conjunction filter plus popularity" — it is **keep asking
while evidence is insufficient, then rank with popularity-first late fusion**.

```text
User turn
 ↓
[1] Dialogue state            slots, scoped intent override, scenario
 ↓
[2] Exact-evidence AND        category lock + verbatim conjunction (empty filter is skipped)
 ↓
[3] Value-of-Information controller
      ├ evidence insufficient → ask one more `other`
      └ evidence sufficient   → recommend
 ↓
[4] Popularity-first late fusion
      popularity 1.0 + exact field line 0.35 + distinctive title phrase 0.15 + MiniLM 0.1
 ↓
[5] Optional listwise LLM rerank (shortlist ≤ 10, disabled by default)
```

The key insight is that **a small candidate pool does not mean the agent has enough
information**. Slot-disclosure trajectories differ by scenario — Buying tends to go
`1 → +2 → +1 → exhausted`, Browsing `0 → +2 → +2 → exhausted`. The controller decides
using scenario, number of disclosed slots, whether "no additional preference" was
already received, and pool size. It never inspects the remaining turn budget and never
changes `rank()`.

MiniLM is applied as **late fusion only**: the conjunction produces a hard pool first,
then `score += 0.1 × min-max(cosine)`. It never replaces popularity and never
participates in recall.

Detailed design notes live in `report/`: `architecture.md` (data flow),
`attribution.md` (per-component contribution), `robustness.md` (8-shard study),
`methods.md` (accepted and rejected ablations), `freeze.md` (frozen configuration).

## Model Choice, Cost, Tokens, Latency

| Component | Default | Cost | Behaviour without network |
|---|---|---|---|
| Category lock + verbatim AND + popularity | Standard-library in-memory index | $0 | Works |
| MiniLM sentence encoder | Bundled sidecar, then HF cache, then pinned Hub revision | $0 | Works from the bundled sidecar |
| Listwise LLM rerank | **Disabled** | Per token if enabled | Falls back to the 0-token ranking |

**Reported token usage across the 200-session public evaluation: 0 prompt tokens,
0 completion tokens, $0.** The scored configuration sets `llm_listwise=False` and calls
no LLM.

**Latency**, measured locally on Windows with the 50,000-item catalog: index build
about 8 s, then about 35 s for 200 sessions, roughly **0.2 s per session** including
MiniLM.

**Network:** the submission requires no network access. Official final scoring may
disable it; our scored path is unaffected because the encoder ships with the bundle.

### MiniLM is a scoring dependency, not an optional extra

The champion numbers use `sentence-transformers/all-MiniLM-L6-v2` at revision
`c9745ed1d9f207416be6d2e6f8de32d1f16199bf` (Apache-2.0), with `model.safetensors`
sha256 `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.

Load order: `TECHJAM_DENSE_HOME` → `models/all-MiniLM-L6-v2` (the bundled sidecar) →
Hugging Face cache → the same pinned revision from the Hub when network is allowed.
Rebuild the sidecar with `python scripts/vendor_minilm.py`.

If the weights are absent the agent **still runs**, but it is **not score-equivalent**:

| Set | With MiniLM | Without MiniLM |
|---|---|---|
| Public 200 | Hit 1.000 / 0.95125 | Hit 1.000 / 0.953339 |
| Holdout 200 | Hit **0.980** / 0.911753 | Hit **0.975** / 0.909529 |

The Value-of-Information stopping behaviour does not depend on MiniLM; public MTTC
stays at 2.75 either way. Force the offline path with `TECHJAM_DENSE_OFFLINE=1`.

### Optional tiered model backend (off by default)

An optional, explicitly tiered model path exists for experimentation and stays usable
offline: `DeepSeek API → local OpenAI-compatible endpoint → deterministic fallback`.
It is enabled only by environment variables, never by default. If a configured backend
times out or returns an HTTP, JSON, schema or validation error, the next tier is
attempted, and the semantic ranker repairs invalid, duplicate, unknown or omitted IDs
using the original deterministic candidate order.

```text
SHOPPING_AGENT_DEEPSEEK_API_KEY       # enables the DeepSeek tier
SHOPPING_AGENT_DEEPSEEK_BASE_URL      # default: https://api.deepseek.com
SHOPPING_AGENT_DEEPSEEK_MODEL         # default: deepseek-v4-flash
SHOPPING_AGENT_LOCAL_BASE_URL         # enables the local tier together with LOCAL_MODEL
SHOPPING_AGENT_LOCAL_MODEL            # model name sent to the local endpoint
SHOPPING_AGENT_LOCAL_API_KEY          # optional Authorization token for local servers
SHOPPING_AGENT_MODEL_TIMEOUT_SECONDS  # per-request hard timeout; default 8
SHOPPING_AGENT_MODEL_CANDIDATE_LIMIT  # semantic-ranker candidate cap; default 30
SHOPPING_AGENT_RETRIEVAL_LIMIT        # retrieval budget; default 100
SHOPPING_AGENT_MODEL_MAX_TOKENS       # completion cap; default 512
SHOPPING_AGENT_MODEL_TEMPERATURE      # default 0
```

Teams manage their own credentials; no API key is committed to this repository.

## Agent Interface

```python
class Agent:
    def reset(self, session_id: str, user_profile: dict) -> None:
        ...

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        return {
            "message": "Do you have a material preference?",
            "ask_attribute": "material",
            "recommendations": [{"parent_asin": "B000..."}, {"parent_asin": "B001..."}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 30},
        }
```

`ask_attribute` is one of `category`, `material`, `color`, `size`, `style`, `brand`,
`budget`, `feature`, `use_case`, `other`, or `null`. See `docs/agent_api_contract.json`.
Only exact `parent_asin` equality counts as a hit, and only the first 10 valid unique
IDs are scored.

## Repository Layout

```text
starter/agent.py                     Agent = ContestAgent PUBLIC (scored); LegacyAgent = earlier pipeline
starter/shopping_agent/contest_*.py  the scored implementation
starter/shopping_agent/*.py          supporting modules (dialogue state, catalog, ranking, response guard)
evaluator/local_evaluator.py         official public-set simulator and scorer, unmodified
eval_contest.py                      scores the public 200 → results_contest_public.json
eval_holdout.py                      scores our own ID-disjoint holdout 200
eval_shard.py                        scores one shard of the random 800
demo/run_demo.py                     replays one multi-turn session
models/                              pinned MiniLM sidecar and its README
report/                              architecture, ablations, robustness, freeze notes
holdout/                             our own test sets and comparison JSON (not the organizer's private 800)
scripts/pack_submission.py           builds the clean Devpost ZIP
data/public_set.jsonl                200 labelled development sessions
docs/                                competition specification, API contract, scoring config
```

## Branches

| Branch | `starter.agent.Agent` | Purpose |
|---|---|---|
| `contest/public` | ContestAgent PUBLIC | **Submission and scoring** |
| `main` | — | Group integration |
| `legacy/qwen` | Retrieval + Qwen reranker | Teammate experiment, not loaded by the evaluator |

The scored configuration is frozen. `report/freeze.md` records the algorithm-freeze
commit and the gates that would be required to reopen it.

## The Challenge

Build an AI shopping agent that asks useful follow-up questions and recommends the
customer's hidden target product within at most 10 turns.

For each session the agent receives an anonymized preference profile and a short
customer message. Raw user IDs, review text, timestamps and purchase history are never
disclosed. On every turn the agent may ask a natural clarification question in
`message` while naming one requested field in `ask_attribute`, return a ranked list of
up to 10 catalog `parent_asin` values, or do both. A session ends when the target
appears in the scored Top 10, or after turn 10. Sessions cover Buying, Browsing,
Intent Override and Boundary behaviour.

Metrics: **Hit Rate@10** is the fraction of sessions that find the target within 10
turns; **MRR** is the mean reciprocal rank, with a miss contributing zero; **MTTC** is
the mean first-hit turn, with a miss assigned turn 11. Reported token usage is a
feasibility metric, not part of the core technical score.

Participant rules are in `docs/submission_rules.md` and
`docs/competition_specification.md`.

## Data Source

The catalog and sessions are derived from Amazon Reviews 2023 by McAuley Lab, UCSD.
Sessions are sampled deterministically from the official Clothing 5-core
leave-last-out split and joined to the frozen catalog. See `DATA_ATTRIBUTION.md`
before using or redistributing the data.
