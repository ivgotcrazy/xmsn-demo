"""Stage0 硬过滤（AI核心 §5.3.1 / D2 / D6）：SQL JSONB 零 LLM，strict 受控维度 → passed 集。

规则：
- 只筛 **strict** 且受控的维度（enum/scalar/number，含 options 或数值方向）；text/extended 不在此（走 Stage2 语义）
- enum/scalar：需求值 **⊆** 厂商值（JSONB @> 数组包含；strict=全部满足）
- number：无容差（D6）：direction=upper → 厂商≤需求；lower → 厂商≥需求
- 品类（product_type）为固有硬条件（strict 语义）：structured_tags.product_types 含品类
- 仅 passed 厂商（audit_status='passed'）
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import ontology

logger = logging.getLogger("xmsn.match")


def _build_sql(demand: dict, product_type: str | None) -> tuple[str | None, dict]:
    """生成 Stage0 SQL 条件。无硬条件 → (None, {})（调用方走全量 passed）。"""
    dims = (demand or {}).get("dimensions", {})
    conditions: list[str] = []
    params: dict = {}

    pt = product_type or (dims.get("product_type") or {}).get("value")
    if pt:
        conditions.append("c.structured_tags @> :pt_tag")
        params["pt_tag"] = json.dumps({"product_types": [pt]}, ensure_ascii=False)

    for key, sv in dims.items():
        if key == "product_type":
            continue
        if not isinstance(sv, dict) or sv.get("strictness") != "strict":
            continue  # 仅 strict 维度进硬筛（best-effort 走语义计分）
        v = sv.get("value")
        if v in (None, "", []):
            continue
        f = ontology.field_by_key(key, pt)
        if not f:
            continue
        vt = f.get("value_type")
        if vt in ("enum", "scalar"):
            vals = v if isinstance(v, list) else [v]
            vals = [str(x) for x in vals if x not in (None, "")]
            if not vals:
                continue
            conditions.append(f"c.structured_tags @> :tag_{key}")
            params[f"tag_{key}"] = json.dumps({key: vals}, ensure_ascii=False)
        elif vt == "number":
            direction = f.get("direction")
            try:
                num = float(v)
            except (TypeError, ValueError):
                continue
            if direction == "upper":
                conditions.append(f"(c.structured_tags->>'{key}')::float <= :num_{key}")
            elif direction == "lower":
                conditions.append(f"(c.structured_tags->>'{key}')::float >= :num_{key}")
            else:
                continue
            params[f"num_{key}"] = num
    if not conditions:
        return None, {}
    sql = (
        "SELECT v.vendor_id FROM vendors v "
        "JOIN vendor_capabilities c ON c.vendor_id = v.vendor_id "
        f"WHERE v.audit_status = 'passed' AND " + " AND ".join(conditions)
    )
    return sql, params


async def stage0(db: AsyncSession, demand: dict, product_type: str | None) -> list[str]:
    """Stage0 → passed vendor_id 列表。无硬条件 → 空列表（调用方视作"无过滤"，取全量 passed）。"""
    sql, params = _build_sql(demand, product_type)
    if not sql:
        return []
    try:
        res = await db.execute(text(sql), params)
        return [str(r[0]) for r in res.all()]
    except Exception as exc:  # noqa: BLE001 - 硬筛失败 → 降级不筛（语义兜底），不阻断匹配
        logger.warning("stage0 hard filter failed (降级不筛): %s", exc)
        return []
