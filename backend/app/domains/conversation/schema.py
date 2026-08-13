"""需求 Schema（T3.1）：固定字段 + 品类扩展 + 三态。实现以架构 6.6 / 代理 LLD 0.1 为准。

- 固定字段（共通维度，参与通道B计分）
- 品类扩展（按 product_type 加载：机顶盒/智能音箱/IoT设备/其他）
- 开放扩展（extra_constraints）不在此静态 Schema，见对话合并逻辑
- 三态：set（已指定）/ wildcard（未指定通配）/ excluded（明确排除）
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path


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


# 固定字段（架构 6.6.1）
FIXED_FIELDS: list[dict] = [
    {"key": "product_type", "label": "产品类型", "kind": "single", "required": True, "level": LEVEL_HARD,
     "options": ["机顶盒", "智能音箱", "IoT设备", "其他"]},
    {"key": "os", "label": "操作系统", "kind": "multi", "level": LEVEL_HARD,
     "options": ["Linux", "Android", "RTOS", "其他"]},
    {"key": "interfaces", "label": "接口", "kind": "multi", "level": LEVEL_HARD,
     "options": ["网口", "USB", "HDMI", "GPIO", "其他"]},
    {"key": "certifications", "label": "认证", "kind": "multi", "level": LEVEL_HARD,
     "options": ["CE", "FCC", "CCC", "SRRC", "ISO9001", "其他"]},
    {"key": "moq", "label": "起订量", "kind": "number", "level": LEVEL_SOFT},
    {"key": "lead_time_days", "label": "交期(天)", "kind": "number", "level": LEVEL_SOFT},
    {"key": "application_scenario", "label": "应用场景", "kind": "single", "level": LEVEL_SOFT},
    {"key": "customization_needs", "label": "定制需求", "kind": "single", "level": LEVEL_SOFT},
    {"key": "budget_range", "label": "预算范围", "kind": "single", "optional": True, "level": LEVEL_OPTIONAL},
]

# 品类扩展（架构 6.6.2）→ 外部 JSON 配置（L2 多品类配置化：新增品类不改代码）
def _load_categories() -> dict[str, list[dict]]:
    """从 schema_categories.json 加载品类扩展字段；缺失/异常静默回退空。"""
    p = Path(__file__).resolve().parent / "schema_categories.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


CATEGORY_EXTENSIONS: dict[str, list[dict]] = _load_categories()

# 完成判定"关键维度"（代理 LLD 0.4）：品类锚点之外的必填关键项
KEY_DIMS = ["os", "interfaces", "certifications"]


def _normalize(f: dict, category: str | None = None) -> dict:
    """字段缺省归一：未标 level 则按锚点/关键维度/optional 推断；品类扩展补 depends_on=品类锚点。"""
    f = dict(f)
    if "level" not in f:
        if f["key"] == "product_type" or f["key"] in KEY_DIMS:
            f["level"] = LEVEL_HARD
        elif f.get("optional"):
            f["level"] = LEVEL_OPTIONAL
        else:
            f["level"] = LEVEL_SOFT
    if "depends_on" not in f and category:
        f["depends_on"] = [{"key": "product_type", "values": [category]}]
    return f


def fields_for(product_type: str | None) -> list[dict]:
    """当前品类的完整字段（固定 + 品类扩展），已归一 level/depends_on。"""
    fixed = [_normalize(f) for f in FIXED_FIELDS]
    if not product_type:
        return fixed
    return fixed + [_normalize(f, product_type) for f in CATEGORY_EXTENSIONS.get(product_type, [])]


def label_of(key: str, product_type: str | None = None) -> str:
    for f in fields_for(product_type):
        if f["key"] == key:
            return f["label"]
    return key


def next_unfilled(state: dict, product_type: str | None) -> dict | None:
    """按字段顺序返回下一个未指定且必填的字段（用于追问）；无则 None。"""
    for f in fields_for(product_type):
        if f.get("optional"):
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
    """动态 Validator：active 且 level=hard 的字段 100% SET 且非空 → done。
    返回 {done, missing_hard[], missing_soft[]}。"""
    active = active_fields(state, product_type)
    missing_hard = [f["key"] for f in active
                    if f.get("level") == LEVEL_HARD and not _is_filled(state.get(f["key"]))]
    missing_soft = [f["key"] for f in active
                    if f.get("level") in (LEVEL_SOFT, LEVEL_OPTIONAL) and not _is_filled(state.get(f["key"]))]
    return {"done": len(missing_hard) == 0,
            "missing_hard": missing_hard,
            "missing_soft": missing_soft}
