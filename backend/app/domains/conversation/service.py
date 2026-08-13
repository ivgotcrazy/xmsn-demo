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
    """三态 slots → 纯值 dict（兼容旧快照读取；新快照用 _slots_snapshot）。"""
    out: dict = {}
    for k, sv in state.items():
        if k.startswith("_"):
            continue
        if isinstance(sv, dict) and "state" in sv:
            if sv["state"] == SlotTriState.EXCLUDED.value:
                out[k] = {"excluded": True, "value": sv.get("value")}  # 保留排除值（M4 硬过滤）
            elif sv["state"] == SlotTriState.SET.value and sv.get("value") is not None:
                out[k] = sv["value"]
        elif k == "extra_constraints":
            out[k] = sv
    return out


def _slots_snapshot(state: dict) -> dict:
    """三态 slots → 三态快照（structured_demand 落库，对齐匹配详细设计 0.2/8.1：含 state/value/排除）。"""
    out: dict = {}
    for k, sv in state.items():
        if k.startswith("_"):
            continue
        if isinstance(sv, dict) and "state" in sv:
            out[k] = {"value": sv.get("value"), "state": sv["state"]}
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


def _bump_stall(state: dict, progress: bool) -> None:
    """熔断计数：有进展清零，无进展自增（连续无进展 ≥3 触发换方式/引导人工）。"""
    if progress:
        state["_stall_counter"] = 0
    else:
        state["_stall_counter"] = state.get("_stall_counter", 0) + 1


async def _non_extract_message(
    db: AsyncSession, conv: Conversation, state: dict, history: list,
    turn: int, text: str, intent: str, reply_text: str,
) -> MessageResponse:
    """路径A 非填槽轮分流：按推理节点结构化 intent 处理（QA/引导/弱收尾/推荐）。

    B/C 合规后置保险：原文强命中厂商/结果/闲聊 → 强制引导话术（防模型越界评价厂商）。
    """
    override = agent.guide_override_for(text)
    if override == "guide_result" and intent != "recommend":
        intent = "guide_result"          # 强命中厂商/结果 → 强制引导
    elif override == "guide_back":
        intent = "guide_back"

    if intent == "guide_result":
        content = agent.guide_to_results(_title_of(state))
        evt, opts = "redirect", []
    elif intent == "guide_back":
        content = agent.guide_back(_title_of(state))
        evt, opts = "guard", []
    elif intent == "weak_close":
        content = agent.weak_close_recap(state)
        opts = ["确认并提交匹配", "继续补充"]
        state["_pending"] = {"key": None, "options": opts}
        evt = "recap"
    elif intent == "recommend":
        profile_ctx = await profile.build_profile_context(db, str(conv.user_id))
        rec = agent.build_recommendation(state, profile_ctx)
        if not rec:
            _nk, content, opts = agent.decide_question(state)
            state["_pending"] = {"key": _nk, "options": opts} if _nk else {}
            evt = "question"
        else:
            state["_recommend"] = {"key": rec["key"], "value": rec["value"]}
            val_s = agent._fmt_val(rec["value"])
            content = f"看您拿不定主意，我建议：{rec['label']}选「{val_s}」（{rec['reason']}）。要我按此填写吗？"
            opts = ["按建议填写", "我自己定"] + ([] if rec["key"] == "product_type" else ["跳过"])
            state["_pending"] = {"key": None, "options": opts}
            evt = "recommend"
    else:  # qa / empty
        content = reply_text or "好的，请继续补充您的需求。"
        opts = []
        evt = "qa_answer" if intent == "qa" else "question"
        _bump_stall(state, False)

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": content, "options": opts})
    conv.current_slots = state
    conv.conversation_history = history
    await db.commit()
    await _append_event(db, str(conv.conversation_id), evt, {"turn": turn, "content": text[:300]})
    return MessageResponse(
        assistant_message=AssistantMessage(content=content, options=opts),
        demand_points=to_demand_points(state), title=conv.title,
    )


async def message(db: AsyncSession, conversation_id: str, text: str) -> MessageResponse:
    """对话轮次（代理详细设计 v2 8 章）：意图路由 → 强命令/帮助/推荐直写/推理节点 → 合并修剪 → 完成判定 → 追问。"""
    conv = await _load_conv(db, conversation_id)
    state: dict = dict(conv.current_slots or {})
    history: list = list(conv.conversation_history or [])
    turn = len(history) + 1
    await _append_event(db, conversation_id, "user_message", {"turn": turn, "content": text[:500]})

    intent = agent.route_intent(text, None, state)

    # ① 强命令 → 直接提交（SC-22/25；品类锚点缺失禁止提交）
    if intent == "confirm_command":
        if not (state.get("product_type") or {}).get("value"):
            reply = AssistantMessage(content="请先明确要寻找的产品类型，才能提交匹配。", options=[])
            return MessageResponse(assistant_message=reply, demand_points=to_demand_points(state), title=conv.title)
        try:
            req, _run, warnings = await _do_confirm(db, conv)
        except Exception as exc:  # noqa: BLE001
            logger.warning("auto confirm failed: %s", exc)
            reply = AssistantMessage(content="提交失败，请重试或联系客服。", options=[])
            return MessageResponse(assistant_message=reply, demand_points=to_demand_points(state), title=conv.title)
        content = f"✅ 已提交匹配（需求档案 v{req.version}），正在计算匹配中…"
        if warnings:
            content += "\n" + warnings[0]
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": content, "options": []})
        state["_pending"] = {}
        conv.current_slots = state
        conv.conversation_history = history
        await db.commit()
        await _append_event(db, conversation_id, "confirm",
                            {"turn": turn, "version": req.version, "request_id": str(req.request_id)})
        return MessageResponse(assistant_message=AssistantMessage(content=content, options=[]),
                               demand_points=to_demand_points(state), title=conv.title,
                               submitted=True, redirect_to=f"/buyer/matches/{req.request_id}", warnings=warnings)

    # ② 帮助（确定性命令）
    if intent == "help":
        content = agent.help_text()
        reply = AssistantMessage(content=content, options=[])
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": content, "options": reply.options})
        conv.conversation_history = history
        await db.commit()
        await _append_event(db, conversation_id, "guide", {"turn": turn, "content": text[:300]})
        return MessageResponse(assistant_message=reply, demand_points=to_demand_points(state), title=conv.title)

    # ③ SC-05 拒绝建议 → 清空 _recommend，正常追问
    if intent == "decline_recommend":
        state.pop("_recommend", None)
        _nk, _q, _o = agent.decide_question(state)
        reply = AssistantMessage(content=_q, options=_o)
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": _q, "options": _o})
        state["_pending"] = {"key": _nk, "options": _o} if _nk else {}
        conv.current_slots = state
        conv.conversation_history = history
        await db.commit()
        return MessageResponse(assistant_message=reply, demand_points=to_demand_points(state), title=conv.title)

    # ④ 选项/建议直写 → 确定性；否则推理节点（Tool Calling 一次推断）
    pending = state.get("_pending") or {}
    parsed = {"slot_delta": {}, "extra_constraints": []}
    rr_reply = ""
    if intent == "accept_recommend":
        # SC-05：采纳建议 → 直写建议值（确定性）
        rec = state.pop("_recommend", None)
        if rec and rec.get("key"):
            state = agent.write_option(state, rec["key"], rec["value"])
            parsed = {"slot_delta": {rec["key"]: state[rec["key"]]}, "extra_constraints": []}
        progress = True
    elif intent == "skip_current":
        # SC-05：跳过 → 当前待填维度置通配
        state.pop("_recommend", None)
        _pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
        _nf = req_schema.next_slot(state, _pt)
        if _nf:
            state[_nf["key"]] = {"value": None, "state": SlotTriState.WILDCARD.value}
            parsed = {"slot_delta": {_nf["key"]: state[_nf["key"]]}, "extra_constraints": []}
        progress = True
    elif pending.get("key") and pending.get("options") and text.strip() in pending.get("options", []):
        key = pending["key"]
        val = text.strip()
        state = agent.write_option(state, key, val)
        parsed = {"slot_delta": {key: state[key]}, "extra_constraints": []}
        progress = True
    elif agent.is_continuation(text) and agent.completion_ready(state):
        # 完成态"继续补充"→ 开放引导（跳过 LLM）
        progress = False
    else:
        profile_ctx = await profile.build_profile_context(db, str(conv.user_id))
        rr = await agent.agent_reasoning(
            state, text, db=db,
            meta={"conversation_id": conversation_id, "turn": turn, "user_profile": profile_ctx},
        )
        rr_reply = rr["reply_text"].strip()
        state = agent.merge_slot(state, rr["slot_delta"], rr["extra_constraints"])
        parsed = {"slot_delta": rr["slot_delta"], "extra_constraints": rr["extra_constraints"]}
        # 路径A：非填槽轮 → 按推理节点结构化 intent 分流（QA/引导/弱收尾/推荐），本轮结束
        if rr.get("intent", "extract") != "extract":
            return await _non_extract_message(
                db, conv, state, history, turn, text, rr.get("intent", "empty"), rr_reply)
        progress = bool(rr["slot_delta"] or rr["extra_constraints"])

    slot_delta = parsed.get("slot_delta", {})
    new_extras = parsed.get("extra_constraints", [])

    # 熔断计数（有进展清零）
    _bump_stall(state, progress)

    # ⑤ 状态修剪 reconcile（merge 后确定性级联清理：依赖失效/旧品类扩展清空）
    state = agent.reconcile(state)

    # 历史回显（槽位变更 + 扩展需求）
    history.append({"role": "user", "content": text})
    summary = _delta_summary(slot_delta, state)
    if new_extras:
        if summary:
            summary += "；"
        summary += "扩展需求已记录：" + "、".join(new_extras)
    if slot_delta or new_extras:
        history.append({"role": "assistant", "content": summary})

    # 下一追问 / 完成提示 / 熔断
    next_key, question, opts = agent.decide_question(state)
    state["_pending"] = {"key": next_key, "options": opts} if next_key else {}

    # 混合意图：有槽位且 LLM 有正文 → 正文（答疑/回执）+ 追问合并为一气泡
    final_content = f"{rr_reply}\n\n{question}" if (rr_reply and slot_delta) else question

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
        assistant_message=AssistantMessage(content=final_content, options=opts),
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
        elif st == SlotTriState.WILDCARD.value:
            parts.append(f"{label}不限")
        else:
            v = sv.get("value")
            parts.append(f"{label}已记录：{'、'.join(v) if isinstance(v, list) else v}")
    return "；".join(parts)


async def _next_version(db: AsyncSession, conversation_id: uuid.UUID) -> int:
    res = await db.execute(
        select(func.count()).select_from(BuyerRequest).where(BuyerRequest.conversation_id == conversation_id)
    )
    return int(res.scalar_one() or 0) + 1


async def _do_confirm(db: AsyncSession, conv: Conversation) -> tuple[BuyerRequest, MatchRun, list[str]]:
    """确认提交（SC-22/25）：生成快照（version++）+ match_runs（running）。

    - 品类锚点缺失 → 400（禁止提交）；
    - 其余硬约束缺失 + 强命令 → 允许但返回显著警示（warnings，不静默），对应 SC-25；
    - 会话状态重新设计（第 10 章）：不再写 conv.status="confirmed"（提交是可重复事件，会话保持 active）。
    """
    state = dict(conv.current_slots or {})
    if not (state.get("product_type") or {}).get("value"):
        raise err_400("请先明确要寻找的产品类型")
    pt = (state.get("product_type") or {}).get("value")
    verdict = req_schema.validate_completion(state, pt)
    missing = [req_schema.label_of(k, pt) for k in verdict["missing_hard"]]
    warnings: list[str] = []
    if missing:
        warnings.append("以下需求尚未明确：" + "、".join(missing) + "。已按当前信息提交匹配，可稍后继续补充并重新匹配。")

    version = await _next_version(db, conv.conversation_id)
    req = BuyerRequest(
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        version=version,
        structured_demand=_slots_snapshot(state),
        status="confirmed",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    run = MatchRun(request_id=req.request_id, status="running", total_vendors=0, computation_time_ms=0)
    db.add(run)
    # 会话状态重新设计：不写 conv.status（保持 active）
    await db.commit()
    await _append_event(db, str(conv.conversation_id), "confirmed",
                        {"version": version, "request_id": str(req.request_id)})

    # 异步画像更新（T3.7，不阻塞 confirm 主流程）
    profile.schedule_profile_update(str(req.request_id), str(conv.conversation_id))
    return req, run, warnings


async def confirm(db: AsyncSession, conversation_id: str, user_id: str) -> ConfirmResponse:
    """确认需求档案并提交匹配（单端点，SC-22/25）。"""
    conv = await _load_conv(db, conversation_id)
    req, _run, warnings = await _do_confirm(db, conv)
    return ConfirmResponse(request_id=str(req.request_id), version=req.version,
                           redirect_to=f"/buyer/matches/{req.request_id}", warnings=warnings)


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
