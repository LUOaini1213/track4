# Final submission package

GitHub `contest/public` keeps the research trail. The **Devpost ZIP** is a clean scoring bundle. Do not delete holdout JSON from git just to look tidy.

Video and captions **must not embed a commit SHA**. Use:

`ByteSize · contest/public · reproducible locally`

Fill `git rev-parse HEAD` on Devpost **on the submit day**.

## ZIP must contain

| Path | Why |
|---|---|
| `starter/agent.py` | Official `Agent` facade → ContestAgent PUBLIC |
| `starter/shopping_agent/contest_*.py` | Scored path (VoI stop + late fusion) |
| `evaluator/local_evaluator.py` | Unmodified official harness |
| `README.md` | How to run |
| `requirements.txt` | Python 3.10+; MiniLM extras commented |
| `report/freeze.md` | Champion numbers, gates, MiniLM dependency |
| `report/architecture.md` | VoI controller diagram |
| `report/submit.md` | Cost / latency / fallback |
| `models/README.md` | Pinned MiniLM revision |
| **`models/all-MiniLM-L6-v2/`** | **Champion encoder. Not in git. Must be in the ZIP.** |
| `scripts/vendor_minilm.py` | Rebuild sidecar if needed |
| `demo/run_demo.py` | One multi-turn session |
| `docs/agent_api_contract.json` | Contract |

MiniLM is a **scoring dependency**, not an optional extra. Missing weights: Holdout Hit `0.980 → 0.975` (drops `0090`). After packing, confirm:

```text
models/all-MiniLM-L6-v2/config.json
models/all-MiniLM-L6-v2/model.safetensors
```

`model.safetensors` sha256 must be:

```text
53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db
```

If the folder is missing:

```bash
python scripts/vendor_minilm.py
```

then pack again. `python scripts/pack_submission.py` vendors MiniLM if missing, copies only the tokenizer + `model.safetensors` (not ONNX/TF/PyTorch duplicates), and writes `submission_dist/bytesize-track4.zip`. Expect roughly **100MB**, not 800MB.

## ZIP must not contain

- `.git/`, `.claude/`, `.cursor/`, `.trellis/`
- `holdout/holdout_200.jsonl`, `random_800.jsonl`, `holdout/shards/`
- `holdout/network_listwise_compare.json` (lists specific holdout misses)
- `report/demo_video/_frames/`, `node_modules/`
- API keys, `.env`, private evaluation labels
- MiniLM blobs **in git**; they belong in the ZIP only
- Edited evaluator / catalog

GitHub may still keep those research files. The ZIP is what a judge should unzip.

## Devpost (separate from the ZIP)

1. Public GitHub (group repo after clean-room copy — not this private research branch dump).
2. Written description (English).
3. Public 3-minute YouTube: `report/demo_video/bytesize_track4_demo.mp4` + `captions.en.srt`.
4. Final **Submission SHA** = `git rev-parse HEAD` of the tree you actually zip.

## Algorithm freeze (do not reopen)

- `progress_defer="e123"`, `ambiguity_defer="a"`, `llm_listwise=False`
- Do not change `rank()`
- Algorithm freeze commit: `3a31aceb969a0697511e254f7273f8b57cb40fce`
