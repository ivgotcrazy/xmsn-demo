"""通道B 参数判定（T4.2）——《匹配详细设计》第 4 章。

- PARAM_MAP：规范参数 ↔ 需求字段 ↔ 厂商能力字段（4.1）
- judge_rule：确定性判定（枚举集合 / 数值比较，4.2），不走 LLM
- judge_semantic_batch：语义参数一次 LLM 批量判定（4.3），含判定缓存（9.2）
- judge：对单厂商产出已指定参数的 ParamJudgement 列表 + match_source
- 分母=已指定（4.4）；排除项硬过滤（4.5）由 service 执行
"""
from __future__ import annotations

import hashlib
import json
import logging
import re

from app.llm.client import chat

logger = logging.getLogger("xmsn.match")

MATCHED = "matched"
PARTIAL = "partial"
MISSING = "missing"
UNMATCHED = "unmatched"
_VALID = {MATCHED, PARTIAL, MISSING, UNMATCHED}

# (规范参数, 权重, 需求字段, 厂商能力字段, kind, critical)
PARAM_MAP: list[tuple[str, float, str | None, str | None, str, bool]] = [
    ("product_type", 2.0, "product_type", "product_types", "semantic", True),
    ("os_support", 1.5, "os", "os_support", "rule", True),
    ("certifications", 1.5, "certifications", "certifications", "rule", True),
    ("application_scenes", 1.0, "application_scenario", "application_scenarios", "semantic", False),
    ("interfaces", 1.0, "interfaces", "interfaces", "rule", False),
    ("min_order_qty", 1.0, "moq", "moq", "rule", False),
    ("lead_time_days", 0.5, "lead_time_days", "lead_time_days", "rule", False),
    ("customization", 0.5, "customization_needs", None, "semantic", False),
]

CRITICAL = {"product_type", "os_support", "certifications"}

_SEMANTIC_PROMPT = """给定买家需求 {demand_json} 与厂商能力 {capability_json}，
对以下语义参数逐项判定 verdict（matched/partial/missing/unmatched）：
{params}
strict 只输出 JSON：{{"params": [{{"param": "...", "verdict": "...", "note": "..."}}]}}
规则：matched=完全满足；partial=需协商/部分覆盖；missing=厂商未声明；unmatched=明确不满足。
关键参数（product_type）unmatched 时 note 需显式标注 critical。
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


def _demand_value(demand: dict, d_field: str | None):
    """需求字段已指定值；未指定/排除/通配 → None。"""
    if not d_field:
        return None
    sv = demand.get(d_field)
    if sv is None:
        return None
    v, st = _norm_slot(sv)
    if st != "set":
        return None
    if v in (None, "", []):
        return None
    return v


def excluded_values(demand: dict, d_field: str | None) -> list:
    """排除项的排除值（负向硬过滤用；旧数据无值时返回 []）。"""
    if not d_field:
        return []
    sv = demand.get(d_field)
    if sv is None:
        return []
    v, st = _norm_slot(sv)
    if st != "excluded":
        return []
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def judge_rule(param: str, d_val, s_val) -> str:
    """规则判定（4.2）：枚举集合需求值⊆厂商值；数值需求≤厂商（≤1.25 为 partial）。"""
    if s_val is None or s_val == [] or s_val == {} or s_val == "":
        return MISSING
    if isinstance(d_val, list):
        s_set = set(s_val) if isinstance(s_val, list) else {str(s_val)}
        missing = [v for v in d_val if v not in s_set]
        if not missing:
            return MATCHED
        return PARTIAL if any(v in s_set for v in d_val) else UNMATCHED
    if isinstance(d_val, (int, float)):
        try:
            s_num = float(s_val)
        except (TypeError, ValueError):
            return MISSING
        # 数值：厂商值满足需求值方向（moq/交期均适用）：
        # s<=d → 厂商优于/等同需求；s<=d*1.5 → 略超可协商（UC-M2 交期 30 vs 45 = partial）；否则 unmatched
        if s_num <= d_val:
            return MATCHED
        return PARTIAL if s_num <= d_val * 1.5 else UNMATCHED
    return MATCHED if str(d_val) == str(s_val) else UNMATCHED


async def judge_semantic_batch(demand: dict, capability: dict, params: list) -> list[dict]:
    """对单厂商全部语义参数一次 LLM 批量判定（4.3）。返回 [{param, verdict, note}]。"""
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
        params=json.dumps([p[0] for p in params], ensure_ascii=False),
    )
    raw = await chat([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=512)
    data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
    out = [r for r in data.get("params", []) if r.get("verdict") in _VALID]
    _cache[key] = out
    return out


async def judge(demand: dict, capability: dict) -> tuple[list[dict], str]:
    """对单厂商判定全部已指定参数 → (judgements, match_source)。

    - RULE 参数确定性判定；SEMANTIC 参数 LLM 批量（失败 → 全部 missing，source='rule' 不虚报）。
    """
    judgements: list[dict] = []
    semantic: list[tuple] = []

    for param, weight, d_field, s_field, kind, critical in PARAM_MAP:
        d_val = _demand_value(demand, d_field)
        if d_val is None:
            continue  # 未指定：不进分母
        s_val = capability.get(s_field) if s_field else (capability.get("summary_text") or "")
        if kind == "rule":
            verdict = judge_rule(param, d_val, s_val)
            judgements.append({
                "param": param, "demand_value": d_val, "supply_value": s_val,
                "verdict": verdict, "weight": weight, "kind": kind, "note": _note(param, verdict),
            })
        else:
            semantic.append((param, weight, d_field, s_field, critical))

    if semantic:
        try:
            res = await judge_semantic_batch(demand, capability, semantic)
            vmap = {r.get("param"): r for r in res}
            for param, weight, d_field, s_field, critical in semantic:
                r = vmap.get(param, {})
                verdict = r.get("verdict") if r.get("verdict") in _VALID else MISSING
                judgements.append({
                    "param": param, "demand_value": _demand_value(demand, d_field),
                    "supply_value": capability.get(s_field) if s_field else None,
                    "verdict": verdict, "weight": weight, "kind": "semantic",
                    "note": r.get("note", _note(param, verdict)),
                })
        except Exception as exc:  # noqa: BLE001 - LLM 不可用 → 语义参数 missing 兜底
            logger.warning("semantic judge failed, rule fallback: %s", exc)
            for param, weight, d_field, s_field, critical in semantic:
                judgements.append({
                    "param": param, "demand_value": _demand_value(demand, d_field),
                    "supply_value": capability.get(s_field) if s_field else None,
                    "verdict": MISSING, "weight": weight, "kind": "semantic",
                    "note": "LLM 不可用，按未声明处理",
                })
            return judgements, "rule"

    return judgements, "llm"


def _note(param: str, verdict: str) -> str:
    if verdict == MATCHED:
        return "匹配"
    if verdict == PARTIAL:
        return "部分覆盖，需协商"
    if verdict == MISSING:
        return "厂商未声明"
    return "明确不满足"
