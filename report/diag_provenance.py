"""Oracle diagnostic: catalog provenance vs current PUBLIC ranking.

Does not change rank(). Replays holdout, snapshots the scoring recommend
turn, and asks whether feature/details/clone/store/brand can separate
target from items ranked above it without dethroning Rank1.
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
    _DENSE_GENERIC,
    _TITLE_SKIP,
    candidate_pool,
    hard_pool,
    rank,
)
from starter.shopping_agent.contest_text import field_key, terms


ROOT = Path(__file__).resolve().parents[1]
SKIP = _TITLE_SKIP | _DENSE_GENERIC
CHROME_DETAIL_KEYS = {
    "date first available",
    "is discontinued by manufacturer",
    "package dimensions",
    "product dimensions",
    "item weight",
    "package weight",
    "item package dimensions l x w x h",
    "best sellers rank",
    "batteries",
}


class SnapAgent(ContestAgent):
    def reset(self, session_id: str, user_profile: dict | None = None) -> None:
        super().reset(session_id, user_profile)
        self.snap: dict | None = None

    def _respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        payload = super()._respond(session_id, user_message, turn, top_k)
        recs = [item["parent_asin"] for item in payload.get("recommendations") or []]
        if not recs:
            return payload
        state = self._state(session_id)
        pool = candidate_pool(self.index, state, self.config)
        filtered = (
            hard_pool(self.index, state, pool, selective=self.config.hard_selective)
            if self.config.hard_filter
            else list(pool)
        )
        working = filtered if (self.config.hard_filter and filtered) else pool
        ordered = rank(self.index, state, self.config, list(working), limit=len(working))
        self.snap = {
            "working": list(working),
            "ordered": ordered,
            "recs": recs,
            "slots": [item.text for item in state.active],
            "turn": state.turn,
        }
        return payload


def feature_lines(product: dict) -> set[str]:
    out: set[str] = set()
    for item in product.get("features") or []:
        key = field_key(item)
        if key:
            out.add(key)
    return out


def details_pairs(product: dict) -> list[tuple[str, str]]:
    details = product.get("details")
    if not isinstance(details, dict):
        return []
    pairs: list[tuple[str, str]] = []
    for key, value in details.items():
        if value in (None, "", []):
            continue
        dkey = field_key(key)
        line = field_key(f"{key}: {value}")
        if dkey and line:
            pairs.append((dkey, line))
    return pairs


def details_lines(product: dict) -> set[str]:
    return {line for _key, line in details_pairs(product)}


def details_keys(product: dict) -> set[str]:
    return {key for key, _line in details_pairs(product)}


def brand_text(product: dict) -> str:
    for key, line in details_pairs(product):
        if key in {"brand", "brand name", "manufacturer"}:
            value = line.split(":", 1)[-1].strip()
            if value:
                return value
    return field_key(product.get("store") or "")


def store_text(product: dict) -> str:
    return field_key(product.get("store") or "")


def title_bag(title: str) -> set[str]:
    return {
        token
        for token in terms(title)
        if token not in SKIP and len(token) >= 3 and not token.isdigit()
    }


def slot_keys(slots: list[str]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for text in slots:
        if "budget" in text.lower():
            continue
        key = field_key(text)
        if len(key) < 8 or key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def slot_detail_key(slot: str) -> str | None:
    if ":" not in slot:
        return None
    key = field_key(slot.split(":", 1)[0])
    if not key or key in CHROME_DETAIL_KEYS:
        return None
    return key


def counts(product: dict, keys: list[str]) -> dict[str, int]:
    feats = feature_lines(product)
    dlines = details_lines(product)
    dkeys = details_keys(product)
    title = field_key(product.get("title") or "")
    store = store_text(product)
    brand = brand_text(product)
    feature = details = dkey = title_n = store_n = brand_n = 0
    for key in keys:
        if key in feats:
            feature += 1
        if key in dlines:
            details += 1
        sk = slot_detail_key(key)
        if sk and sk in dkeys:
            dkey += 1
        if key in title:
            title_n += 1
        if store and (store in key or key in store):
            store_n += 1
        if brand and (brand in key or key in brand):
            brand_n += 1
    return {
        "feature": feature,
        "details": details,
        "dkey": dkey,
        "title": title_n,
        "store": store_n,
        "brand": brand_n,
    }


def unique_hits(pool_products: list[dict], keys: list[str], kind: str) -> list[set[str]]:
    """Per-product set of slot keys that no other pool item matches for this kind."""

    hits: list[set[str]] = []
    df: dict[str, int] = defaultdict(int)
    for product in pool_products:
        if kind == "feature":
            bag = feature_lines(product)
        elif kind == "details":
            bag = details_lines(product)
        else:
            bag = details_keys(product)
        owned: set[str] = set()
        for key in keys:
            probe = slot_detail_key(key) if kind == "dkey" else key
            if probe and probe in bag:
                owned.add(probe)
        hits.append(owned)
        for item in owned:
            df[item] += 1
    return [{item for item in owned if df[item] == 1} for owned in hits]


def title_jaccard(left: str, right: str) -> float:
    a, b = title_bag(left), title_bag(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def family_size(target: dict, pool_products: list[dict], threshold: float = 0.5) -> int:
    t_title = str(target.get("title") or "")
    t_feat = feature_lines(target)
    size = 0
    for product in pool_products:
        same_title = title_jaccard(t_title, str(product.get("title") or "")) >= threshold
        feats = feature_lines(product)
        same_feat = bool(t_feat and feats and len(t_feat & feats) / len(t_feat | feats) >= threshold)
        if same_title or same_feat:
            size += 1
    return size


def replay(agent: SnapAgent, sample: dict, catalog_ids: set[str], categories: dict, products: dict) -> dict:
    session_id = sample["sample_id"]
    agent.reset(session_id, sample.get("user_profile") or {})
    target = str(sample["ground_truth"]["parent_asin"])
    card, behavior = materialize_hidden_fields(sample, products)
    effective = {**sample, "intent_card": card, "behavior": behavior}
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    user_message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)
    best_rank = None
    hit_turn = None
    snap = None
    for turn in range(1, MAX_TURNS + 1):
        response = agent.respond(session_id, user_message, turn, TOP_K)
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        if override_applied and target in ranked:
            best_rank = ranked.index(target) + 1
            hit_turn = turn
            snap = agent.snap
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
        else:
            user_message, boundary_used = customer_reply(
                effective, response.get("ask_attribute"), disclosed, boundary_used
            )
    return {
        "sample_id": sample["sample_id"],
        "scenario": sample["scenario_type"],
        "target": target,
        "best_rank": best_rank,
        "hit_turn": hit_turn,
        "snap": snap,
    }


def analyze_row(row: dict, products: dict, index: ContestIndex) -> dict | None:
    snap = row["snap"]
    if not snap:
        return None
    target = row["target"]
    id_to_idx = {asin: i for i, asin in enumerate(index.ids)}
    tidx = id_to_idx.get(target)
    if tidx is None:
        return None
    working = snap["working"]
    ordered = snap["ordered"]
    if tidx not in ordered or len(ordered) < 2:
        return None
    final_rank = ordered.index(tidx) + 1
    pop_sorted = sorted(working, key=lambda i: (-index.popularity(i), index.ids[i]))
    pop_rank = 1 + pop_sorted.index(tidx)
    keys = slot_keys(snap["slots"])
    pool_products = [products[index.ids[i]] for i in working]
    tprod = products[target]
    t_counts = counts(tprod, keys)
    other_idx = ordered[1] if final_rank == 1 else ordered[0]
    head_idx = other_idx
    head_prod = products[index.ids[head_idx]]
    h_counts = counts(head_prod, keys)
    uniq_feat = unique_hits(pool_products, keys, "feature")
    uniq_det = unique_hits(pool_products, keys, "details")
    loc = {index.ids[i]: n for n, i in enumerate(working)}
    t_u_feat = uniq_feat[loc[target]]
    t_u_det = uniq_det[loc[target]]
    h_u_feat = uniq_feat[loc[index.ids[head_idx]]] if head_idx is not None else set()
    h_u_det = uniq_det[loc[index.ids[head_idx]]] if head_idx is not None else set()
    fam = family_size(tprod, pool_products)
    same_family_head = False
    if head_prod is not None:
        same_family_head = (
            title_jaccard(str(tprod.get("title") or ""), str(head_prod.get("title") or "")) >= 0.5
            or (
                bool(feature_lines(tprod) and feature_lines(head_prod))
                and len(feature_lines(tprod) & feature_lines(head_prod))
                / len(feature_lines(tprod) | feature_lines(head_prod))
                >= 0.5
            )
        )
    return {
        "sample": row["sample_id"],
        "scen": row["scenario"],
        "official_rank": row["best_rank"],
        "final_rank": final_rank,
        "pop_rank": pop_rank,
        "pool_size": len(working),
        "n_slots": len(snap["slots"]),
        "feature_exact_delta": t_counts["feature"] - h_counts["feature"],
        "details_exact_delta": t_counts["details"] - h_counts["details"],
        "details_key_delta": t_counts["dkey"] - h_counts["dkey"],
        "title_delta": t_counts["title"] - h_counts["title"],
        "store_consistency_delta": t_counts["store"] - h_counts["store"],
        "brand_consistency_delta": t_counts["brand"] - h_counts["brand"],
        "clone_family_size": fam,
        "same_family_head": same_family_head,
        "uniq_feature": len(t_u_feat),
        "uniq_details": len(t_u_det),
        "head_uniq_feature": len(h_u_feat),
        "head_uniq_details": len(h_u_det),
        "t_feature": t_counts["feature"],
        "h_feature": h_counts["feature"],
        "t_details": t_counts["details"],
        "h_details": h_counts["details"],
        "head_asin": index.ids[head_idx] if head_idx is not None else None,
        "head_store": store_text(head_prod) if head_prod is not None else "",
        "t_store": store_text(tprod),
        "store_diff": bool(head_prod is not None and store_text(tprod) and store_text(tprod) != store_text(head_prod)),
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


def oracle_stats(rows: list[dict]) -> dict:
    residual = [r for r in rows if r["official_rank"] and r["official_rank"] > 1]
    rank1 = [r for r in rows if r["official_rank"] == 1]
    signals = [
        ("feature_exact_delta>0", lambda r: r["feature_exact_delta"] > 0, lambda r: r["feature_exact_delta"] < 0),
        ("details_exact_delta>0", lambda r: r["details_exact_delta"] > 0, lambda r: r["details_exact_delta"] < 0),
        ("details_key_delta>0", lambda r: r["details_key_delta"] > 0, lambda r: r["details_key_delta"] < 0),
        ("uniq_details>0 & head=0", lambda r: r["uniq_details"] > 0 and r["head_uniq_details"] == 0, lambda r: r["head_uniq_details"] > 0 and r["uniq_details"] == 0),
        ("uniq_feature>0 & head=0", lambda r: r["uniq_feature"] > 0 and r["head_uniq_feature"] == 0, lambda r: r["head_uniq_feature"] > 0 and r["uniq_feature"] == 0),
        ("title_delta>0", lambda r: r["title_delta"] > 0, lambda r: r["title_delta"] < 0),
        ("store_consistency_delta>0", lambda r: r["store_consistency_delta"] > 0, lambda r: r["store_consistency_delta"] < 0),
        ("brand_consistency_delta>0", lambda r: r["brand_consistency_delta"] > 0, lambda r: r["brand_consistency_delta"] < 0),
        ("same_family & details_delta>0", lambda r: r["same_family_head"] and r["details_exact_delta"] > 0, lambda r: r["same_family_head"] and r["details_exact_delta"] < 0),
        ("same_family & store_diff", lambda r: r["same_family_head"] and r["store_diff"], lambda r: r["same_family_head"] and r["store_diff"]),
        ("store_diff", lambda r: r["store_diff"], lambda r: r["store_diff"]),
        ("field_tied & details_delta>0", lambda r: r["feature_exact_delta"] == 0 and r["details_exact_delta"] > 0, lambda r: r["feature_exact_delta"] == 0 and r["details_exact_delta"] < 0),
        ("any_provenance_delta>0", lambda r: max(r["feature_exact_delta"], r["details_exact_delta"], r["details_key_delta"], r["title_delta"], r["store_consistency_delta"], r["brand_consistency_delta"]) > 0, lambda r: min(r["feature_exact_delta"], r["details_exact_delta"], r["details_key_delta"], r["title_delta"], r["store_consistency_delta"], r["brand_consistency_delta"]) < 0),
    ]
    out = []
    for name, save_fn, kill_fn in signals:
        save = [r["sample"] for r in residual if save_fn(r)]
        kill = [r["sample"] for r in rank1 if kill_fn(r)]
        out.append(
            {
                "signal": name,
                "save_n": len(save),
                "kill_n": len(kill),
                "save": save,
                "kill": kill,
                "net": len(save) - len(kill),
                "clean": len(save) > 0 and len(kill) == 0,
            }
        )
    return {"residual": len(residual), "rank1": len(rank1), "signals": out}


def main() -> None:
    catalog_ids, categories, products = catalog_index(ROOT / "data/catalog.jsonl")
    index = ContestIndex(ROOT / "data/catalog.jsonl")
    samples = load_jsonl(ROOT / "holdout/holdout_200.jsonl")
    agent = SnapAgent(ROOT / "data/catalog.jsonl", config=PUBLIC, index=index)
    print("PUBLIC.ambiguity_defer", repr(PUBLIC.ambiguity_defer), flush=True)
    rows: list[dict] = []
    for sample in samples:
        raw = replay(agent, sample, catalog_ids, categories, products)
        analyzed = analyze_row(raw, products, index)
        if analyzed is None:
            continue
        analyzed["bucket"] = bucket(analyzed["official_rank"])
        rows.append(analyzed)
        if analyzed["bucket"] != "rank1":
            print(json.dumps(analyzed, ensure_ascii=False), flush=True)

    by = Counter(r["bucket"] for r in rows)
    print("buckets", dict(by), flush=True)
    residual = [r for r in rows if r["bucket"] in {"rank2", "rank3-5", "rank6-10"}]
    print("same_family_head residual", sum(1 for r in residual if r["same_family_head"]), "/", len(residual), flush=True)
    print("clone_family_size residual", Counter(r["clone_family_size"] for r in residual), flush=True)
    stats = oracle_stats(rows)
    for item in stats["signals"]:
        print(
            "ORACLE",
            item["signal"],
            "save",
            item["save_n"],
            "kill",
            item["kill_n"],
            "net",
            item["net"],
            "clean",
            item["clean"],
            "save_ids",
            item["save"],
            "kill_ids",
            item["kill"][:12],
            flush=True,
        )

    md = ["# Catalog provenance oracle (holdout, PUBLIC=`ambiguity_defer=a`)", ""]
    md.append("只统计，不改 `rank()`。快照是 **官方计分那一轮出表** 的 hard pool。")
    md.append("Residual 的 delta 是 `target − 当前榜首`；Rank1 对照是 `target − #2`。")
    md.append("")
    md.append(f"覆盖 {len(rows)} / 200。buckets: `{dict(by)}`。")
    md.append("")
    md.append("## Residual 表（rank 2 / 3–5 / 6–10）")
    md.append("")
    md.append(
        "| sample | rank | pop | pool | featΔ | detΔ | dkeyΔ | fam | brandΔ | storeΔ | same_fam |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in sorted(residual, key=lambda x: (x["official_rank"] or 99, x["sample"])):
        md.append(
            f"| {r['sample']} | {r['official_rank']} | {r['pop_rank']} | {r['pool_size']} | "
            f"{r['feature_exact_delta']} | {r['details_exact_delta']} | {r['details_key_delta']} | "
            f"{r['clone_family_size']} | {r['brand_consistency_delta']} | {r['store_consistency_delta']} | "
            f"{str(r['same_family_head']).lower()} |"
        )
    md.append("")
    md.append("## Oracle：能否把 residual 和榜首分开、同时不碰 Rank1")
    md.append("")
    md.append("| signal | residual save | rank1 kill | net | clean |")
    md.append("|---|---:|---:|---:|---|")
    for item in stats["signals"]:
        md.append(
            f"| `{item['signal']}` | {item['save_n']} | {item['kill_n']} | {item['net']} | "
            f"{'yes' if item['clean'] else 'no'} |"
        )
    md.append("")
    md.append("save = residual 里 target 严格强于当前榜首。kill = Rank1 里 #2 用同一规则会赢。")
    md.append("")
    (ROOT / "report/provenance.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (ROOT / "report/provenance_rows.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print("wrote report/provenance.md", flush=True)


if __name__ == "__main__":
    main()
