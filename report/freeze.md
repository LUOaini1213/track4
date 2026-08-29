# Submission freeze：E123 champion

E123 不再当实验版。只在 **正确性 bug** 或 **真正新的信息源** 时重开 PUBLIC。holdout 上 +0.0005 的新 heuristic 不碰冠军。

## 锁定

| | |
|---|---|
| 分支 | `contest/public` |
| 计分入口 | `starter.agent.Agent` → `ContestAgent` + `PUBLIC` |
| 停问策略 | `progress_defer="e123"`（一次性 other，不是问到四槽） |
| 排序 | **未改** `rank()`：热度 1.0 + 精确行 0.35 + 短语 0.15 + MiniLM 0.1 |
| LLM | `llm_listwise=False`，0 token |
| Commit SHA | 见同目录提交后回填；以 `git rev-parse contest/public` 为准 |

## 冠军数字

| 集合 | Hit@10 | MRR | MTTC | TechnicalScore | Rank1 |
|---|---:|---:|---:|---:|---:|
| Public 200 | **1.000** | 0.954167 | 2.75 | **0.95125** | 184 |
| Holdout 200 | **0.980** | 0.864845 | 2.885 | **0.911753** | **162** |
| Random 800 八片均值 A | 0.9738 | 0.8439 | 2.71 | 0.9058 | 612 |
| Random 800 八片均值 e123 | 0.9738 | **0.8880** | 2.90 | **0.9153** | **672** |

答辩数字：**+60 Rank-1 / 800 unseen sessions, with zero Hit-rate loss**（8/8 shard 同向）。

Holdout Rank1 相对更早的 144 是 **+18**，Hit 仍 0.980。oracle +0.0156 吃掉约 83%。

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

## 环境（hardening，Windows）

| | |
|---|---|
| OS | Windows-10-10.0.22631-SP0 |
| Python | 3.11.5 (Anaconda, MSC v.1916 64-bit) |
| 计分 | 内存索引，0 token |
| 测试 | `tests.test_contest_agent` 全绿；全库 129 测里 **1 条预存在** Windows `Path("/content/")` 失败（非 ContestAgent） |

## 无 MiniLM 缓存 / 无 API key 回退

`TECHJAM_DENSE_OFFLINE=1`、`HF_HUB_OFFLINE=1`、空 `HF_HOME`，且去掉 DeepSeek/OpenAI key。`get_encoder().available() == False`。

| 集合 | Hit@10 | MRR | MTTC | 分 | Rank1 | token |
|---|---:|---:|---:|---:|---:|---:|
| Public nodense | **1.000** | 0.961131 | 2.75 | 0.953339 | 187 | 0 |
| Holdout nodense | 0.975 | 0.868429 | 2.925 | 0.909529 | 162 | 0 |

VoI stop 不依赖 MiniLM（公开 MTTC 仍 2.75）。Holdout 少 `0090`（rubber sole，已知要 MiniLM）。**官方计分路径有缓存时 Hit 0.980。** 工件：`report/freeze_nodense.json`。

## 提交清单

- `python -m unittest discover -s tests -v`（ContestAgent 合同绿）
- `python -m evaluator.local_evaluator` 入口是 `Agent`
- `results_contest_public.json` / `holdout/ours_holdout.json` 为带 MiniLM 的冠军数字
- 跨 shard：`holdout/shards/a_vs_e123.json`，**8/8 e123 > A**

