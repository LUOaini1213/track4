# 报告目录（ContestAgent PUBLIC）

计分实现：`starter/shopping_agent/contest_*.py`。评估器加载的 `starter.agent.Agent` 就是它。组员 Qwen 实验见分支 `legacy/qwen`。

## 当前分数

| 集合 | n | Hit@10 | MRR | MTTC | 技术分 | 说明 |
|---|---:|---:|---:|---:|---:|---|
| 公开 200 | 200 | 1.000 | 0.9542 | 2.75 | **0.95125** | `results_contest_public.json`，0 token |
| ID-holdout 200 | 200 | 0.980 | 0.8648 | 2.885 | **0.9118** | 排除公开集 asin，不是官方私有 800 |
| 随机 800 | 800 | 0.9725 | 0.8249 | 2.691 | **0.89989** | 8×100 并行；**跳过泛约束 MiniLM 之前**的快照 |

技术分 = `0.50×Hit + 0.30×MRR + 0.20×Efficiency`。**E123 已冻结为提交候选**（`report/freeze.md`）。下一闸 > 0.911753 **只接受正确性 bug 或新信息源**，不为 holdout 上 +0.0005 的 heuristic 改 PUBLIC。

## 读哪篇

| 文件 | 内容 |
|---|---|
| [methods.md](methods.md) | 公开 200 消融：去留表（标题覆盖、FlashRank、gate 8–10、RRF 等已拒） |
| [holdout.md](holdout.md) | holdout 200 是什么、和同学对照 |
| [optimize.md](optimize.md) | 还怎么涨分（不要再刷公开集） |
| [optimize_kb.md](optimize_kb.md) | **不要新建知识库**；硬池 IDF/BM25 优先 |
| [architecture.md](architecture.md) | VoI stopping 数据流；override 分档 / 响应守卫 |
| [attribution.md](attribution.md) | E1/E2/E3 对 ΔMRR、ΔMTTC、Rank1 的可加贡献 |
| [robustness.md](robustness.md) | 8×100 ID-disjoint shard：e123 vs A，8/8 同向 |
| [freeze.md](freeze.md) | **提交冻结**：唯一 SHA、MiniLM 是正确性依赖、Path("/content/") 为 infrastructure-only |
| [complete_agent.md](complete_agent.md) | 五段完整 Agent：RRF 实测、LLM blend、门控、为何不做 LambdaMART |
| [provenance.md](provenance.md) | catalog-side oracle：feature/details/clone/store；**不进 rank()** |
| [disclosure.md](disclosure.md) | turn/disclosure oracle：+1 other 的 EVI；下一刀不是收窄 A |
| [submit.md](submit.md) | 复现命令、0 token / $0、延迟、限制、贡献 |
| [rubric_4_6.md](rubric_4_6.md) | Image #1 五轴对照；IDF / 独占稀有词 / 泛约束小池 MiniLM 均未进 PUBLIC |

演示记录（官方模拟器重放）：[buying](demo_buying.txt) · [browsing](demo_browsing.txt) · [override](demo_override.txt) · [boundary](demo_boundary.txt)。

## 复现

```bash
python eval_contest.py --only public
python eval_holdout.py --skip-generate
python demo/run_demo.py --session public_0002
python -m unittest discover -s tests -v
```

协议骨架（不要为公开集再拧）：永远问 `other`、逐字 AND、`gate_size=5`、Override 前不出表、`dump_slots=4`。3 槽 field-flat 再问一轮（`ambiguity_defer=a`）。Buying/Browsing 在池 ≤5 但槽未满、或 3 槽 leftover 时再问一轮（`progress_defer=e123`，一次性）。MiniLM 只在有区分项的硬池上。硬池精确行 `w_field=0.35`，标题短语 `w_phrase=0.15`。缺权重则 dense 为 0（Holdout Hit 0.975，不是冠军路径）。
