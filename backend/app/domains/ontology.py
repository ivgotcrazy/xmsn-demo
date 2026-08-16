"""供需双侧单一本体（D1）：统一维度字典，JSON 配置 + 查询 API。

数据源：`ontology.json`（《供需Schema设计》§2 元数据 / §3.4 通用 / §3.5 品类+消费电子通用 / §7 配置样例）
- `general`：所有品类公共维度（provenance=general）
- `shared_groups`：共享品类维度组（如 `consumer_electronics`：os/interfaces/wireless，§9 决策1 归品类）
- `categories`：各品类 = `extends`(共享组) + `fields`(本品类字段)

品类 Schema = general + extends 共享组 + 品类字段（需求档案/前端/匹配均按此展开，D1 单一本体、无映射）。

⚠ 兼容层：为现有 Agent/匹配（Step 3 迁移前）推导 `level`/`optional`（D11 已移除 demand_level，本体不含该字段；
Step 3 改为正向点 + strictness 后本层删除）。
"""
from __future__ import annotations

import json
from pathlib import Path

_ONTOLOGY_PATH = Path(__file__).resolve().parent / "ontology.json"


def _load() -> dict:
    return json.loads(_ONTOLOGY_PATH.read_text(encoding="utf-8"))


_ONT = _load()

_LEVEL_HARD = "hard"
_LEVEL_SOFT = "soft"
_LEVEL_OPTIONAL = "optional"


def _defaults(f: dict) -> dict:
    """字段缺省归一 + 兼容层（level/optional 推导，Step 3 删除）。"""
    f = dict(f)
    f.setdefault("provenance", "category")
    f.setdefault("value_type", "enum" if f.get("options") else "text")
    f.setdefault("kind", "single")
    f.setdefault("options", None)
    f.setdefault("direction", None)
    f.setdefault("unit", None)
    f.setdefault("compare_tolerance", 1.5)
    f.setdefault("depends_on", None)
    f.setdefault("applicable", "both")
    # ---- 兼容层（Step 3 删除）----
    if f["key"] == "product_type":
        f.setdefault("level", _LEVEL_HARD)
    elif f["key"] == "budget_range":
        f.setdefault("level", _LEVEL_OPTIONAL)
    else:
        f.setdefault("level", _LEVEL_SOFT)
    f.setdefault("optional", f.get("level") == _LEVEL_OPTIONAL)
    f.setdefault("required", f["key"] == "product_type")
    return f


GENERAL: list[dict] = [_defaults(f) for f in _ONT.get("general", [])]

_SHARED: dict[str, list[dict]] = {
    name: [_defaults(f) for f in fields]
    for name, fields in _ONT.get("shared_groups", {}).items()
}


def _category_extends(name: str) -> list[dict]:
    c = _ONT.get("categories", {}).get(name)
    if not c:
        return []
    out: list[dict] = []
    for g in c.get("extends", []):
        out.extend(_SHARED.get(g, []))
    out.extend(_defaults(f) for f in c.get("fields", []))
    # 品类字段未显式声明 depends_on → 补品类锚点依赖
    for f in out:
        if f.get("depends_on") is None:
            f["depends_on"] = [{"key": "product_type", "values": [name]}]
    return out


CATEGORIES: dict[str, list[dict]] = {
    name: _category_extends(name) for name in _ONT.get("categories", {})
}


# ---------- 查询 API ----------

def version() -> str:
    return _ONT.get("version", "v1")


def category_names() -> list[str]:
    """已配置品类（闭集，无"其他"，D6）。"""
    return list(_ONT.get("categories", {}).keys())


def general_fields() -> list[dict]:
    return list(GENERAL)


def category_fields(category: str | None) -> list[dict]:
    """品类字段 = extends 共享组 + 本品类字段（provenance=category）。"""
    if not category:
        return []
    return list(CATEGORIES.get(category, []))


def fields_for(category: str | None) -> list[dict]:
    """品类 Schema 全量字段 = general + 品类（extends 已合并）。"""
    return general_fields() + category_fields(category)


def field_by_key(key: str, category: str | None = None) -> dict | None:
    for f in fields_for(category):
        if f["key"] == key:
            return f
    return None


def label_of(key: str, category: str | None = None) -> str:
    f = field_by_key(key, category)
    return f["label"] if f else key


def value_type_of(key: str, category: str | None = None) -> str | None:
    f = field_by_key(key, category)
    return f["value_type"] if f else None
