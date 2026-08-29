# Submission freeze：E123 champion

E123 不再当实验版。只在 **正确性 bug** 或 **真正新的信息源** 时重开 PUBLIC。holdout 上 +0.0005 的新 heuristic 不碰冠军。**不要再优化 E123 或 `rank()`。**

答辩主线：**Evidence-Aware Conversational Search with Value-of-Information Stopping**。

最强的一页不是 Public `0.95125`，而是：

> **+60 Rank-1 recommendations across 800 unseen ID-disjoint sessions, with zero Hit-rate loss; improvement on all 8/8 shards.**

## 唯一 SHA

不要同时报两个 commit 当“提交版”。数字来自算法冻结；提交物是带 MiniLM sidecar loader 的 `contest/public` 树。

| 角色 | SHA | 含义 |
|---|---|---|
| **Algorithm freeze** | `3a31aceb969a0697511e254f7273f8b57cb40fce` | 最后一次改 E123 / `rank()`。下面的冠军数字来自这里。 |
| **Submission SHA** | `contest/public` 的 `git rev-parse HEAD` | 含 MiniLM 可获得性闭环与本文件。**评委只引用这一个。** |

`3a31ace` 之后的 commit **不允许**改 PUBLIC knobs 或 `rank()`。本文件若与 `git rev-parse HEAD` 不一致，以 HEAD 为准，并在提交当日把 HEAD 写进 Devpost。

个人仓库：`LUOaini1213/techjam-conversational-search` 分支 `contest/public`。组仓库迁移是另一次可审计动作，迁移后必须重跑官方入口，不要假设两仓内容一致。

## 锁定

| | |
|---|---|
| 分支 | `contest/public` |
| 计分入口 | `starter.agent.Agent` → `ContestAgent` + `PUBLIC` |
| 停问策略 | `progress_defer="e123"`（一次性 other，不是问到四槽） |
| 排序 | **未改** `rank()`：热度 1.0 + 精确行 0.35 + 短语 0.15 + MiniLM 0.1 |
| LLM | `llm_listwise=False`，0 token |
| Encoder | `sentence-transformers/all-MiniLM-L6-v2` @ `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`；`model.safetensors` sha256 `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db` |

## 冠军数字（有 MiniLM）

| 集合 | Hit@10 | MRR | MTTC | TechnicalScore | Rank1 |
|---|---:|---:|---:|---:|---:|
| Public 200 | **1.000** | 0.954167 | 2.75 | **0.95125** | 184 |
| Holdout 200 | **0.980** | 0.864845 | 2.885 | **0.911753** | **162** |
| Random 800 八片均值 A | 0.9738 | 0.8439 | 2.71 | 0.9058 | 612 |
| Random 800 八片均值 e123 | 0.9738 | **0.8880** | 2.90 | **0.9153** | **672** |

答辩数字：**+60 Rank-1 / 800 unseen sessions, with zero Hit-rate loss**（8/8 shard 同向）。

Holdout Rank1 相对更早的 144 是 **+18**，Hit 仍 0.980。oracle +0.0156 吃掉约 83%。剩余 oracle gap ~0.0026，小于 MiniLM 缺失造成的 Hit `0.980→0.975`。

## 闸

Public Hit = 1.000；Holdout Hit ≥ 0.980。**下一闸 > 0.911753 仅用于 correctness / 新信息源。** 不再为 holdout 200 上的第 N 个 stopping 规则开 PUBLIC。

## 入口核对

```text
starter.agent.Agent  →  ContestAgent  →  PUBLIC
MRO: Agent, ContestAgent, object
PUBLIC.progress_defer = "e123"
PUBLIC.ambiguity_defer = "a"
PUBLIC.llm_listwise = False
```

## MiniLM 是提交正确性依赖

无缓存 / `TECHJAM_DENSE_OFFLINE=1` / `HF_HUB_OFFLINE=1` / 空 `HF_HOME`、无 API key 时：`get_encoder().available() == False`，dense=0。

| 集合 | Hit@10 | MRR | MTTC | 分 | Rank1 | token |
|---|---:|---:|---:|---:|---:|---:|
| Public nodense | **1.000** | 0.961131 | 2.75 | 0.953339 | 187 | 0 |
| Holdout nodense | **0.975** | 0.868429 | 2.925 | 0.909529 | 162 | 0 |

VoI stop 不依赖 MiniLM（公开 MTTC 仍 2.75）。Holdout 少 `0090`（rubber sole）。**Agent 能跑 ≠ 分数等价。** 冠军路径是有 MiniLM 的 Hit `0.980`。工件：`report/freeze_nodense.json`。

### 官方 Q&A 实际说了什么

不是“final evaluation 环境保证网络/API 可访问”。

| 来源 | 原话大意 |
|---|---|
| kit `docs/submission_rules.md` | official final scoring **may disable network**；须声明是否需要联网；允许 lightweight local assets |
| 2026-08-28 workshop Chenxing 43:39 | 可 bundle 合法预训练权重；大文件用 documented download，**不要 commit 进 git**；允许 sidecar |
| 同上 47:11 | 外部 LLM API / 本地模型 / 非 LLM 都允许，**因为 teams run final evaluation in their own environments**；凭据、限额、可用性、成本自负 |

因此：

1. **最稳：提交 zip 携带** `models/all-MiniLM-L6-v2/`（Apache-2.0，`python scripts/vendor_minilm.py`）。加载器优先读它。
2. 评分机有网时，加载器会拉 **同一 pinned revision**，不换 encoder。
3. **不要**改成线上 embedding API：超时、限流、key、结果漂移都会重开 ranking validation。冻结版已经 8/8 shard 过闸。

加载顺序：`TECHJAM_DENSE_HOME` → `models/all-MiniLM-L6-v2` → HF 缓存 → Hub。见 `models/README.md`。

## 环境（hardening，Windows）

| | |
|---|---|
| OS | Windows-10-10.0.22631-SP0 |
| Python | 3.11.5 (Anaconda, MSC v.1916 64-bit) |
| 计分 | 内存索引，0 token |
| 测试 | **133/133 绿。** 原先 Windows 上 `Path("/content/")` 失败的是 `tests.test_reranker_benchmark.test_local_path_validation_is_portable_and_explicit`——**Legacy/Qwen Colab 路径助手，不是 ContestAgent，不影响 scoring path**。断言已改为与 `Path.resolve()` 比较。 |

## 提交清单

- `python scripts/vendor_minilm.py` 后确认 `models/all-MiniLM-L6-v2/model.safetensors` 存在（zip 带上；不要推进 git）
- `python -m unittest discover -s tests -v`（133/133。Path("/content/") 曾是 infrastructure-only，现已 portable）
- `python -m evaluator.local_evaluator` 入口是 `Agent`
- `results_contest_public.json` / `holdout/ours_holdout.json` 为 **带 MiniLM** 的冠军数字
- 跨 shard：`holdout/shards/a_vs_e123.json`，**8/8 e123 > A**
- 组仓库迁移后 **clean-room 再跑一次官方入口**，不要假设 personal clone ≡ group repo
