# Catalog provenance oracle (holdout, PUBLIC=`ambiguity_defer=a`)

只统计，不改 `rank()`。快照是 **官方计分那一轮出表** 的 hard pool。
Residual 的 delta 是 `target − 当前榜首`；Rank1 对照是 `target − #2`。

覆盖 78 / 200。buckets: `{'rank3-5': 22, 'rank2': 16, 'rank1': 27, 'rank6-10': 13}`。

## Residual 表（rank 2 / 3–5 / 6–10）

| sample | rank | pop | pool | featΔ | detΔ | dkeyΔ | fam | brandΔ | storeΔ | same_fam |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| holdout_0003 | 2 | 1 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | true |
| holdout_0010 | 2 | 2 | 3 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0032 | 2 | 3 | 4 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0033 | 2 | 7 | 8 | 0 | 0 | 0 | 2 | 0 | 0 | true |
| holdout_0045 | 2 | 2 | 4 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0056 | 2 | 2 | 3 | 0 | 0 | 0 | 2 | 0 | 0 | true |
| holdout_0059 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | true |
| holdout_0062 | 2 | 2 | 4 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0093 | 2 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0104 | 2 | 4 | 6 | 0 | 0 | 0 | 2 | 0 | 0 | true |
| holdout_0123 | 2 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0124 | 2 | 4 | 4 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0125 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | true |
| holdout_0144 | 2 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0153 | 2 | 4 | 4 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0160 | 2 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0018 | 3 | 2 | 6 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0078 | 3 | 3 | 3 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0079 | 3 | 3 | 6 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0088 | 3 | 2 | 10 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0100 | 3 | 1 | 3 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0102 | 3 | 3 | 19 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0113 | 3 | 2 | 3 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0120 | 3 | 2 | 5 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0129 | 3 | 3 | 5 | 0 | 0 | 0 | 4 | 0 | 0 | true |
| holdout_0138 | 3 | 6 | 33 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0143 | 3 | 3 | 11 | 0 | 0 | 0 | 9 | 0 | 0 | true |
| holdout_0149 | 3 | 3 | 3 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0169 | 3 | 2 | 3 | -1 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0172 | 3 | 2 | 8 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0180 | 3 | 2 | 16 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0181 | 3 | 3 | 4 | 0 | 0 | 0 | 3 | 0 | 0 | true |
| holdout_0001 | 4 | 2 | 5 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0016 | 4 | 8 | 9 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0017 | 4 | 5 | 6 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0054 | 4 | 2 | 4 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0076 | 4 | 5 | 5 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0187 | 5 | 2 | 6 | 0 | 0 | 0 | 6 | 0 | 0 | true |
| holdout_0026 | 6 | 6 | 8 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0042 | 6 | 6 | 25 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0106 | 6 | 8 | 23 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0122 | 6 | 8 | 20 | 1 | -1 | -1 | 1 | 0 | 0 | false |
| holdout_0173 | 6 | 4 | 20 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0191 | 6 | 7 | 37 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0025 | 7 | 7 | 10 | 0 | 0 | 0 | 2 | 0 | 0 | false |
| holdout_0162 | 7 | 7 | 26 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0184 | 7 | 10 | 11 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0035 | 10 | 9 | 13 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0067 | 10 | 10 | 13 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0084 | 10 | 10 | 12 | 0 | 0 | 0 | 1 | 0 | 0 | false |
| holdout_0090 | 10 | 12 | 30 | 0 | 0 | 0 | 1 | 0 | 0 | false |

## Oracle：能否把 residual 和榜首分开、同时不碰 Rank1

| signal | residual save | rank1 kill | net | clean |
|---|---:|---:|---:|---|
| `feature_exact_delta>0` | 1 | 0 | 1 | yes |
| `details_exact_delta>0` | 0 | 0 | 0 | no |
| `details_key_delta>0` | 0 | 0 | 0 | no |
| `uniq_details>0 & head=0` | 0 | 0 | 0 | no |
| `uniq_feature>0 & head=0` | 0 | 0 | 0 | no |
| `title_delta>0` | 0 | 0 | 0 | no |
| `store_consistency_delta>0` | 0 | 0 | 0 | no |
| `brand_consistency_delta>0` | 0 | 0 | 0 | no |
| `same_family & details_delta>0` | 0 | 0 | 0 | no |
| `same_family & store_diff` | 4 | 3 | 1 | no |
| `store_diff` | 44 | 18 | 26 | no |
| `field_tied & details_delta>0` | 0 | 0 | 0 | no |
| `any_provenance_delta>0` | 1 | 0 | 1 | yes |

save = residual 里 target 严格强于当前榜首。kill = 有竞争者的 Rank1（池 ≥2 的 27 条；另外 118 条池=1，不存在 #2）里 #2 用同一规则会赢。

## 结论：**不实现**

问的是：有没有新 catalog signal 能把 target 和它前面的商品稳定分开，同时基本不碰 145 个 Rank1？

**没有可落地的 conditional tie-break。**

1. **Details provenance**  
   出表时的 disclosed slot 几乎全是 feature bullet。51 条 residual 里 `details_exact_delta` / `details_key_delta` / 独占 details 全是 0。拆 `feature_exact` vs `details_exact` 没有上限。唯一非零是 `0122`（rank 6，featΔ=+1 且 detΔ=−1），合并后仍打平；这不是 top-2 tie-break，也不是单向证据。

2. **Parent/variant clone family**  
   目录没有 parent/child 变体图，`parent_asin` 就是商品 ID。用标题/feature Jaccard≥0.5 当 family：residual 32/51 的 family_size=1（和榜首不是同一簇）；只有 10/51 与榜首同簇。同簇时 exact/title/brand 增量仍是 0。family 存在，但 **family 内没有稳定 metadata 能指出 target**。

3. **Store/brand consistency**  
   `store_consistency_delta` 和 `brand_consistency_delta` 全 0：已披露行从不点名 store/brand。`store_diff` 在 residual 里 44/51、在 27 个可竞争 Rank1 里 18 个，只是「两件商品店名不同」，没有方向。`same_family & store_diff` 看起来能救 0059/0104/0125/0129，但会误伤 **0128**（刚被 ambiguity defer 升到 Rank1）以及 0071/0141。不能直接奖 store。

4. **真正的 tie-break 面是 rank2（16 条）**  
   16 条 rank2 的 feat/det/dkey/title/brand/store-consistency **全部是 0**。榜首和 target 在当前证据上不可区分；剩下的是热度 + MiniLM。这和 G1/G2/G3、B/C/D 是同一类 information-timing 问题，不是缺一个 catalog 字段。

正式闸固定为：**Public Hit = 1.000；Holdout Hit ≥ 0.980；Holdout TechnicalScore > 0.898718。** 不改 `rank()`。

