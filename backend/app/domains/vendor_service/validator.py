"""能力档案校验器（厂商解析 LLD 4.3）：Schema 校验 / 置空 / 归一 / 完备度 / source_map。

能力 Schema 与《匹配详细设计》PARAM_MAP 厂商侧同源；硬能力缺失计入完备度，
与档案页缺失项标红严格一致（2026-08-10 决策）。
"""
from __future__ import annotations

# 硬能力（RULE 判定主锚，缺失计入完备度）
HARD_FIELDS = [
    "process_types",
    "certifications",
    "os",
    "interfaces",
    "moq",
    "lead_time_days",
    "monthly_capacity",
]
# 软标签（语义召回，不设硬门槛）
SOFT_FIELDS = ["product_types", "application_scenarios", "customization"]
ALL_FIELDS = HARD_FIELDS + SOFT_FIELDS


def _has_value(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, list):
        return len(v) > 0
    if isinstance(v, str):
        return bool(v.strip())
    return True


def validate(extracted: dict) -> tuple[dict, float, dict, str, list]:
    """归一 structured_tags + 计算 completeness + 归一 source_map（含 confidence）+ 摘要。"""
    raw_tags = (extracted.get("structured_tags") or {})

    tags: dict = {}
    for k in ALL_FIELDS:
        v = raw_tags.get(k)
        if isinstance(v, list):
            tags[k] = [str(x).strip() for x in v if str(x).strip()]
        elif isinstance(v, (int, float)) and v is not None:
            tags[k] = v
        elif isinstance(v, str) and v.strip():
            tags[k] = v.strip()
        elif k in HARD_FIELDS:
            tags[k] = []  # 硬能力缺失置空（不猜测补全）
        else:
            tags[k] = None  # 软标签缺失置空

    filled = sum(1 for k in HARD_FIELDS if _has_value(tags.get(k)))
    completeness = round(filled / len(HARD_FIELDS), 3)

    source_map: dict = {}
    for k, ref in (extracted.get("sources") or {}).items():
        if k not in ALL_FIELDS or not isinstance(ref, dict):
            continue
        source_map[k] = {
            "doc_id": str(ref.get("doc_id", "")),
            "doc_name": str(ref.get("doc_name", "")),
            "page": int(ref.get("page", 1) or 1),
            "chunk_text": str(ref.get("chunk_text", "")),
            "confidence": float(ref.get("confidence", 0.5) or 0.5),
        }

    summary = str(extracted.get("summary_text") or "").strip()
    soft_tags = [str(x).strip() for x in (extracted.get("soft_tags") or []) if str(x).strip()]  # D3 软层自由标签
    return tags, completeness, source_map, summary, soft_tags
