"""Stage2 逐维度判定（AI核心 §5.3.3，D1/D7/D10）——《匹配详细设计》第 4 章 + 供需Schema §6。

- 判定方式由本体 `value_type` 派生（enum 集合 / scalar 等值 / number 容差1.5 / text LLM），无 PARAM_MAP 映射层（D1）
- verdict 四档：matched/partial/missing/unmatched（missing=厂商未声明，独立，D10）
- strictness 接受（D7）：strict → 仅 matched（否则 strict_ok=false，不硬杀，供 Stage4 risk_warning）；best-effort → 全接受计分
- judge_semantic_batch：text/extended 语义需求点一次 LLM 批量判定（含判定缓存 9.2）
"""
from __future__ import annotations

import hashlib
import json
import logging
import re

from app.domains import ontology
from app.llm.client import chat

logger = logging.getLogger("xmsn.match")

MATCHED = "matched"
PARTIAL = "partial"
MISSING = "missing"
UNMATCHED = "unmatched"
_VALID = {MATCHED, PARTIAL, MISSING, UNMATCHED}

_SEMANTIC_PROMPT = """给定客户需求 {demand_json} 与厂商能力 {capability_json}，
对以下语义需求点逐项判定 verdict（matched/partial/missing/unmatched）：
{params}
strict 只输出 JSON：{{"params": [{{"param": "...", "verdict": "...", "note": "..."}}]}}
规则：matched=完全满足；partial=需协商/部分覆盖；missing=厂商未声明；unmatched=明确不满足。
extended（自由需求点）判定：厂商 summary/soft_tags 提及才算 matched。
"""

# 判定缓存（9.2：demand+capability 哈希 → verdict，命中复用，提升稳定性与降本）
_cache: dict[str, list[dict]] = {}


def _norm_slot(sv):
    """兼容三态 dict({value,state}) / 纯值 / excluded 标记({excluded:True,value}) → (value, state)。"""
    if isinstance(sv, dict):
        if "state" in sv:
            return sv.get("value"), sv.get("state")
        if sv.get("excluded"):
            return sv.get("value"), "excluded"
        return sv, "set"
    return sv, "set"


def _judge_enum(d_val, s_val) -> str:
    """enum（多选）：需求值 ⊆ 厂商值 → matched；有交集 → partial；厂商未声明 → missing；无交集 → unmatched。"""
    if s_val in (None, [], ""):
        return MISSING
    s_set = set(s_val) if isinstance(s_val, list) else {str(s_val)}
    d_list = d_val if isinstance(d_val, list) else [d_val]
    miss = [v for v in d_list if str(v) not in s_set]
    if not miss:
        return MATCHED
    return PARTIAL if any(str(v) in s_set for v in d_list) else UNMATCHED


def _judge_scalar(d_val, s_val) -> str:
    """scalar（单值等值）：无 partial 档（§9 决策4）；厂商值兼容数组（如 product_types）。"""
    if s_val in (None, "", []):
        return MISSING
    s_set = set(s_val) if isinstance(s_val, list) else {str(s_val)}
    return MATCHED if str(d_val) in s_set else UNMATCHED


def _judge_number(d_val, s_val, direction: str | None) -> str:
    """number：direction 比较，容差 1.5 → partial（D10）。"""
    if s_val in (None, ""):
        return MISSING
    try:
        s_num = float(s_val)
        d_num = float(d_val)
    except (TypeError, ValueError):
        return MISSING
    if direction == "upper":
        if s_num <= d_num:
            return MATCHED
        return PARTIAL if s_num <= d_num * 1.5 else UNMATCHED
    if direction == "lower":
        if s_num >= d_num:
            return MATCHED
        return PARTIAL if s_num * 1.5 >= d_num else UNMATCHED
    return MATCHED


def _judge_by_value_type(f: dict, d_val, s_val) -> str:
    vt = f.get("value_type")
    if vt == "number":
        return _judge_number(d_val, s_val, f.get("direction"))
    if vt == "enum":
        return _judge_enum(d_val, s_val)
    return _judge_scalar(d_val, s_val)


async def judge_semantic_batch(demand: dict, capability: dict, params: list[str]) -> list[dict]:
    """对单厂商全部语义需求点（text/extended）一次 LLM 批量判定。返回 [{param, verdict, note}]。"""
    if not params:
        return []
    key = hashlib.md5(
        (json.dumps(demand, ensure_ascii=False, sort_keys=True)
         + "|" + json.dumps(capability, ensure_ascii=False, sort_keys=True)).encode()
    ).hexdigest()
    if key in _cache:
        return _cache[key]
    prompt = _SEMANTIC_PROMPT.format(
        demand_json=json.dumps(demand, ensure_ascii=False),
        capability_json=json.dumps(capability, ensure_ascii=False),
        params=json.dumps(params, ensure_ascii=False),
    )
    raw = await chat([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=512)
    data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
    out = [r for r in data.get("params", []) if r.get("verdict") in _VALID]
    _cache[key] = out
    return out


async def judge(demand: dict, capability: dict, product_type: str | None = None) -> tuple[list[dict], bool]:
    """Stage2（AI核心 §5.3.3）：逐需求点判定四档（本体 value_type 派生，D1）。

    返回 (judgements, strict_ok)。judgements 每项 {param, demand_value, supply_value, verdict,
    strictness, kind(rule/semantic), note}；strict_ok = 全部 strict 维度 matched
    （D7：strict 未满足不硬杀，strict_ok=false 供 Stage4 risk_warning）。
    """
    dims = (demand or {}).get("dimensions", {})
    judgements: list[dict] = []
    strict_ok = True
    semantic: list[tuple] = []

    for key, sv in dims.items():
        if not isinstance(sv, dict):
            continue
        v = sv.get("value")
        if v in (None, "", []):
            continue  # 未指定不参与（D10 分母=已指定点数）
        strictness = sv.get("strictness", "best-effort") or "best-effort"
        f = ontology.field_by_key(key, product_type)
        vt = f.get("value_type") if f else "text"
        if vt == "text":
            semantic.append((key, v, strictness))
            continue
        # 厂商侧品类字段为 product_types（复数，历史产品数组）；其余同 key（D1）
        s_val = capability.get("product_types") if key == "product_type" else capability.get(key)
        verdict = _judge_by_value_type(f, v, s_val)
        judgements.append({
            "param": key, "demand_value": v, "supply_value": s_val,
            "verdict": verdict, "strictness": strictness, "kind": "rule", "note": _note(verdict),
        })
        if strictness == "strict" and verdict != MATCHED:
            strict_ok = False

    # extended（D8 自由需求点）→ 语义 LLM
    for e in (demand or {}).get("extended", []) or []:
        if isinstance(e, dict) and e.get("value"):
            semantic.append(("extended", str(e["value"]), e.get("strictness", "best-effort") or "best-effort"))

    if semantic:
        try:
            res = await judge_semantic_batch(demand, capability, [s[0] for s in semantic])
            vmap = {r.get("param"): r for r in res}
            for key, v, strictness in semantic:
                r = vmap.get(key, {})
                verdict = r.get("verdict") if r.get("verdict") in _VALID else MISSING
                judgements.append({
                    "param": key, "demand_value": v, "supply_value": None,
                    "verdict": verdict, "strictness": strictness, "kind": "semantic",
                    "note": r.get("note", _note(verdict)),
                })
                if strictness == "strict" and verdict != MATCHED:
                    strict_ok = False
        except Exception as exc:  # noqa: BLE001 - LLM 不可用 → 语义点 missing 兜底
            logger.warning("semantic judge failed, missing fallback: %s", exc)
            for key, v, strictness in semantic:
                judgements.append({
                    "param": key, "demand_value": v, "supply_value": None,
                    "verdict": MISSING, "strictness": strictness, "kind": "semantic",
                    "note": "LLM 不可用，按未声明处理",
                })
                if strictness == "strict":
                    strict_ok = False
    return judgements, strict_ok


def _note(verdict: str) -> str:
    if verdict == MATCHED:
        return "匹配"
    if verdict == PARTIAL:
        return "部分覆盖，需协商"
    if verdict == MISSING:
        return "厂商未声明"
    return "明确不满足"
