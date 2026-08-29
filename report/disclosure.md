# Turn / disclosure oracle (holdout, PUBLIC=`ambiguity_defer=a`)

不改 `rank()`。官方计分出表后**继续 1–2 轮 `other`**（评估器本来会停），看 ΔMRR 能否付 MTTC 税。
`net_technical_gain_1` = 单条对总分的贡献 `(0.5ΔHit + 0.3ΔRR − 0.02Δturns)/200`。闸：Public Hit=1.000 / Holdout Hit≥0.980 / score>0.898718。

buckets `{'rank3-5': 22, 'rank1': 145, 'rank2': 16, 'miss': 4, 'rank6-10': 13}`。强制 +1 other 赚钱的会话：**23**。

## Simulator disclosure

Intent card 顺序固定：`features+details` 去重后 `hard=[:2]`，`soft=[2:4]`（不够则复制 hard[:1]）。
`other` 按这个顺序取**尚未进入 `disclosed` 的最多 2 条**。Buying 开场泄 hard[0]；Browsing 开场 0 条；空则 `no additional preference`。

### 每次 other 泄出条数（开场之后）

| 泄出序列 (每轮 n) | n |
|---|---:|
| `(2, 2, 0, 0)` | 56 |
| `(2, 1, 0)` | 53 |
| `(2, 2, 0)` | 49 |
| `(2, 1, 0, 0)` | 15 |
| `(2, 1)` | 11 |
| `(0, 2, 2, 0, 0)` | 5 |
| `(0, 2, 2, 0)` | 5 |
| `(2, 2, 0, 0, 0, 0, 0, 0)` | 2 |
| `(2, 2, 0, 0, 0, 0, 0, 0, 0)` | 1 |
| `(2, 0)` | 1 |
| `(2, 1, 0, 0, 0, 0, 0, 0, 0)` | 1 |
| `(1, 0)` | 1 |

### 第 4 个已披露槽来自哪

| source | card 位 | scenario | n |
|---|---:|---|---:|
| feature | None | browsing | 32 |
| feature | None | buying | 15 |
| feature | None | intent_override | 13 |
| details | None | browsing | 7 |
| details | None | buying | 5 |
| details | None | intent_override | 5 |
| feature | None | boundary | 4 |
| details | None | boundary | 1 |
| feature | 4 | browsing | 1 |
| extracted | 2 | intent_override | 1 |

## Residual：多问一轮是否赚钱

| sample | scen | t | slots | remain | rank0 | rank+1 | rank+2 | pool0 | pool+1 | ΔRR | net | profit | field_flat |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| holdout_0084 | buying | 2 | 3 | 1 | 10 | 1 | 1 | 12 | 1 | 0.9 | 0.00125 | true | false |
| holdout_0173 | buying | 2 | 3 | 1 | 6 | 1 | 1 | 20 | 1 | 0.833333 | 0.00115 | true | false |
| holdout_0054 | browsing | 2 | 2 | 2 | 4 | 1 | 1 | 4 | 1 | 0.75 | 0.001025 | true | true |
| holdout_0113 | buying | 2 | 3 | 1 | 3 | 1 | 1 | 3 | 1 | 0.666667 | 0.0009 | true | true |
| holdout_0120 | buying | 1 | 1 | 3 | 3 | 1 | 1 | 5 | 1 | 0.666667 | 0.0009 | true | false |
| holdout_0129 | buying | 1 | 1 | 3 | 3 | 1 | 1 | 5 | 1 | 0.666667 | 0.0009 | true | true |
| holdout_0149 | browsing | 2 | 2 | 2 | 3 | 1 | 1 | 3 | 1 | 0.666667 | 0.0009 | true | true |
| holdout_0169 | browsing | 2 | 2 | 2 | 3 | 1 | 1 | 3 | 1 | 0.666667 | 0.0009 | true | false |
| holdout_0181 | buying | 2 | 3 | 1 | 3 | 1 | 1 | 4 | 1 | 0.666667 | 0.0009 | true | true |
| holdout_0010 | buying | 1 | 1 | 3 | 2 | 1 | 1 | 3 | 1 | 0.5 | 0.00065 | true | true |
| holdout_0045 | boundary | 3 | 2 | 2 | 2 | 1 | 1 | 4 | 1 | 0.5 | 0.00065 | true | false |
| holdout_0059 | boundary | 3 | 2 | 2 | 2 | 1 | 1 | 2 | 1 | 0.5 | 0.00065 | true | true |
| holdout_0062 | browsing | 2 | 2 | 2 | 2 | 1 | 1 | 4 | 1 | 0.5 | 0.00065 | true | true |
| holdout_0093 | buying | 2 | 3 | 1 | 2 | 1 | 1 | 2 | 1 | 0.5 | 0.00065 | true | true |
| holdout_0123 | buying | 2 | 3 | 1 | 2 | 1 | 1 | 2 | 1 | 0.5 | 0.00065 | true | true |
| holdout_0124 | buying | 1 | 1 | 3 | 2 | 1 | 1 | 4 | 2 | 0.5 | 0.00065 | true | true |
| holdout_0125 | buying | 2 | 3 | 1 | 2 | 1 | 1 | 2 | 1 | 0.5 | 0.00065 | true | true |
| holdout_0160 | browsing | 2 | 2 | 2 | 2 | 1 | 1 | 2 | 1 | 0.5 | 0.00065 | true | true |
| holdout_0184 | buying | 2 | 3 | 1 | 7 | 2 | 2 | 11 | 2 | 0.357143 | 0.00043571 | true | false |
| holdout_0078 | boundary | 3 | 2 | 2 | 3 | 2 | 2 | 3 | 2 | 0.166667 | 0.00015 | true | true |
| holdout_0088 | intent_override | 4 | 4 | 0 | 3 | 2 | 2 | 10 | 10 | 0.166667 | 0.00015 | true | false |
| holdout_0102 | buying | 2 | 3 | 1 | 3 | 2 | 2 | 19 | 13 | 0.166667 | 0.00015 | true | false |
| holdout_0016 | buying | 2 | 3 | 1 | 4 | 3 | 3 | 9 | 6 | 0.083333 | 2.5e-05 | true | false |
| holdout_0035 | buying | 2 | 3 | 1 | 10 | 6 | 6 | 13 | 8 | 0.066667 | -0.0 | false | false |
| holdout_0026 | intent_override | 3 | 3 | 2 | 6 | 5 | 5 | 8 | 5 | 0.033333 | -5e-05 | false | false |
| holdout_0067 | buying | 3 | 4 | 0 | 10 | 8 | 8 | 13 | 13 | 0.025 | -6.25e-05 | false | false |
| holdout_0001 | browsing | 3 | 4 | 0 | 4 | 4 | 4 | 5 | 5 | 0.0 | -0.0001 | false | true |
| holdout_0003 | browsing | 3 | 4 | 0 | 2 | 2 | 2 | 2 | 2 | 0.0 | -0.0001 | false | true |
| holdout_0017 | buying | 3 | 4 | 0 | 4 | 4 | 4 | 6 | 6 | 0.0 | -0.0001 | false | false |
| holdout_0018 | browsing | 3 | 4 | 0 | 3 | 3 | 3 | 6 | 6 | 0.0 | -0.0001 | false | false |
| holdout_0025 | browsing | 3 | 4 | 0 | 7 | 7 | 7 | 10 | 10 | 0.0 | -0.0001 | false | true |
| holdout_0032 | intent_override | 4 | 4 | 0 | 2 | 2 | 2 | 4 | 4 | 0.0 | -0.0001 | false | false |
| holdout_0033 | browsing | 3 | 4 | 0 | 2 | 2 | 2 | 8 | 8 | 0.0 | -0.0001 | false | false |
| holdout_0042 | intent_override | 4 | 4 | 0 | 6 | 6 | 6 | 25 | 25 | 0.0 | -0.0001 | false | false |
| holdout_0056 | intent_override | 4 | 4 | 0 | 2 | 2 | 2 | 3 | 3 | 0.0 | -0.0001 | false | false |
| holdout_0076 | browsing | 3 | 4 | 0 | 4 | 4 | 4 | 5 | 5 | 0.0 | -0.0001 | false | false |
| holdout_0079 | browsing | 3 | 4 | 0 | 3 | 3 | 3 | 6 | 6 | 0.0 | -0.0001 | false | true |
| holdout_0090 | browsing | 3 | 4 | 0 | 10 | 10 | 12 | 30 | 30 | 0.0 | -0.0001 | false | false |
| holdout_0100 | buying | 2 | 3 | 1 | 3 | 3 | 3 | 3 | 3 | 0.0 | -0.0001 | false | true |
| holdout_0104 | intent_override | 4 | 4 | 0 | 2 | 2 | 2 | 6 | 6 | 0.0 | -0.0001 | false | false |
| holdout_0106 | buying | 3 | 4 | 0 | 6 | 6 | 8 | 23 | 23 | 0.0 | -0.0001 | false | false |
| holdout_0122 | buying | 3 | 4 | 0 | 6 | 6 | 6 | 20 | 20 | 0.0 | -0.0001 | false | false |
| holdout_0138 | buying | 3 | 4 | 0 | 3 | 3 | 3 | 33 | 33 | 0.0 | -0.0001 | false | true |
| holdout_0143 | intent_override | 3 | 3 | 2 | 3 | 3 | 4 | 11 | 6 | 0.0 | -0.0001 | false | false |
| holdout_0144 | buying | 3 | 4 | 0 | 2 | 2 | 2 | 2 | 2 | 0.0 | -0.0001 | false | true |
| holdout_0153 | browsing | 3 | 4 | 0 | 2 | 2 | 2 | 4 | 4 | 0.0 | -0.0001 | false | false |
| holdout_0162 | browsing | 3 | 4 | 0 | 7 | 7 | 6 | 26 | 26 | 0.0 | -0.0001 | false | false |
| holdout_0172 | buying | 3 | 4 | 0 | 3 | 3 | 3 | 8 | 8 | 0.0 | -0.0001 | false | true |
| holdout_0180 | browsing | 3 | 4 | 0 | 3 | 3 | 3 | 16 | 16 | 0.0 | -0.0001 | false | false |
| holdout_0187 | browsing | 3 | 4 | 0 | 5 | 5 | 5 | 6 | 6 | 0.0 | -0.0001 | false | true |
| holdout_0191 | boundary | 4 | 4 | 0 | 6 | 6 | 6 | 37 | 37 | 0.0 | -0.0001 | false | false |

## 赚钱会话在问之前的可观测结构

| sample | bucket | slots | pool | remain | last_leak | field_flat | phrase_flat | pop_gap | scen |
|---|---|---:|---:|---:|---:|---|---|---:|---|
| holdout_0010 | rank2 | 1 | 3 | 3 | 0 | true | true | 0.0043 | buying |
| holdout_0016 | rank3-5 | 3 | 9 | 1 | 2 | false | true | 0.0187 | buying |
| holdout_0045 | rank2 | 2 | 4 | 2 | 2 | false | true | 0.095 | boundary |
| holdout_0054 | rank3-5 | 2 | 4 | 2 | 2 | true | true | 0.0025 | browsing |
| holdout_0059 | rank2 | 2 | 2 | 2 | 2 | true | true | 0.0848 | boundary |
| holdout_0062 | rank2 | 2 | 4 | 2 | 2 | true | true | 0.1309 | browsing |
| holdout_0078 | rank3-5 | 2 | 3 | 2 | 2 | true | true | 0.0483 | boundary |
| holdout_0084 | rank6-10 | 3 | 12 | 1 | 2 | false | true | 0.0581 | buying |
| holdout_0088 | rank3-5 | 4 | 10 | 0 | 1 | false | true | 0.0153 | intent_override |
| holdout_0093 | rank2 | 3 | 2 | 1 | 2 | true | true | 0.2075 | buying |
| holdout_0102 | rank3-5 | 3 | 19 | 1 | 2 | false | true | 0.0255 | buying |
| holdout_0113 | rank3-5 | 3 | 3 | 1 | 2 | true | true | 0.2117 | buying |
| holdout_0120 | rank3-5 | 1 | 5 | 3 | 0 | false | true | 0.0 | buying |
| holdout_0123 | rank2 | 3 | 2 | 1 | 2 | true | true | 0.2331 | buying |
| holdout_0124 | rank2 | 1 | 4 | 3 | 0 | true | true | 0.0219 | buying |
| holdout_0125 | rank2 | 3 | 2 | 1 | 2 | true | true | 0.1545 | buying |
| holdout_0129 | rank3-5 | 1 | 5 | 3 | 0 | true | true | 0.042 | buying |
| holdout_0149 | rank3-5 | 2 | 3 | 2 | 2 | true | true | 0.03 | browsing |
| holdout_0160 | rank2 | 2 | 2 | 2 | 2 | true | true | 0.07 | browsing |
| holdout_0169 | rank3-5 | 2 | 3 | 2 | 2 | false | true | 0.1376 | browsing |
| holdout_0173 | rank6-10 | 3 | 20 | 1 | 2 | false | true | 0.0184 | buying |
| holdout_0181 | rank3-5 | 3 | 4 | 1 | 2 | true | true | 0.0 | buying |
| holdout_0184 | rank6-10 | 3 | 11 | 1 | 2 | false | true | 0.0986 | buying |

## 合法 / 非法 policy 上界（全 200 条，+1 other）

| policy | fire | profit | waste | ΔMRR | ΔMTTC | ΔScore | 过闸? |
|---|---:|---:|---:|---:|---:|---:|---|
| god_profit (illegal, uses future rank) | 23 | 23 | 0 | 0.059619 | 0.115 | 0.015586 | yes |
| remain>0 | 120 | 22 | 96 | 0.056786 | 0.6 | 0.005036 | yes |
| remain>0 and rank>1 | 26 | 22 | 2 | 0.059286 | 0.13 | 0.015186 | yes |
| remain>0 and rank6-10 | 5 | 3 | 0 | 0.010952 | 0.025 | 0.002786 | yes |
| n_slots==3 and pool>5 (wider than A) | 9 | 5 | 2 | 0.012202 | 0.045 | 0.002761 | yes |
| n_slots==3 and field_flat and pool 6-20 (A) | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 | no |
| rank>1 and field_flat and remain>0 | 15 | 14 | 1 | 0.037917 | 0.075 | 0.009875 | yes |
| rank>1 and last_leak==2 | 34 | 18 | 15 | 0.047452 | 0.17 | 0.010836 | yes |
| last_leak==2 and remain>0 | 96 | 18 | 77 | 0.044952 | 0.48 | 0.003886 | yes |

`remain>0 and rank>1` 偷看 target 名次，不能做 PUBLIC。`god_profit` 偷看未来名次。
A 已经在跑；出表时再测 `n_slots==3 ∧ field_flat ∧ pool 6–20` 为 0，是因为那些会话已经被 A 推到了第 4 槽。

合法、不偷看名次的两条候选（holdout 切片，**尚未**上官方闸）：

| policy | fire | profit | waste | rank1 被拖 | ΔScore |
|---|---:|---:|---:|---:|---:|
| 小池未完成：`2≤pool≤5` 且 `slots<4` 且 remain>0 | 33 | 17 | 16 | 15（**0141 rank1→2**） | +0.010075 |
| 3 槽 leftover：`slots==3` 且 `pool>5`（field 不 flat，A 没拦） | 9 | 5 | 2 | 1（0185 仍 rank1） | +0.002761 |
| 两者并集 | 42 | 22 | 18 | 16 | +0.012836 |

## 三个问题的答案

**1. 哪些 session 多问一次真的赚钱？**

23 条。几乎全是 **出表时卡还没问完**（remain>0），多问一轮后 hard-AND 把池子收到 1–2。最大头：`0084` 10→1、`0173` 6→1、`0054` 4→1。

rank6–10 的 13 条里 **8 条 remain=0、4 槽已经问完**，再问只付 MTTC（0122/0090/0025 这一类）。有剩余槽的 5 条才是 3 槽 leftover（0084/0173/0184 赚钱，0026/0035 增量付不起税）。

四条 miss 的 remain=0、池 24–568，再问帮不上。

**2. 问之前合法可观测的共同特征？两类，都不是收窄 A。**

- **Gate-early**：`pool≤5` 触发 `gate_size=5` 出表，但 `slots` 只有 1–3。Buying 开场 1 槽、Browsing 第一次 other 后 2 槽、Boundary 跳过一轮后 2 槽。A 不管这条路。
- **3-slot leftover**：`min_slots=3` 出表且 field **不** flat（所以 A 放行），池 9–20，卡上还剩 1 条。下一条往往能把池 AND 到 1。

偷看 `rank>1` 的 oracle ΔScore=+0.015，但不能用。`remain>0` 全开会拖 96 条 rank1，0141 还会 1→2。

**3. 第四槽 vs 前三槽的 disclosure 有没有规律？**

有，而且是模拟器写死的：

- Card 顺序固定：features+details 去重后 `hard=[:2]`，`soft=[2:4]`。`other` 按此顺序最多取 2 条未披露。
- Buying：开场 hard[0] → 第一次 other 2 条 → **第 4 条是第二次 other 的 1 条**（序列 `(2,1,0)` 53 次）。
- Browsing：开场 0 → other 2+2 填满 4 条后 `no additional`（`(2,2,0,0)` 56 次）。
- 空回复 = 卡面耗尽，不是模糊。

所以 EVI 不是猜「下一句语义」，而是：「还没走到 dump_slots=4 / 还没听到 no-additional，就不要因为 pool≤5 或 3 槽 shortcut 停。」

## 结论（本轮不改代码）

`rank()` 继续冻。PUBLIC 继续 `ambiguity_defer="a"`。

下一刀如果做，是 **EVI defer**，不是 `ambiguity_defer=b`：

1. 小池未完成：pool 已 ≤gate 但槽 <4 且 other 未 exhausted。  
2. 可选：3 槽 leftover（field 不 flat 的 min_slots）。

两者都要先过官方闸；**0141** 说明再问一轮可以把已经 Rank1 的会话打到 Rank2。未评 public 之前不上。

## Stop/Continue 实测（E1 / E2 / E3 分开，再组合）

Shrink：Buying 开场 1 槽且池 ≤5，`P(shrink≤0.4)=0.38`；Buying 3 槽且池 6–20，`P=0.43`；Browsing 2 槽且池 ≤5，中位数 shrink=1.00（多数不再缩）。所以必须分 scenario。

| policy | Public Hit | Public 分 | Holdout Hit | Holdout MRR | MTTC | Holdout 分 | rank1 | 闸 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A only | 1.000 | 0.9547 | 0.980 | 0.80806 | 2.685 | 0.898718 | 145 | 旧地板 |
| E1 Buying | 1.000 | 0.95365 | 0.980 | 0.831393 | 2.780 | 0.903818 | 153 | 过（丢 0141） |
| E2 Browsing | 1.000 | 0.95295 | 0.980 | 0.829310 | 2.745 | 0.903893 | 152 | 过（0 丢失） |
| E3 leftover | 1.000 | 0.95405 | 0.980 | 0.820262 | 2.730 | 0.901479 | 147 | 过（0084/0173） |
| E1+E2 | 1.000 | 0.9519 | 0.980 | 0.852643 | 2.840 | 0.908993 | 160 | 过 |
| **E1+E2+E3** | **1.000** | **0.95125** | **0.980** | **0.864845** | **2.885** | **0.911753** | **162** | **晋升** |

一次 other，不是问到四槽。`remain>0` 全开的 120 次开火没做。0141 是已知税。

正式闸改为：**Public Hit=1.000 / Holdout Hit≥0.980 / TechnicalScore>0.911753。**

