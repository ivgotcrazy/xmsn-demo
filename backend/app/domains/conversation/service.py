"""会话服务（T3.2/T3.5）：start/message/confirm + 快照 + match_runs + 逻辑删除。

- 一会话一产品：会话标题 = 聚焦产品类型（未确定时「新会话」）
- message 编排：选项精确命中 → 确定性直写；否则 LLM 解析 → merge_slot 三态合并
- 确认并提交匹配（单端点 confirm）：生成 buyer_requests 快照（version 递增）+ match_runs（running）+ 异步画像
- 会话/快照逻辑删除（deleted_at，数据保留）
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("xmsn.conversation")

from app.domains.conversation import agent, schema as req_schema
from app.domains.conversation import profile
from app.domains.conversation.schema import SlotTriState
from app.db.models import BuyerRequest, Conversation, ConversationEvent, MatchRun
from app.schemas.common import err_400, err_404
from app.schemas.conversation import (
    AssistantMessage,
    ConfirmResponse,
    ConversationListItem,
    ConversationListResponse,
    ConversationMessageItem,
    ConversationMessagesResponse,
    ConversationStartResponse,
    DemandPoint,
    MessageResponse,
    RequestSnapshot,
    RequestSnapshotListResponse,
)


async def _append_event(db: AsyncSession, conversation_id: str, event_type: str, payload: dict) -> None:
    """会话事件流埋点（append-only，可重放；T3.3）。"""
    try:
        cid = uuid.UUID(conversation_id)
        res = await db.execute(
            select(func.count()).select_from(ConversationEvent).where(ConversationEvent.conversation_id == cid)
        )
        seq = int(res.scalar_one() or 0) + 1
        db.add(ConversationEvent(
            conversation_id=cid, seq=seq, event_type=event_type, payload=payload
        ))
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("conversation_event write failed: %s", exc)


def to_demand_points(state: dict) -> list[DemandPoint]:
    """current_slots → 前端「当前需求」需求点集合（不感知 schema；三态 SET 才展示）。"""
    pts: list[DemandPoint] = []
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    for f in req_schema.fields_for(pt):
        sv = state.get(f["key"])
        if sv and sv.get("state") == SlotTriState.SET.value and sv.get("value") is not None:
            v = sv["value"]
            if isinstance(v, list) and len(v) == 0:
                continue
            if isinstance(v, list):
                v = [str(x) for x in v]
            else:
                v = str(v)
            pts.append(DemandPoint(key=f["key"], label=f["label"], value=v, confidence=1.0))
    for c in state.get("extra_constraints", []):
        pts.append(DemandPoint(key="extra_constraints", label="扩展需求", value=str(c), confidence=0.9))
    return pts


def _title_of(state: dict) -> str:
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    return str(pt) if pt else "新会话"


def _slots_pure(state: dict) -> dict:
    """三态 slots → 纯值 dict（structured_demand 落库用；排除标记保留）。"""
    out: dict = {}
    for k, sv in state.items():
        if k.startswith("_"):
            continue
        if isinstance(sv, dict) and "state" in sv:
            if sv["state"] == SlotTriState.EXCLUDED.value:
                out[k] = {"excluded": True}
            elif sv["state"] == SlotTriState.SET.value and sv.get("value") is not None:
                out[k] = sv["value"]
        elif k == "extra_constraints":
            out[k] = sv
    return out


async def start(db: AsyncSession, user_id: str) -> ConversationStartResponse:
    conv = Conversation(user_id=uuid.UUID(user_id), title="新会话", status="active",
                        conversation_history=[], current_slots={})
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    await _append_event(db, str(conv.conversation_id), "session_started", {"title": "新会话"})
    return ConversationStartResponse(
        conversation_id=str(conv.conversation_id),
        first_message=AssistantMessage(
            content="您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？",
            options=["机顶盒", "智能音箱", "IoT设备", "其他"],
        ),
        demand_points=[],
        title="新会话",
    )


async def _load_conv(db: AsyncSession, conversation_id: str) -> Conversation:
    try:
        cid = uuid.UUID(conversation_id)
    except ValueError:
        raise err_404("会话不存在")
    res = await db.execute(select(Conversation).where(Conversation.conversation_id == cid))
    conv = res.scalar_one_or_none()
    if not conv or conv.deleted_at is not None:
        raise err_404("会话不存在")
    return conv


async def message(db: AsyncSession, conversation_id: str, text: str) -> MessageResponse:
    conv = await _load_conv(db, conversation_id)
    state: dict = dict(conv.current_slots or {})
    history: list = list(conv.conversation_history or [])

    # 意图路由
    turn = len(history) + 1
    await _append_event(db, conversation_id, "user_message", {"turn": turn, "content": text[:500]})
    pending = state.get("_pending") or {}
    intent = agent.route_intent(text, None, state)
    if intent == "done" or intent == "confirm":
        # 完成/确认由 finish/confirm 接口处理；此处回复引导
        reply = AssistantMessage(content="请点击「完成需求描述」生成需求档案，或「确认并提交匹配」。", options=[])
        return MessageResponse(assistant_message=reply, demand_points=to_demand_points(state), title=conv.title)

    # 选项精确命中 → 确定性直写；否则 LLM 解析
    if pending.get("key") and pending.get("options") and text.strip() in pending.get("options", []):
        key = pending["key"]
        val = text.strip()
        # 数值/枚举：multi 单选时按字符串直写（LLM 负责数值归一）
        state = agent.write_option(state, key, val)
        slot_delta = {key: state[key]}
    else:
        parsed = await agent.extract_slots(
            state, text, db=db, meta={"conversation_id": conversation_id, "turn": turn}
        )
        state = agent.merge_slot(state, parsed.get("slot_delta", {}), parsed.get("extra_constraints", []))
        slot_delta = parsed.get("slot_delta", {})

    # 追加历史
    history.append({"role": "user", "content": text})
    if slot_delta:
        history.append({"role": "assistant", "content": _delta_summary(slot_delta, state)})

    # 下一追问 / 完成提示
    next_key, question, opts = agent.decide_question(state)
    state["_pending"] = {"key": next_key, "options": opts} if next_key else {}

    # 更新标题（一会话一产品）
    title = _title_of(state)
    if conv.title == "新会话" and title != "新会话":
        conv.title = title

    history.append({"role": "assistant", "content": question, "options": opts})
    conv.current_slots = state
    conv.conversation_history = history
    await db.commit()
    if slot_delta:
        await _append_event(db, conversation_id, "slot_updated", {"turn": turn, "delta": slot_delta})
    await _append_event(db, conversation_id, "question", {"turn": turn, "question": question[:300], "options": opts})

    return MessageResponse(
        assistant_message=AssistantMessage(content=question, options=opts),
        demand_points=to_demand_points(state),
        title=conv.title,
    )


def _delta_summary(delta: dict, state: dict) -> str:
    """本轮槽位变化的自然语言回执（供历史气泡展示）。"""
    parts = []
    for k, sv in delta.items():
        if not isinstance(sv, dict):
            continue
        label = req_schema.label_of(k, (state.get("product_type") or {}).get("value") if state.get("product_type") else None)
        st = sv.get("state")
        if st == SlotTriState.EXCLUDED.value:
            parts.append(f"不要求{label}")
        else:
            v = sv.get("value")
            parts.append(f"{label}已记录：{'、'.join(v) if isinstance(v, list) else v}")
    return "；".join(parts)


async def _next_version(db: AsyncSession, conversation_id: uuid.UUID) -> int:
    res = await db.execute(
        select(func.count()).select_from(BuyerRequest).where(BuyerRequest.conversation_id == conversation_id)
    )
    return int(res.scalar_one() or 0) + 1


async def confirm(db: AsyncSession, conversation_id: str, user_id: str) -> ConfirmResponse:
    """确认需求档案：生成快照（version 递增）+ match_runs（running）+ 会话关闭。"""
    conv = await _load_conv(db, conversation_id)
    state = dict(conv.current_slots or {})
    if not (state.get("product_type") or {}).get("value"):
        raise err_400("请先明确要寻找的产品类型")

    version = await _next_version(db, conv.conversation_id)
    req = BuyerRequest(
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        version=version,
        structured_demand=_slots_pure(state),
        status="confirmed",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    run = MatchRun(request_id=req.request_id, status="running", total_vendors=0, computation_time_ms=0)
    db.add(run)
    conv.status = "confirmed"
    await db.commit()
    await _append_event(db, conversation_id, "confirmed", {"version": version, "request_id": str(req.request_id)})

    # 异步画像更新（T3.7，不阻塞 confirm 主流程）
    profile.schedule_profile_update(str(req.request_id), str(conv.conversation_id))

    return ConfirmResponse(request_id=str(req.request_id), version=version,
                           redirect_to=f"/buyer/matches/{req.request_id}")


async def list_conversations(db: AsyncSession, user_id: str) -> ConversationListResponse:
    res = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == uuid.UUID(user_id), Conversation.deleted_at.is_(None))
        .order_by(Conversation.updated_at.desc())
    )
    convs = res.scalars().all()
    items = []
    for c in convs:
        rc = await db.execute(
            select(func.count()).select_from(BuyerRequest).where(
                BuyerRequest.conversation_id == c.conversation_id, BuyerRequest.deleted_at.is_(None)
            )
        )
        items.append(ConversationListItem(
            conversation_id=str(c.conversation_id), title=c.title or "新会话",
            status=c.status, updated_at=c.updated_at, request_count=int(rc.scalar_one() or 0),
        ))
    return ConversationListResponse(conversations=items, total=len(items))


async def list_messages(db: AsyncSession, conversation_id: str) -> ConversationMessagesResponse:
    conv = await _load_conv(db, conversation_id)
    history = conv.conversation_history or []
    messages = [
        ConversationMessageItem(role=m["role"], content=m["content"], options=m.get("options", []))
        for m in history
        if m.get("content")
    ]
    state = dict(conv.current_slots or {})
    return ConversationMessagesResponse(
        conversation_id=str(conv.conversation_id), title=conv.title or "新会话",
        status=conv.status, messages=messages, demand_points=to_demand_points(state),
    )


async def list_requests(db: AsyncSession, conversation_id: str) -> RequestSnapshotListResponse:
    conv = await _load_conv(db, conversation_id)
    res = await db.execute(
        select(BuyerRequest)
        .where(BuyerRequest.conversation_id == conv.conversation_id, BuyerRequest.deleted_at.is_(None))
        .order_by(BuyerRequest.version.asc())
    )
    reqs = res.scalars().all()
    items = []
    for r in reqs:
        rc = await db.execute(select(func.count()).select_from(MatchRun).where(MatchRun.request_id == r.request_id))
        items.append(RequestSnapshot(
            request_id=str(r.request_id), version=r.version,
            structured_demand=r.structured_demand or {}, created_at=r.created_at,
            match_count=int(rc.scalar_one() or 0),
        ))
    return RequestSnapshotListResponse(requests=items, total=len(items))


async def delete_conversation(db: AsyncSession, conversation_id: str) -> dict:
    conv = await _load_conv(db, conversation_id)
    conv.deleted_at = datetime.utcnow()
    await db.commit()
    return {"id": conversation_id, "deleted": True, "deleted_at": conv.deleted_at}


async def delete_request(db: AsyncSession, conversation_id: str, request_id: str) -> dict:
    conv = await _load_conv(db, conversation_id)
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise err_404("需求档案不存在")
    res = await db.execute(select(BuyerRequest).where(
        BuyerRequest.request_id == rid, BuyerRequest.conversation_id == conv.conversation_id
    ))
    req = res.scalar_one_or_none()
    if not req:
        raise err_404("需求档案不存在")
    req.deleted_at = datetime.utcnow()
    await db.commit()
    return {"id": request_id, "deleted": True, "deleted_at": req.deleted_at}
