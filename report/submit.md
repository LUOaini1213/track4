# 提交说明（ContestAgent PUBLIC）

官方要：可复现的 `Agent`、短报告、延迟 / token / 成本、一场多轮演示。计分入口是 `starter.agent.Agent`（ContestAgent + `PUBLIC`，`progress_defer="e123"`）。冻结说明见 `report/freeze.md`。

## 怎么跑

Python 3.10+。无 MiniLM 时计分路径只依赖标准库（能跑，Holdout Hit 0.975）。冠军数字需要同一份 MiniLM。

```bash
gzip -dc catalog.jsonl.gz > data/catalog.jsonl   # 发布包，见 SHA256SUMS
python -m unittest discover -s tests -v
python -m evaluator.local_evaluator --catalog data/catalog.jsonl --dataset data/public_set.jsonl --output results.json
python demo/run_demo.py --session public_0002
```

MiniLM（提交正确性依赖，不是性能等价 fallback）：`sentence-transformers/all-MiniLM-L6-v2` revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`。加载顺序：`TECHJAM_DENSE_HOME` → `models/all-MiniLM-L6-v2`（`python scripts/vendor_minilm.py`）→ HF 缓存 → 允许联网时 Hub 拉同一 revision。硬池余弦 `w_dense=0.1`（区分项且池 ≤6 时再加 `w_dense_tiny=0.12`）。加载失败则 dense=0：Holdout Hit **0.980→0.975**，掉 `0090`。强制不访问 Hub：`TECHJAM_DENSE_OFFLINE=1`。Devpost zip **应携带** sidecar；不要换成线上 embedding API。官方 Q&A 细节见 `report/freeze.md`。

可选 listwise LLM（默认关）：只在已经决定出表、短名单 ≤10 时重排，不改 `ask_attribute`（仍永远问 `other`）。密钥 `SHOPPING_AGENT_DEEPSEEK_API_KEY` 或桌面 `.env`；超时/坏 JSON 退回当前排序。打开：`ContestConfig(llm_listwise=True)` 或临时 `replace(PUBLIC, llm_listwise=True)`。没有 holdout > 0.911753 的证据前不进 PUBLIC。

## 模型、token、成本、延迟

| 组件 | 默认 | 成本 | 断网 |
|---|---|---|---|
| 类目锁 + 逐字 AND + 热度 | 标准库内存索引 | $0 | 是 |
| MiniLM | sidecar / 缓存 / 钉死 revision 的 Hub | $0 | 缺权重能跑但 Holdout Hit 0.975；zip 带 sidecar 则断网仍走 0.980 |
| Listwise LLM | 默认关；出表短名单才调 | 按 token | 超时/无密钥退回 0-token 排序 |
| DeepSeek / Qwen 问句 | 不计分 | — | 不要改 `ask_attribute` |

公开 200 次评估：`usage` **0 token**。本机 Windows、catalog 5 万条：索引约 8s，200 会话约 35s（约 0.2s/会话，含 MiniLM）。无 MiniLM 时会话循环更快；公开分接近，但 holdout 会掉 `0090`（Hit 0.975），不要把这条路径报成冠军。

## 演示会话

`demo/run_demo.py` 用官方模拟器策略重放公开集。稳定样本：

| 场景 | 命令 | 记录 |
|---|---|---|
| Buying | `--session public_0001` | `report/demo_buying.txt` |
| Browsing | `--session public_0006` | `report/demo_browsing.txt` |
| Intent Override | `--session public_0002` | `report/demo_override.txt` |
| Boundary | `--session public_0035` | `report/demo_boundary.txt` |

## 限制

- 公开 0.95 不能当私有 800 的预测；holdout 上 MRR 会掉（克隆共享模板句）。
- 热度名次深于 Top-10 的合取命中（holdout `0005/0052/0135/0183`）不倒热度硬抬。
- 模拟器只看 `ask_attribute`；字段必须继续问 `other`，口头问题可以复述已记意图。

## 贡献

- ContestAgent PUBLIC（`contest/public` / 本工作树）：模拟器协议、合取检索、holdout 门禁、演示与报告。
- `legacy/qwen`：组员 FTS / 结构化池 / 可选 Qwen，评估器不加载。
