"""需求 Schema（T3.1）：本体（D1）+ 品类扩展 + 三态。实现以供需Schema / AI核心 v2 为准。

- 固定字段（通用维度）= 本体 general（provenance=general，供需Schema §3.4）
- 品类扩展（按 product_type 加载）= 本体品类字段（extends 共享组已合并，§3.5）
- 开放扩展（extended）不在此静态 Schema，见对话合并逻辑（D8 结构化）
- 三态：set（已指定）/ wildcard（未指定通配）/ excluded（明确排除）——Step 3 收敛为正向点
"""
from __future__ import annotations

import re
from enum import Enum

from app.domains import ontology


# 数字槽位归一（需求侧）：把带单位/中文量词/自然语言的数字值归一成 int。
# 例："1000台"→1000、"不超过30天"→30、"至少5000"→5000、">=3000"→3000、"约1000"→1000、"5000+"→5000
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def normalize_number(value) -> int | None:
    """数字槽位值 → int；无法解析返回 None（调用方决定保留原值或置空）。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().replace(",", "").replace("，", "")
    if not s:
        return None
    m = _NUMBER_RE.search(s)
    if not m:
        return None
    try:
        return int(float(m.group(0)))
    except (TypeError, ValueError):
        return None


class SlotTriState(str, Enum):
    SET = "set"
    WILDCARD = "wildcard"
    EXCLUDED = "excluded"


# 字段必填级别（代理详细设计 v2 9.1）：
#   hard    硬约束：缺失阻塞完成判定/提交（品类锚点、关键维度）
#   soft    软引导：细节参数，可通配不阻塞
#   optional 可选：预算等
LEVEL_HARD = "hard"
LEVEL_SOFT = "soft"
LEVEL_OPTIONAL = "optional"

# 依赖/联动声明：depends_on = [{"key": "...", "values": [...]}]
#   全部满足（依赖字段 SET 且值交集非空；values 省略则仅要求 SET）时该字段才生效。
#   未生效字段：不进入 allowed_set / 追问 / 完成判定；reconcile 会确定性清除其脏值。


# 固定字段（通用维度）= 本体 general（D1，来源 ontology.json / 供需Schema §3.4）
FIXED_FIELDS: list[dict] = ontology.general_fields()

# 品类扩展 = 本体品类字段（extends 共享组已合并，D1，来源 ontology.json / 供需Schema §3.5）
CATEGORY_EXTENSIONS: dict[str, list[dict]] = {
    name: ontology.category_fields(name) for name in ontology.category_names()
}


def fields_for(product_type: str | None) -> list[dict]:
    """品类 Schema 全量字段 = 本体 general + 品类（extends 已合并）。"""
    return ontology.fields_for(product_type)


def label_of(key: str, product_type: str | None = None) -> str:
    return ontology.label_of(key, product_type)


def next_unfilled(state: dict, product_type: str | None) -> dict | None:
    """按字段顺序返回下一个未指定且必填的字段（用于追问）；无则 None。

    D6：已确认"不限/跳过"的维度（_confirmed_unlimited，Agent 私有标记）不再追问。"""
    skip = set(state.get("_confirmed_unlimited", []))
    for f in fields_for(product_type):
        if f.get("optional") or f["key"] in skip:
            continue
        sv = state.get(f["key"])
        if not sv or sv.get("state") != SlotTriState.SET.value or _empty(sv.get("value")):
            return f
    return None


def _empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, list):
        return len(v) == 0
    return str(v).strip() == ""


# ---- 代理详细设计 v2 9.3：依赖 / 待填集 / 动态 Validator（确定性）----


def _deps_ok(state: dict, f: dict) -> bool:
    """依赖声明是否满足：全部 depends_on 需 SET 且（values 缺省或值交集非空）。"""
    for dep in f.get("depends_on") or []:
        key = dep["key"]
        vals = dep.get("values")
        sv = state.get(key)
        if not sv or sv.get("state") != SlotTriState.SET.value:
            return False
        if vals is not None:
            v = sv.get("value")
            if isinstance(v, list):
                if not (set(vals) & set(v)):
                    return False
            elif v not in vals:
                return False
    return True


def active_fields(state: dict, product_type: str | None) -> list[dict]:
    """按依赖声明过滤当前生效字段（allowed_set / 追问 / 判定的输入）。"""
    return [f for f in fields_for(product_type) if _deps_ok(state, f)]


def _is_filled(sv) -> bool:
    """槽位是否"已决定"：SET 且有值，或明确 EXCLUDED / WILDCARD（不限/排除=已决定，不再追问、完成判定视为满足）。"""
    if not sv:
        return False
    st = sv.get("state")
    if st in (SlotTriState.EXCLUDED.value, SlotTriState.WILDCARD.value):
        return True
    if st != SlotTriState.SET.value:
        return False
    v = sv.get("value")
    if v is None:
        return False
    if isinstance(v, list):
        return len(v) > 0
    return str(v).strip() != ""


def pending_slots(state: dict, product_type: str | None) -> list[dict]:
    """当前合法待填集：active 且未填；排序 硬→软→可选，同级按 Schema 顺序。"""
    order = {LEVEL_HARD: 0, LEVEL_SOFT: 1, LEVEL_OPTIONAL: 2}
    items = [(i, f) for i, f in enumerate(active_fields(state, product_type))
             if not _is_filled(state.get(f["key"]))]
    items.sort(key=lambda p: (order.get(p[1].get("level", LEVEL_SOFT), 1), p[0]))
    return [f for _, f in items]


def next_slot(state: dict, product_type: str | None) -> dict | None:
    """本轮追问锚点 = 待填集第一项（硬约束优先）。"""
    ps = pending_slots(state, product_type)
    return ps[0] if ps else None


def validate_completion(state: dict, product_type: str | None) -> dict:
    """完成判定（D12）：品类锚定 + 至少 1 个需求点（品类外 dimensions 或 extended 非空）→ done。

    不再有 hard/soft 分级（D11）；missing_* 保留空结构兼容旧调用。最终由用户确认（两步化确认框）把关。
    返回 {done, missing_hard[], missing_soft[]}。"""
    anchored = bool((state.get("product_type") or {}).get("value"))
    enough = count_demand_points(state, product_type) >= 1
    return {"done": anchored and enough, "missing_hard": [], "missing_soft": []}


def count_demand_points(state: dict, product_type: str | None = None) -> int:
    """品类外需求点数（D12 提交门槛）：非 product_type 的正向指定点（value 非空）+ extended 条数。"""
    n = 0
    for k, sv in state.items():
        if k.startswith("_") or k in ("product_type", "extended"):
            continue
        if isinstance(sv, dict) and not _empty(sv.get("value")):
            n += 1
    n += len(state.get("extended") or [])
    return n


def schema_ref_of(product_type: str | None) -> str:
    """品类 Schema 引用（D1：需求档案 = 品类 Schema 的实例，通过 schema_ref 指向定义）。"""
    return f"category:{product_type}@v1" if product_type else "category:@v1"
