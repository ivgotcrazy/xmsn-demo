"""用户画像（T3.7）——《用户画像设计》v1.0。

- ensure_active_schema：幂等 seed `profile_schemas` v1（6 维：行业焦点/OS/认证/接口/订单模式/交互风格）
- extract_profile：需求确认后，LLM 产出"本次学到什么"的增量建议（updates）
- merge_profile：代码层逐条校验（key 存在/type-enum/置信度≥0.6）后按 merge 策略合并，幻觉不直接入库
- schedule_profile_update：异步触发（新 DB 会话后台跑，不阻塞 confirm 主流程）
- 画像只影响对话引导（use_in_prompt 注入），不参与匹配打分（画像设计 1.2）
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BuyerRequest, Conversation, ProfileSchema, UserProfile
from app.llm.client import chat

logger = logging.getLogger("xmsn.profile")

CONF_THRESHOLD = 0.6

# 画像 Schema v1（画像设计 3.4 Dimension 契约）
PROFILE_SCHEMA_V1 = {
    "schema_version": 1,
    "name": "buyer_profile_v1",
    "scope": "base",
    "industry": None,
    "dimensions": [
        {"key": "industry_focus", "name": "行业焦点", "type": "string[]", "enum": ["机顶盒", "智能音箱", "IoT设备"],
         "source": "implicit", "merge": "append", "use_in_prompt": True, "queryable": False,
         "description": "用户历史需求中常关注的行业/品类", "examples": ["机顶盒"]},
        {"key": "preferred_os", "name": "偏好操作系统", "type": "string[]", "enum": ["Linux", "Android", "RTOS", "其他"],
         "source": "implicit", "merge": "append", "use_in_prompt": True, "queryable": False,
         "description": "历史需求中常选的 OS", "examples": ["Linux"]},
        {"key": "common_certifications", "name": "常备认证", "type": "string[]", "enum": [],
         "source": "implicit", "merge": "append", "use_in_prompt": True, "queryable": False,
         "description": "历史需求中常要求的认证（CE/FCC/ISO9001 等）", "examples": ["CE"]},
        {"key": "typical_interfaces", "name": "常用接口", "type": "string[]", "enum": [],
         "source": "implicit", "merge": "append", "use_in_prompt": True, "queryable": False,
         "description": "历史需求中常用的硬件接口", "examples": ["网口", "USB"]},
        {"key": "order_pattern", "name": "订单模式", "type": "object", "enum": [],
         "source": "implicit", "merge": "latest", "use_in_prompt": True, "queryable": False,
         "description": "历史订单规模/频次特征（如起订量、交期偏好）", "examples": [{"moq_typical": 5000}]},
        {"key": "interaction_style", "name": "交互风格", "type": "string",
         "enum": ["detail_oriented", "price_sensitive", "quick_decisive"], "source": "implicit",
         "merge": "latest", "use_in_prompt": True, "queryable": False,
         "description": "交互偏好：重细节/重价格/快速决断", "examples": ["detail_oriented"]},
    ],
}

EXTRACT_PROMPT = """你是一个用户画像分析专家。基于以下信息，输出用户画像的增量更新建议。

# 画像Schema（严格遵循 key/type/enum，不得自创维度）
{dimensions}

# 当前画像（最新值，可能为空）
{current_profile}

# 本次需求确认记录（结构化）
{demand}

# 本次会话行为摘要
{signal}

请只输出如下 JSON（不要输出其他文字）：
{{
  "updates": [
    {{"key": "preferred_os", "value": ["Linux"], "confidence": 0.9, "merge": "append"}}
  ],
  "no_change": true
}}
规则：
- key 必须存在于 Schema；value 必须符合该 key 的 type/enum；
- confidence 0~1（用户显式指定/多次出现 → 高；仅一次暗示 → 低）；
- 若无有效信息可更新，则 no_change=true 且 updates 为空数组。
"""


async def ensure_active_schema(db: AsyncSession) -> ProfileSchema:
    """幂等获取 active 画像 Schema v1（不存在则插入）。"""
    res = await db.execute(
        select(ProfileSchema).where(ProfileSchema.active.is_(True), ProfileSchema.scope == "base")
        .order_by(ProfileSchema.schema_version.desc())
    )
    schema = res.scalars().first()
    if schema:
        return schema
    schema = ProfileSchema(
        schema_version=PROFILE_SCHEMA_V1["schema_version"],
        name=PROFILE_SCHEMA_V1["name"],
        scope=PROFILE_SCHEMA_V1["scope"],
        industry=PROFILE_SCHEMA_V1["industry"],
        dimensions=PROFILE_SCHEMA_V1["dimensions"],
        active=True,
    )
    db.add(schema)
    await db.commit()
    await db.refresh(schema)
    logger.info("profile schema v1 seeded")
    return schema


def _dimension_map(schema: ProfileSchema) -> dict:
    return {d["key"]: d for d in schema.dimensions}


def _validate_value(dim: dict, value) -> bool:
    """type/enum 校验（画像设计 4.4）。"""
    t = dim.get("type")
    if t == "string[]":
        if not isinstance(value, list):
            return False
        if dim.get("enum"):
            return all(v in dim["enum"] for v in value)
        return all(isinstance(v, str) for v in value)
    if t == "string":
        if not isinstance(value, str):
            return False
        return not dim.get("enum") or value in dim["enum"]
    if t == "object":
        return isinstance(value, dict)
    return False


def _merge_values(merge: str, old, new):
    """merge 策略：append 去重追加 / latest 覆盖（画像设计 3.4/4.4）。"""
    if merge == "append" and isinstance(old, list) and isinstance(new, list):
        out = list(old)
        for v in new:
            if v not in out:
                out.append(v)
        return out
    return new


async def _get_profile(db: AsyncSession, user_id: str) -> UserProfile:
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == uuid.UUID(user_id)))
    prof = res.scalar_one_or_none()
    if not prof:
        prof = UserProfile(user_id=uuid.UUID(user_id), schema_version=1, profile_data={}, confidence={})
        db.add(prof)
        await db.commit()
        await db.refresh(prof)
    return prof


async def extract_profile(db: AsyncSession, user_id: str, demand: dict, signal: str) -> None:
    """需求确认后：LLM 提取增量 → 合并器校验合并（异步调用）。"""
    try:
        schema = await ensure_active_schema(db)
        prof = await _get_profile(db, user_id)
        dims = schema.dimensions
        prompt = EXTRACT_PROMPT.format(
            dimensions=json.dumps(dims, ensure_ascii=False),
            current_profile=json.dumps(prof.profile_data or {}, ensure_ascii=False),
            demand=json.dumps(demand, ensure_ascii=False),
            signal=(signal or "")[:1000],
        )
        raw = await chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=512)
        data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
        if data.get("no_change"):
            return
        updates = data.get("updates") or []
        await merge_profile(db, prof, schema, updates)
    except Exception as exc:  # noqa: BLE001
        logger.warning("profile extract failed (降级，不影响主流程): %s", exc)


async def merge_profile(db: AsyncSession, prof: UserProfile, schema: ProfileSchema, updates: list) -> None:
    """合并器（画像设计 4.4）：key 校验 / type-enum / 置信度阈值 / merge 策略。"""
    dims = _dimension_map(schema)
    data = dict(prof.profile_data or {})
    conf = dict(prof.confidence or {})
    changed = False
    for u in updates:
        key = u.get("key")
        dim = dims.get(key)
        if not dim:
            logger.info("profile: 自创维度丢弃 %s", key)
            continue
        value = u.get("value")
        if not _validate_value(dim, value):
            logger.info("profile: type/enum 校验失败 %s", key)
            continue
        c = float(u.get("confidence", 0))
        if c < CONF_THRESHOLD:
            logger.info("profile: 低置信度丢弃 %s (%.2f)", key, c)
            continue
        merge = u.get("merge") or dim.get("merge") or "latest"
        data[key] = _merge_values(merge, data.get(key), value)
        conf[key] = max(conf.get(key, 0.0), c)
        changed = True
    if changed:
        prof.profile_data = data
        prof.confidence = conf
        prof.total_requests = (prof.total_requests or 0) + 1
        prof.last_request_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("profile updated for user %s", prof.user_id)


async def _run_async_profile_update(request_id: str, conversation_id: str) -> None:
    """后台任务：独立会话加载快照+历史 → 提取画像（不阻塞 confirm 主流程）。"""
    from app.db.session import SessionLocal
    try:
        async with SessionLocal() as db:
            req = await db.get(BuyerRequest, uuid.UUID(request_id))
            conv = await db.get(Conversation, uuid.UUID(conversation_id))
            if not req or not conv:
                return
            demand = req.structured_demand or {}
            history = conv.conversation_history or []
            user_msgs = [m.get("content") for m in history if m.get("role") == "user"]
            signal = "；".join(str(m) for m in user_msgs[-6:])
            await extract_profile(db, str(conv.user_id), demand, signal)
    except Exception as exc:  # noqa: BLE001
        logger.warning("profile background update failed: %s", exc)


def schedule_profile_update(request_id: str, conversation_id: str) -> None:
    """confirm 后异步调度画像更新（fire-and-forget）。"""
    asyncio.create_task(_run_async_profile_update(request_id, conversation_id))
