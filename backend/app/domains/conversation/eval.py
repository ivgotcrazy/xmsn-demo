"""Agent 评估体系（T3.8）——《代理详细设计》第 7 章。

六维指标：
- slot_extraction_f1：正确性（per-field F1）
- completeness_score：完整度（关键字段覆盖率）
- guidance_quality：引导（轮数/重复询问/主动确认提示）
- e2e_top1_hit：端到端（档案→匹配 Top-1 命中；M4 匹配引擎后启用）
- latency_and_cost：体验（LLM 调用次数/平均耗时）
- stability_metrics：稳定性（槽位一致率/分数标准差/Top-5 Jaccard/排序位移）

run_case：离线模拟对话编排（选项直写/LLM 解析/merge，不依赖 DB/API），
提取最终槽位作为 pred，与 gold_slots 对比。
"""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time

from app.domains.conversation import agent

logger = logging.getLogger("xmsn.eval")


async def run_case(dialog: list[dict]) -> dict:
    """逐条 user 消息跑编排（RAG 关闭），返回最终纯值槽位。"""
    state: dict = {}
    for turn in dialog:
        if turn.get("role") != "user":
            continue
        text = (turn.get("content") or "").strip()
        if not text:
            continue
        intent = agent.route_intent(text, None, state)
        if intent in ("done", "confirm"):
            break
        pending = state.get("_pending") or {}
        if pending.get("key") and pending.get("options") and text in pending.get("options", []):
            state = agent.write_option(state, pending["key"], text)
        else:
            parsed = await agent.extract_slots(state, text, db=None)
            state = agent.merge_slot(state, parsed.get("slot_delta", {}), parsed.get("extended", []))
        _next_key, _q, opts, _otype = agent.decide_question(state)
        state["_pending"] = {"key": _next_key, "options": opts} if _next_key else {}
    return _pure_slots(state)


def _pure_slots(state: dict) -> dict:
    """三态槽位 → 纯值 dict（仅 SET 且有值）。"""
    out: dict = {}
    for k, sv in state.items():
        if k.startswith("_") or not isinstance(sv, dict) or sv.get("state") != "set":
            continue
        v = sv.get("value")
        if v is not None and v != []:
            out[k] = v
    return out


def slot_extraction_f1(gold: dict, pred: dict) -> float:
    """per-field F1：多选按集合精确率/召回率，单选按相等。字段级平均。"""
    keys = set(gold) | set(pred)
    if not keys:
        return 1.0
    f1s = []
    for k in keys:
        g, p = gold.get(k), pred.get(k)
        if isinstance(g, list) or isinstance(p, list):
            gs, ps = set(g or []), set(p or [])
            inter = len(gs & ps)
            prec = inter / len(ps) if ps else (1.0 if not gs else 0.0)
            rec = inter / len(gs) if gs else (1.0 if not ps else 0.0)
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else (1.0 if gs == ps else 0.0)
        else:
            f1 = 1.0 if g == p else 0.0
        f1s.append(f1)
    return round(statistics.mean(f1s), 4)


def completeness_score(gold: dict, pred: dict) -> float:
    """关键字段覆盖率：gold 已提及字段中 pred 成功提取的比例。"""
    if not gold:
        return 1.0
    covered = 0
    for k, g in gold.items():
        p = pred.get(k)
        if isinstance(g, list):
            if g and p and set(g) & set(p):
                covered += 1
            elif not g:
                covered += 1
        elif g is not None and p is not None and g == p:
            covered += 1
    return round(covered / len(gold), 4)


def guidance_quality(dialog: list[dict]) -> dict:
    """引导：总轮数、自由文本轮数、是否出现主动确认提示。"""
    user_msgs = [t for t in dialog if t.get("role") == "user"]
    return {
        "turns": len(user_msgs),
        "free_text_turns": len([t for t in user_msgs if "。确认完成" in str(t.get("content", "")) or "确认完成" in str(t.get("content", ""))]),
    }


def e2e_top1_hit(gold_vendor_id, matches) -> float | None:
    """端到端 Top-1 命中（M4 匹配引擎后启用）；无匹配数据返回 None。"""
    if not matches:
        return None
    return 1.0 if matches[0].get("vendor_id") == gold_vendor_id else 0.0


def latency_and_cost(timings: list[float]) -> dict:
    """体验：LLM 调用次数 / 平均耗时 / 总耗时。"""
    if not timings:
        return {"llm_calls": 0, "avg_llm_s": 0.0, "total_s": 0.0}
    return {
        "llm_calls": len(timings),
        "avg_llm_s": round(statistics.mean(timings), 3),
        "total_s": round(sum(timings), 3),
    }


def stability_metrics(runs: list[dict]) -> dict:
    """稳定性（LLD 7.2）：按 case 分组算槽位一致率再平均；分数标准差 / Top-5 Jaccard。"""
    n = len(runs)
    if n < 2:
        return {"n": n, "slot_consistency": None, "score_std": None,
                "top5_jaccard": None, "rank_shift": None}
    by_case: dict[str, list[dict]] = {}
    for r in runs:
        by_case.setdefault(r.get("case_id", "?"), []).append(r)
    cons = []
    for _cid, rs in by_case.items():
        if len(rs) < 2:
            continue
        keys = sorted({k for r in rs for k in r.get("slots", {})})
        per_key = []
        for k in keys:
            vals = [json.dumps(r.get("slots", {}).get(k), ensure_ascii=False, sort_keys=True) for r in rs]
            majority = max(set(vals), key=vals.count)
            per_key.append(sum(1 for v in vals if v == majority) / len(vals))
        cons.append(statistics.mean(per_key) if per_key else 1.0)
    slot_consistency = round(statistics.mean(cons), 4) if cons else None
    scores = [r.get("match_score") for r in runs if r.get("match_score") is not None]
    score_std = round(statistics.pstdev(scores), 4) if len(scores) >= 2 else None
    top_sets = [set(r.get("top5", [])) for r in runs]
    jac = (len(top_sets[0] & top_sets[1]) / len(top_sets[0] | top_sets[1])
           if top_sets and top_sets[0] | top_sets[1] else 1.0)
    return {
        "n": n,
        "slot_consistency": slot_consistency,
        "score_std": score_std,
        "top5_jaccard": round(jac, 4),
        "rank_shift": None,
    }


async def evaluate(cases: list[dict], stability_n: int = 0, timing: bool = True) -> dict:
    """跑黄金集：每 case 六维指标 + 汇总；stability_n>0 时对前 2 条跑稳定性。"""
    reports = []
    timings: list[float] = []
    for case in cases:
        t0 = time.perf_counter()
        pred = await run_case(case.get("dialog", []))
        dt = time.perf_counter() - t0
        timings.append(dt)
        gold = case.get("gold_slots", {})
        report = {
            "case_id": case.get("case_id"),
            "category": case.get("category"),
            "slot_f1": slot_extraction_f1(gold, pred),
            "completeness": completeness_score(gold, pred),
            "guidance": guidance_quality(case.get("dialog", [])),
            "e2e_top1": e2e_top1_hit(case.get("gold_vendor_id"), case.get("matches", [])),
            "pred_slots": pred,
        }
        reports.append(report)

    stability = None
    if stability_n > 0:
        sample = cases[:2]
        runs = []
        for case in sample:
            for _ in range(stability_n):
                pred = await run_case(case.get("dialog", []))
                runs.append({"case_id": case.get("case_id"), "slots": pred,
                             "match_score": None, "top5": []})
        stability = stability_metrics(runs)

    return {
        "total_cases": len(cases),
        "avg_slot_f1": round(statistics.mean([r["slot_f1"] for r in reports]), 4) if reports else None,
        "avg_completeness": round(statistics.mean([r["completeness"] for r in reports]), 4) if reports else None,
        "latency_cost": latency_and_cost(timings),
        "stability": stability,
        "reports": reports,
    }
