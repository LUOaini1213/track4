"""Turn / disclosure oracle. Does not change rank() or PUBLIC.

At the official scoring recommend, keep going 1–2 more ``other`` turns
(the evaluate loop would have stopped). Measure ΔMRR vs MTTC tax.
Also dump intent-card disclosure order.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluator.local_evaluator import (
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    normalize_recommendations,
)
from starter.shopping_agent.contest_agent import ContestAgent
from starter.shopping_agent.contest_config import PUBLIC
from starter.shopping_agent.contest_index import ContestIndex
from starter.shopping_agent.contest_rank import (
    candidate_pool,
    field_match_scores,
    hard_pool,
    phrase_title_scores,
    popularity_gap,
    rank,
)
from starter.shopping_agent.contest_text import field_key


ROOT = Path(__file__).resolve().parents[1]
N = 200
_HEAD_EPS = 1e-9


def _flat(scores: dict[int, float]) -> bool:
    if not scores:
        return True
    return max(scores.values()) - min(scores.values()) < _HEAD_EPS


def card_slots(card: dict) -> list[str]:
    hard = [str(x) for x in card.get("hard_constraints") or []]
    soft = [str(x) for x in card.get("soft_preferences") or []]
    return list(dict.fromkeys(hard + soft))


def slot_source(text: str) -> str:
    key = field_key(text)
    if key.startswith("color:") or key.startswith("budget around"):
        return "extracted"
    if ":" in key and len(key.split(":", 1)[0]) <= 40:
        return "details"
    return "feature"


def session_delta(
    old_rank: int | None,
    new_rank: int | None,
    rec_turn: int | None,
    extra: int,
) -> dict:
    old_hit = bool(old_rank and old_rank <= 10)
    new_hit = bool(new_rank and new_rank <= 10)
    old_rr = 0.0 if not old_hit else 1.0 / old_rank
    new_rr = 0.0 if not new_hit else 1.0 / new_rank
    rec = rec_turn or 1
    old_turns = 11 if not old_hit else rec
    new_turns = 11 if not new_hit else rec + extra
    d_hit = int(new_hit) - int(old_hit)
    d_rr = new_rr - old_rr
    d_turns = new_turns - old_turns
    contrib = 0.5 * d_hit + 0.3 * d_rr - 0.02 * d_turns
    return {
        "mrr_gain": round(d_rr, 6),
        "mttc_cost": d_turns,
        "hit_delta": d_hit,
        "score_contrib": round(contrib, 6),
        "net_technical_gain": round(contrib / N, 8),
        "profit": contrib > 0,
    }


class SnapAgent(ContestAgent):
    def reset(self, session_id: str, user_profile: dict | None = None) -> None:
        super().reset(session_id, user_profile)
        self.snap: dict | None = None

    def _respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        payload = super()._respond(session_id, user_message, turn, top_k)
        recs = [item["parent_asin"] for item in payload.get("recommendations") or []]
        state = self._state(session_id)
        pool = candidate_pool(self.index, state, self.config)
        filtered = (
            hard_pool(self.index, state, pool, selective=self.config.hard_selective)
            if self.config.hard_filter
            else list(pool)
        )
        working = filtered if (self.config.hard_filter and filtered) else pool
        ordered: list[int] = []
        if recs and working:
            ordered = rank(self.index, state, self.config, list(working), limit=len(working))
        slots = list(state.active)
        field_map = field_match_scores(self.index, working, slots) if working and slots else {}
        phrase_map = phrase_title_scores(self.index, working, slots) if working and slots else {}
        self.snap = {
            "recs": recs,
            "working": list(working),
            "ordered": ordered,
            "slots": [item.text for item in slots],
            "turn": state.turn,
            "field_flat": _flat(field_map),
            "phrase_flat": _flat(phrase_map),
            "pop_gap": popularity_gap(self.index, working) if len(working) >= 2 else 1.0,
            "other_exhausted": "other" in state.exhausted,
        }
        return payload


def target_rank(snap: dict | None, target: str, index: ContestIndex) -> int | None:
    if not snap or not snap.get("ordered"):
        return None
    id_to_idx = {asin: i for i, asin in enumerate(index.ids)}
    tidx = id_to_idx.get(target)
    if tidx is None or tidx not in snap["ordered"]:
        return None
    return snap["ordered"].index(tidx) + 1


def replay(agent: SnapAgent, sample: dict, catalog_ids, categories, products, index: ContestIndex) -> dict:
    session_id = sample["sample_id"]
    agent.reset(session_id, sample.get("user_profile") or {})
    target = str(sample["ground_truth"]["parent_asin"])
    card, behavior = materialize_hidden_fields(sample, products)
    effective = {**sample, "intent_card": card, "behavior": behavior}
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    user_message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)
    card_list = card_slots(card)
    leaks: list[dict] = []
    official = None
    after: list[dict] = []
    last_leak_n = 0

    for turn in range(1, MAX_TURNS + 1):
        before_disclosed = set(disclosed)
        response = agent.respond(session_id, user_message, turn, TOP_K)
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        snap = agent.snap
        pool_n = len(snap["working"]) if snap else 0
        rank_now = target_rank(snap, target, index)
        hit_now = bool(override_applied and ranked and target in ranked)

        if official is None and hit_now:
            remaining = [s for s in card_list if s not in disclosed]
            official = {
                "recommend_turn": turn,
                "slots_at_recommend": list(snap["slots"]) if snap else [],
                "n_slots": len(snap["slots"]) if snap else 0,
                "remaining_card_slots": remaining,
                "remaining_n": len(remaining),
                "current_rank": rank_now,
                "official_top10_rank": ranked.index(target) + 1,
                "pool_before": pool_n,
                "field_flat": snap["field_flat"] if snap else None,
                "phrase_flat": snap["phrase_flat"] if snap else None,
                "pop_gap": round(snap["pop_gap"], 4) if snap else None,
                "other_exhausted": snap["other_exhausted"] if snap else False,
                "last_leak_n": last_leak_n,
            }

        if official is not None and ranked and turn > official["recommend_turn"]:
            remaining = [s for s in card_list if s not in disclosed]
            after.append(
                {
                    "turn": turn,
                    "rank": rank_now,
                    "pool": pool_n,
                    "n_slots": len(snap["slots"]) if snap else 0,
                    "remaining_n": len(remaining),
                    "field_flat": snap["field_flat"] if snap else None,
                }
            )
            if len(after) >= 2:
                break

        if turn == MAX_TURNS:
            break
        override = effective.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            user_message = str(override.get("message", "Actually, please ignore my earlier preference."))
            leaks.append({"turn": turn + 1, "kind": "override", "n": int(bool(new_value)), "texts": [new_value] if new_value else []})
            last_leak_n = int(bool(new_value))
            continue
        ask = response.get("ask_attribute")
        user_message, boundary_used = customer_reply(effective, ask, disclosed, boundary_used)
        leaked = [s for s in card_list if s in disclosed and s not in before_disclosed]
        no_add = "don't have an additional preference" in user_message.lower() or "don't have a preference" in user_message.lower()
        last_leak_n = 0 if no_add else len(leaked)
        leaks.append(
            {
                "turn": turn + 1,
                "kind": "boundary" if "use your judgment" in user_message.lower() else ("empty" if no_add else "other"),
                "n": last_leak_n,
                "texts": leaked,
                "sources": [slot_source(t) for t in leaked],
            }
        )
        if official is not None and len(after) >= 2:
            break

    if official is None and agent.snap and agent.snap.get("recs"):
        remaining = [s for s in card_list if s not in disclosed]
        snap = agent.snap
        official = {
            "recommend_turn": snap["turn"],
            "slots_at_recommend": list(snap["slots"]),
            "n_slots": len(snap["slots"]),
            "remaining_card_slots": remaining,
            "remaining_n": len(remaining),
            "current_rank": target_rank(snap, target, index),
            "official_top10_rank": None,
            "pool_before": len(snap["working"]),
            "field_flat": snap["field_flat"],
            "phrase_flat": snap["phrase_flat"],
            "pop_gap": round(snap["pop_gap"], 4),
            "other_exhausted": snap["other_exhausted"],
            "last_leak_n": last_leak_n,
        }

    rec_turn = official["recommend_turn"] if official else None
    d1 = session_delta(
        official["current_rank"] if official else None,
        after[0]["rank"] if after else None,
        rec_turn,
        1 if after else 0,
    )
    d2 = session_delta(
        official["current_rank"] if official else None,
        after[1]["rank"] if len(after) > 1 else None,
        rec_turn,
        2 if len(after) > 1 else (1 if after else 0),
    )
    positions = []
    for text in (official["slots_at_recommend"] if official else []):
        try:
            positions.append(card_list.index(text) + 1)
        except ValueError:
            positions.append(None)
    return {
        "sample_id": sample["sample_id"],
        "scenario": sample["scenario_type"],
        "card": card_list,
        "card_n": len(card_list),
        "card_sources": [slot_source(t) for t in card_list],
        "leaks": leaks,
        "slot_positions_at_recommend": positions,
        **(official or {"recommend_turn": None, "current_rank": None, "remaining_n": None, "pool_before": None, "n_slots": None}),
        "rank_after_one_more_other": after[0]["rank"] if after else None,
        "rank_after_two_more_other": after[1]["rank"] if len(after) > 1 else None,
        "pool_after_1": after[0]["pool"] if after else None,
        "pool_after_2": after[1]["pool"] if len(after) > 1 else None,
        "slots_after_1": after[0]["n_slots"] if after else None,
        "slots_after_2": after[1]["n_slots"] if len(after) > 1 else None,
        "mrr_gain_1": d1["mrr_gain"],
        "mrr_gain_2": d2["mrr_gain"],
        "mttc_cost_1": d1["mttc_cost"],
        "net_technical_gain_1": d1["net_technical_gain"],
        "score_contrib_1": d1["score_contrib"],
        "profit_1": d1["profit"],
        "score_contrib_2": d2["score_contrib"],
        "profit_2": d2["profit"],
        "hit": bool(official and official.get("current_rank") and official["current_rank"] <= 10),
    }


def bucket(rank: int | None) -> str:
    if rank is None:
        return "miss"
    if rank == 1:
        return "rank1"
    if rank == 2:
        return "rank2"
    if rank <= 5:
        return "rank3-5"
    if rank <= 10:
        return "rank6-10"
    return "miss"


def policy_delta(rows: list[dict], pred) -> dict:
    d_hit = d_rr = d_turns = n_fire = n_profit = n_waste = 0
    fired = []
    for r in rows:
        if not pred(r):
            continue
        n_fire += 1
        fired.append(r["sample_id"])
        old_r = r.get("current_rank")
        new_r = r.get("rank_after_one_more_other")
        extra = 1 if new_r is not None or r.get("pool_after_1") is not None else 0
        if extra == 0:
            continue
        d = session_delta(old_r, new_r, r.get("recommend_turn"), 1)
        d_hit += d["hit_delta"]
        d_rr += d["mrr_gain"]
        d_turns += d["mttc_cost"]
        if d["profit"]:
            n_profit += 1
        elif d["mrr_gain"] <= 0:
            n_waste += 1
    score = (0.5 * d_hit + 0.3 * d_rr - 0.02 * d_turns) / N
    return {
        "fire": n_fire,
        "profit": n_profit,
        "waste": n_waste,
        "d_mrr": round(d_rr / N, 6),
        "d_mttc": round(d_turns / N, 4),
        "d_score": round(score, 6),
        "gate": score > 0,
        "ids": fired,
    }


def main() -> None:
    print("PUBLIC.ambiguity_defer", repr(PUBLIC.ambiguity_defer), flush=True)
    catalog_ids, categories, products = catalog_index(ROOT / "data/catalog.jsonl")
    index = ContestIndex(ROOT / "data/catalog.jsonl")
    samples = load_jsonl(ROOT / "holdout/holdout_200.jsonl")
    agent = SnapAgent(ROOT / "data/catalog.jsonl", config=PUBLIC, index=index)
    rows = []
    for sample in samples:
        row = replay(agent, sample, catalog_ids, categories, products, index)
        row["bucket"] = bucket(row.get("official_top10_rank") or row.get("current_rank"))
        rows.append(row)
        if row["bucket"] != "rank1":
            print(
                json.dumps(
                    {
                        "id": row["sample_id"],
                        "scen": row["scenario"],
                        "t": row.get("recommend_turn"),
                        "slots": row.get("n_slots"),
                        "remain": row.get("remaining_n"),
                        "rank0": row.get("current_rank"),
                        "rank1": row.get("rank_after_one_more_other"),
                        "rank2": row.get("rank_after_two_more_other"),
                        "pool0": row.get("pool_before"),
                        "pool1": row.get("pool_after_1"),
                        "mrr1": row.get("mrr_gain_1"),
                        "net1": row.get("net_technical_gain_1"),
                        "profit": row.get("profit_1"),
                        "flat": row.get("field_flat"),
                        "leak": row.get("last_leak_n"),
                        "pos": row.get("slot_positions_at_recommend"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    by = Counter(r["bucket"] for r in rows)
    print("buckets", dict(by), flush=True)
    profits = [r for r in rows if r.get("profit_1")]
    print("profit_n", len(profits), [r["sample_id"] for r in profits], flush=True)
    print(
        "profit_by_bucket",
        dict(Counter(r["bucket"] for r in profits)),
        flush=True,
    )
    remain_at_rec = Counter((r.get("remaining_n"), r["bucket"]) for r in rows if r.get("recommend_turn"))
    print("remaining_x_bucket", dict(remain_at_rec), flush=True)

    policies = {
        "god_profit (illegal, uses future rank)": lambda r: r.get("profit_1"),
        "remain>0": lambda r: (r.get("remaining_n") or 0) > 0,
        "remain>0 and rank>1": lambda r: (r.get("remaining_n") or 0) > 0 and (r.get("current_rank") or 1) > 1,
        "remain>0 and rank6-10": lambda r: (r.get("remaining_n") or 0) > 0 and r["bucket"] == "rank6-10",
        "n_slots==3 and pool>5 (wider than A)": lambda r: r.get("n_slots") == 3 and (r.get("pool_before") or 0) > 5,
        "n_slots==3 and field_flat and pool 6-20 (A)": lambda r: r.get("n_slots") == 3
        and r.get("field_flat")
        and 6 <= (r.get("pool_before") or 0) <= 20,
        "rank>1 and field_flat and remain>0": lambda r: (r.get("current_rank") or 1) > 1
        and r.get("field_flat")
        and (r.get("remaining_n") or 0) > 0,
        "rank>1 and last_leak==2": lambda r: (r.get("current_rank") or 1) > 1 and r.get("last_leak_n") == 2,
        "last_leak==2 and remain>0": lambda r: r.get("last_leak_n") == 2 and (r.get("remaining_n") or 0) > 0,
    }
    policy_rows = []
    for name, pred in policies.items():
        stats = policy_delta(rows, pred)
        stats["name"] = name
        policy_rows.append(stats)
        print("POLICY", name, {k: stats[k] for k in ("fire", "profit", "waste", "d_mrr", "d_mttc", "d_score", "gate")}, flush=True)

    leak_hist = Counter()
    fourth_source = Counter()
    for r in rows:
        seq = tuple(item["n"] for item in r.get("leaks") or [] if item["kind"] in {"other", "empty", "boundary"})
        leak_hist[seq] += 1
        slots = r.get("slots_at_recommend") or []
        card = r.get("card") or []
        if len(slots) >= 4 and card:
            fourth = slots[3]
            src = slot_source(fourth)
            try:
                pos = card.index(fourth) + 1
            except ValueError:
                pos = None
            fourth_source[(src, pos, r["scenario"])] += 1
    print("leak_n_sequences", leak_hist.most_common(12), flush=True)
    print("fourth_slot", fourth_source.most_common(12), flush=True)

    residual = [r for r in rows if r["bucket"] in {"rank2", "rank3-5", "rank6-10"}]
    md = [
        "# Turn / disclosure oracle (holdout, PUBLIC=`ambiguity_defer=a`)",
        "",
        "不改 `rank()`。官方计分出表后**继续 1–2 轮 `other`**（评估器本来会停），看 ΔMRR 能否付 MTTC 税。",
        f"`net_technical_gain_1` = 单条对总分的贡献 `(0.5ΔHit + 0.3ΔRR − 0.02Δturns)/200`。闸：Public Hit=1.000 / Holdout Hit≥0.980 / score>0.898718。",
        "",
        f"buckets `{dict(by)}`。强制 +1 other 赚钱的会话：**{len(profits)}**。",
        "",
        "## Simulator disclosure",
        "",
        "Intent card 顺序固定：`features+details` 去重后 `hard=[:2]`，`soft=[2:4]`（不够则复制 hard[:1]）。",
        "`other` 按这个顺序取**尚未进入 `disclosed` 的最多 2 条**。Buying 开场泄 hard[0]；Browsing 开场 0 条；空则 `no additional preference`。",
        "",
        "### 每次 other 泄出条数（开场之后）",
        "",
    ]
    md.append("| 泄出序列 (每轮 n) | n |")
    md.append("|---|---:|")
    for seq, n in leak_hist.most_common():
        md.append(f"| `{seq}` | {n} |")
    md.append("")
    md.append("### 第 4 个已披露槽来自哪")
    md.append("")
    md.append("| source | card 位 | scenario | n |")
    md.append("|---|---:|---|---:|")
    for (src, pos, scen), n in sorted(fourth_source.items(), key=lambda x: -x[1]):
        md.append(f"| {src} | {pos} | {scen} | {n} |")
    md.append("")
    md.append("## Residual：多问一轮是否赚钱")
    md.append("")
    md.append("| sample | scen | t | slots | remain | rank0 | rank+1 | rank+2 | pool0 | pool+1 | ΔRR | net | profit | field_flat |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for r in sorted(residual, key=lambda x: (-(x.get("score_contrib_1") or 0), x["sample_id"])):
        md.append(
            f"| {r['sample_id']} | {r['scenario']} | {r.get('recommend_turn')} | {r.get('n_slots')} | "
            f"{r.get('remaining_n')} | {r.get('current_rank')} | {r.get('rank_after_one_more_other')} | "
            f"{r.get('rank_after_two_more_other')} | {r.get('pool_before')} | {r.get('pool_after_1')} | "
            f"{r.get('mrr_gain_1')} | {r.get('net_technical_gain_1')} | {str(r.get('profit_1')).lower()} | "
            f"{str(r.get('field_flat')).lower()} |"
        )
    md.append("")
    md.append("## 赚钱会话在问之前的可观测结构")
    md.append("")
    if profits:
        md.append("| sample | bucket | slots | pool | remain | last_leak | field_flat | phrase_flat | pop_gap | scen |")
        md.append("|---|---|---:|---:|---:|---:|---|---|---:|---|")
        for r in profits:
            md.append(
                f"| {r['sample_id']} | {r['bucket']} | {r.get('n_slots')} | {r.get('pool_before')} | "
                f"{r.get('remaining_n')} | {r.get('last_leak_n')} | {str(r.get('field_flat')).lower()} | "
                f"{str(r.get('phrase_flat')).lower()} | {r.get('pop_gap')} | {r['scenario']} |"
            )
    else:
        md.append("没有 session 在 +1 other 后 TechnicalScore 贡献为正。")
    md.append("")
    md.append("## 合法 / 非法 policy 上界（全 200 条，+1 other）")
    md.append("")
    md.append("| policy | fire | profit | waste | ΔMRR | ΔMTTC | ΔScore | 过闸? |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for stats in policy_rows:
        md.append(
            f"| {stats['name']} | {stats['fire']} | {stats['profit']} | {stats['waste']} | "
            f"{stats['d_mrr']} | {stats['d_mttc']} | {stats['d_score']} | "
            f"{'yes' if stats['d_score'] > 0 else 'no'} |"
        )
    md.append("")
    md.append("`remain>0 and rank>1` 偷看 target 名次，不能做 PUBLIC。`god_profit` 偷看未来名次。")
    md.append("A 已经在跑，表里那一行只是对照，不是新刀。")
    md.append("")
    (ROOT / "report/disclosure.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    slim = []
    for r in rows:
        slim.append(
            {k: r[k] for k in (
                "sample_id", "scenario", "recommend_turn", "n_slots", "remaining_n",
                "current_rank", "rank_after_one_more_other", "rank_after_two_more_other",
                "pool_before", "pool_after_1", "pool_after_2", "mrr_gain_1", "mrr_gain_2",
                "mttc_cost_1", "net_technical_gain_1", "profit_1", "bucket", "field_flat",
                "phrase_flat", "last_leak_n", "slot_positions_at_recommend", "card_sources",
                "card_n",
            ) if k in r}
        )
    (ROOT / "report/disclosure_rows.json").write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    print("wrote report/disclosure.md", flush=True)


if __name__ == "__main__":
    main()
