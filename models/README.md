# MiniLM sidecar（计分依赖，不是可选增强）

Champion 数字（Public `0.95125` / Holdout Hit `0.980`）用的是本地
`sentence-transformers/all-MiniLM-L6-v2`，钉死 revision：

```text
c9745ed1d9f207416be6d2e6f8de32d1f16199bf
```

许可证：**Apache-2.0**（允许随提交物分发）。加载器不会换成别的 encoder。

## 官方规则怎么说

两套原文不是同一句话：

| 来源 | 原意 | 不意味着 |
|---|---|---|
| kit `docs/submission_rules.md` | official final scoring **may disable network**；须声明是否需要联网；允许 lightweight local assets | 评分机一定预装 MiniLM |
| 2026-08-28 workshop Chenxing Q&A 43:39 | 可以 bundle 合法预训练权重；大文件用 **documented download**，不要 commit 进 git；允许 local sidecar | 必须把 90MB 推进 GitHub |
| 同上 47:11 | 可以用外部 LLM API / 本地模型 / 非 LLM，**因为 teams run final evaluation in their own environments** | final eval **保证** 网络或 Hub 可访问 |

所以：**允许线上模型 ≠ 评分环境一定能拿到这份 MiniLM。** 不要为了“可以线上”去换更大的在线 embedding——那是换模型，会重开 ranking validation。

## 加载顺序

`TECHJAM_DENSE_HOME` → 本目录 `all-MiniLM-L6-v2/` → Hugging Face 缓存 → 允许联网时 Hub 拉**同一 revision**。

缺权重时 Agent 仍能跑（dense=0），但 **不是分数等价**：Holdout Hit `0.980 → 0.975`，明确掉 `0090`。VoI stop（E123）不依赖 MiniLM。

## 怎么落到磁盘

```bash
python scripts/vendor_minilm.py
```

会写出 `models/all-MiniLM-L6-v2/`（gitignored）。Devpost / 提交 zip **应带上这个目录**，这样评分机即使断网、没有 HF 缓存，仍走 0.980 路径。

权重文件 `model.safetensors` 钉死 **Hub LFS oid**（revision `c9745ed1`，90,868,376 字节）：

```text
53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db
```

`python scripts/vendor_minilm.py` 必须打印这个值。本机 Hugging Face 缓存里曾有一份小 64 字节的副本（`c24bb44a…` / 90,868,312）；冠军 eval 走的是缓存。sidecar 以 Hub 为准，不是换 encoder。不要去追浮动的 `main`。
