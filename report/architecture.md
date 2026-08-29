# ContestAgent 架构（计分路径）

评估器加载的是 `starter.agent.Agent` → `ContestAgent` + `PUBLIC`。组仓库 `main` 上的单 Agent
检索管线是另一条实现；本分支只吸收它的**状态分档、响应守卫、离线契约**，不吸收 BM25/FTS/标题覆盖。

## 五段（与同学同构，默认权重不同）

```text
[1] 对话状态     ContestState：槽位、分档 override、口头复述已记意图
[2] 结构化召回   类目锁 + 逐字 AND（空过滤跳过）。不是 BM25 搜全库
[3] 门控         gate=5，dump_slots=4，Override 前不出表。字段永远 other
[4] 硬池多信号   热度 1.0 + 精确行 0.35 + 标题整句 0.15 + MiniLM 0.1（线性）
                 同池名次 RRF（pool_rrf_k=60）已测：公开 Hit 1.0→0.99，holdout Hit 0.98→0.975，**默认关**
[5] 二阶段重排   listwise LLM 仅出表且 n≤10，与当前序做 RRF blend，失败回退
                 PUBLIC 默认关。FlashRank / 整表替换已拒
```

缺 MiniLM 权重或 LLM 密钥时 [4][5] 该项为 0，[1]–[3] 仍能跑完。这符合 Track 4 范围内的 keyword/dense/hybrid + 会话状态 + 可选 LLM，且不依赖工业向量库或全模型训练。

## 每轮

```text
reset(session_id, user_profile)
respond(message, turn, top_k)
  parse_opening / parse_reply
  scoped override → ContestState
  类目锁 → 逐字 AND（空过滤跳过）
  池大则 withhold，继续问 other
  热度 + 精确 feature/details 行 + 可选 MiniLM（泛约束跳过）
  可选 listwise LLM 与当前序 RRF blend
  contest_response.guard_response
```

协议骨架不变：`ask_attribute` 永远是 `other`（模拟器只在这个槽上泄出 intent card 原文）、逐字 AND、`gate_size=5`、Override 前不出表、`dump_slots=4`。

口头问题会带上已记住的类目/约束，并点名还缺的 typed 面（材料、颜色、尺寸…）；字段仍是 `other`，所以不会换成问 `color` 而丢掉长句。`distinctive_early_cap` 已实现（硬池 ≤10 且有非泛化词则出表），公开 MTTC 2.53→2.505，但 holdout MRR 0.774→0.758、总分 0.8845，**默认关闭**。

## 从 group `main` 吸收的部分

| 吸收 | 落点 | 刻意没搬 |
|---|---|---|
| Override 分档：referenced / attribute_replace / global_reset | `contest_dialogue.py`、`contest_slots.apply_override` | classmate 式整表 wipe；官方模板仍 decay+AND |
| 响应合同守卫 | `contest_response.py` | FTS catalog、SQLite |
| 缺模型权重=0、不隐式下载 | 已有 `contest_dense.py`（`HF_HUB_OFFLINE`） | DeepSeek / Qwen 默认路径 |
| 诊断：`intent_scope` / `intent_epoch` / `superseded` | `last_diagnostics` | commit_policy 阈值堆 |

官方模拟器 override 原文是 `Actually, ignore my earlier preference. What I need is: …`，scope 为
`referenced_preference_replace`：首轮槽位权重打到 0.5，新值加入硬 AND。`change the color to blue`
才作废旧颜色；`forget everything` 才清空约束并保留类目。

## 不要改的排序默认

`PUBLIC` 的 `w_title=0`、`w_popularity=1.0`、`w_dense=0.1` + `dense_skip_generic`，硬池 ≤6 且已跑 MiniLM 时再加 `w_dense_tiny=0.12`，精确 feature/details 行 `w_field=0.35`，区分项整句标题 `w_phrase=0.15`。MiniLM **晚融合**：先 AND 出硬池，再 `score += 0.1 * min-max(cosine)`，不替代热度、不参与召回。group `main` 的
BM25 0.36 / 标题 0.12 / 热度 0.03 在公开集上 MRR 更差，禁止作为默认。
