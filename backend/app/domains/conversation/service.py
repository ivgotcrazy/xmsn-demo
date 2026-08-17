"""会话服务（T3.2/T3.5）：start/message/confirm + 快照 + match_runs + 逻辑删除。

- 一会话一产品：会话标题 = 聚焦产品类型（未确定时「新会话」）
- message 编排：选项精确命中 → 确定性直写；否则 LLM 解析 → merge_slot 三态合并
- 确认并提交匹配（单端点 confirm）：生成 customer_requests 快照（version 递增）+ match_runs（running）+ 异步画像
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
from app.db.models import Conversation, ConversationEvent, CustomerRequest, MatchRun
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
    """current_slots → 前端「当前需求」需求点集合（D5：需求点实例；label 由品类 Schema；strictness 两档 D7）。"""
    pts: list[DemandPoint] = []
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    for f in req_schema.fields_for(pt):
        sv = state.get(f["key"])
        if sv and sv.get("value") is not None:
            v = sv["value"]
            if isinstance(v, list) and len(v) == 0:
                continue
            if isinstance(v, list):
                v = [str(x) for x in v]
            else:
                v = str(v)
            pts.append(DemandPoint(key=f["key"], label=f["label"], value=v,
                                   strictness=sv.get("strictness", "best-effort"), confidence=1.0))
    for e in state.get("extended", []) or []:
        pts.append(DemandPoint(key="extended", label=e.get("label") or e.get("value") or "扩展需求",
                               value=str(e.get("value", "")),
                               strictness=e.get("strictness", "best-effort"), confidence=0.9))
    return pts


def _title_of(state: dict) -> str:
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    return str(pt) if pt else "新会话"


def _is_empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, list):
        return len(v) == 0
    return str(v).strip() == ""


def _slots_pure(state: dict) -> dict:
    """需求点 → 纯值 dict（兼容旧快照读取；新快照用 _slots_snapshot）。"""
    out: dict = {}
    for k, sv in state.items():
        if k.startswith("_") or k == "extended":
            continue
        if isinstance(sv, dict) and sv.get("value") is not None:
            out[k] = sv["value"]
    if state.get("extended"):
        out["extended"] = list(state["extended"])
    return out


def _slots_snapshot(state: dict) -> dict:
    """正向点快照（structured_demand 落库，对齐 AI核心 §9 契约：D6/D7/D8）。

    {schema_ref, dimensions: {key: {value, strictness}}, extended: [{label, value, strictness}], version}
    只存明确指定的需求点（value 非空）；wildcard/排除不落档（D6）。
    """
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    num_keys = {f["key"] for f in req_schema.fields_for(pt) if f.get("value_type") == "number"}
    dims: dict = {}
    for k, sv in state.items():
        if k.startswith("_") or k == "extended":
            continue
        if isinstance(sv, dict) and not _is_empty(sv.get("value")):
            val = sv.get("value")
            # 需求侧归一（兜底）：数字槽位值确保为 int（兼容历史/边缘字符串值，如"1000台"）
            if k in num_keys and not isinstance(val, (int, float)):
                _parsed = req_schema.normalize_number(val)
                if _parsed is not None:
                    val = _parsed
            dims[k] = {"value": val, "strictness": sv.get("strictness", "best-effort")}
    return {
        "schema_ref": req_schema.schema_ref_of(pt),
        "dimensions": dims,
        "extended": list(state.get("extended") or []),
        "version": 1,
    }


async def start(db: AsyncSession, user_id: str) -> ConversationStartResponse:
    # 首问即品类锚点：预置 _pending，使首个选项点击走确定性直写（v2.1 点击=确定性执行）
    conv = Conversation(user_id=uuid.UUID(user_id), title="新会话", status="active",
                        conversation_history=[],
                        current_slots={"_pending": {"key": "product_type",
                                                     "options": ["机顶盒", "智能音箱", "IoT设备"]}})
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    await _append_event(db, str(conv.conversation_id), "session_started", {"title": "新会话"})
    return ConversationStartResponse(
        conversation_id=str(conv.conversation_id),
        first_message=AssistantMessage(
            content="您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？",
            options=["机顶盒", "智能音箱", "IoT设备"],
            options_type="single",
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


async def _category_switch_block(
    db: AsyncSession, conv: Conversation, state: dict, history: list,
    turn: int, text: str, cur: str, new: str,
) -> MessageResponse:
    """SC-31 品类切换拦截：一会话一产品——不写槽位（保留现场），提示新建会话。"""
    content = (f"检测到您提到「{new}」，当前会话已聚焦「{cur}」，"
               f"如需咨询 {new} 建议新建会话。")
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": content, "options": [], "options_type": "none"})
    conv.current_slots = state
    conv.conversation_history = history
    await db.commit()
    await _append_event(db, str(conv.conversation_id), "category_conflict",
                        {"turn": turn, "cur": cur, "new": new})
    return MessageResponse(
        assistant_message=AssistantMessage(content=content, options=[], options_type="none"),
        demand_points=to_demand_points(state), title=conv.title,
    )


async def _non_extract_message(
    db: AsyncSession, conv: Conversation, state: dict, history: list,
    turn: int, text: str, intent: str, reply_text: str,
) -> MessageResponse:
    """v2.1 非填槽轮分流：按推理节点结构化 intent 处理（QA/引导/弱收尾/推荐）。

    合规（不评价厂商）= 指令约束 + 评测验证；无正则兜底（v2.1 删 guide_override_for）。
    """
    if intent == "guide_result":
        content = agent.guide_to_results(_title_of(state))
        evt, opts, otype = "redirect", [], "none"
    elif intent == "guide_back":
        content = agent.guide_back(_title_of(state))
        evt, opts, otype = "guard", [], "none"
    elif intent == "weak_close":
        content = agent.weak_close_recap(state)
        # 提交门槛（D12）：已达门槛（品类 + ≥1 需求点）才亮「提交匹配」，否则不展示动作按钮
        _pt = (state.get("product_type") or {}).get("value")
        _done = req_schema.validate_completion(state, _pt)["done"]
        opts = ["提交匹配"] if _done else []
        state["_pending"] = {"key": None, "options": opts}
        evt, otype = "recap", "actions" if _done else "none"
    elif intent == "recommend":
        profile_ctx = await profile.build_profile_context(db, str(conv.user_id))
        rec = agent.build_recommendation(state, profile_ctx)
        if not rec:
            # 无待填维度可给结构化建议（完成态/数字字段无默认/画像无值）→
            # 直接用模型已生成的自然语言建议 reply_text，勿丢弃；真无内容才算空轮计熔断
            content = reply_text or "好的，请继续补充您的需求。"
            opts = []
            state["_pending"] = {}
            evt, otype = ("recommend" if reply_text else "question"), "none"
            if not reply_text:
                _bump_stall(state, False)
        else:
            state["_recommend"] = {"key": rec["key"], "value": rec["value"]}
            val_s = agent._fmt_val(rec["value"])
            content = f"看您拿不定主意，我建议：{rec['label']}选「{val_s}」（{rec['reason']}）。要我按此填写吗？"
            opts = ["按建议填写", "我自己定"] + ([] if rec["key"] == "product_type" else ["跳过"])
            state["_pending"] = {"key": None, "options": opts}
            evt, otype = "recommend", "actions"
    else:  # qa / empty
        content = reply_text or "好的，请继续补充您的需求。"
        opts = []
        evt, otype = ("qa_answer" if intent == "qa" else "question"), "none"
        _bump_stall(state, False)

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": content, "options": opts, "options_type": otype})
    conv.current_slots = state
    conv.conversation_history = history
    await db.commit()
    await _append_event(db, str(conv.conversation_id), evt, {"turn": turn, "content": text[:300]})
    return MessageResponse(
        assistant_message=AssistantMessage(content=content, options=opts, options_type=otype),
        demand_points=to_demand_points(state), title=conv.title,
    )


async def message(db: AsyncSession, conversation_id: str, text: str, clicked_option=None) -> MessageResponse:
    """对话轮次（代理详细设计 v2 8 章，v2.1 收敛）：点击=确定性执行；自由文本→推理节点（三工具）→ 按结构化 intent 分流。"""
    conv = await _load_conv(db, conversation_id)
    state: dict = dict(conv.current_slots or {})
    history: list = list(conv.conversation_history or [])
    turn = len(history) + 1
    await _append_event(db, conversation_id, "user_message", {"turn": turn, "content": text[:500]})

    intent = agent.route_intent(text, clicked_option, state)
    if intent == "option_click":
        return await _handle_click(db, conv, state, history, turn, clicked_option, text)

    # ---- 自由文本 → 推理节点（三工具：填槽 / classify / submit；不做字符串匹配）----
    profile_ctx = await profile.build_profile_context(db, str(conv.user_id))
    rr = await agent.agent_reasoning(
        state, text, db=db,
        meta={"conversation_id": conversation_id, "turn": turn, "user_profile": profile_ctx},
    )
    rr_reply = rr["reply_text"].strip()

    # SC-31 一会话一产品：会话已聚焦品类 A，推理节点提出不同品类 B → 不覆盖、提示新建会话
    # （含提交意图一并拦截：换品类后提交属于新会话；语义判定在推理节点，此处执行不变式）
    conflict = agent.category_switch(state, rr["slot_delta"])
    if conflict:
        return await _category_switch_block(db, conv, state, history, turn, text, *conflict)

    state = agent.merge_slot(state, rr["slot_delta"], rr["extended"])
    parsed = {"slot_delta": rr["slot_delta"], "extended": rr["extended"]}

    # 提交意图（LLM 识别）→ 执行提交（护栏：品类锚点缺失禁止；缺项警示）
    if rr.get("submit_request"):
        return await _do_submit_from_message(db, conv, state, history, turn, text)

    # 非填槽轮 → 按结构化 intent 分流（QA/引导/弱收尾/推荐），本轮结束
    if rr.get("intent", "extract") != "extract":
        return await _non_extract_message(
            db, conv, state, history, turn, text, rr.get("intent", "empty"), rr_reply)

    progress = bool(rr["slot_delta"] or rr["extended"])
    slot_delta = parsed.get("slot_delta", {})
    new_extras = parsed.get("extended", [])

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
        summary += "扩展需求已记录：" + "、".join(
            (e.get("label") or e.get("value")) if isinstance(e, dict) else str(e) for e in new_extras)
    if slot_delta or new_extras:
        history.append({"role": "assistant", "content": summary, "options": []})

    # 下一追问 / 完成提示 / 熔断
    next_key, question, opts, otype = agent.decide_question(state)
    state["_pending"] = {"key": next_key, "options": opts} if next_key else {}

    # 混合意图/回执：有槽位且有 LLM 正文 → 正文 + 追问合并；有槽位但 LLM 无正文（只调工具）→
    # 用确定性回执 summary + 追问（避免"无回执复读模板"，红线1）
    body = rr_reply if rr_reply else (summary if (slot_delta or new_extras) else "")
    # D12：门槛达成时 question 为空（无引导句），气泡正文直接用需求回执/LLM 回执 + 按钮
    final_content = f"{body}\n\n{question}" if (body and question) else (body or question)

    title = _title_of(state)
    if conv.title == "新会话" and title != "新会话":
        conv.title = title

    history.append({"role": "assistant", "content": question, "options": opts, "options_type": otype})
    conv.current_slots = state
    conv.conversation_history = history
    await db.commit()
    if slot_delta:
        await _append_event(db, conversation_id, "slot_updated", {"turn": turn, "delta": slot_delta})
    await _append_event(db, conversation_id, "question", {"turn": turn, "question": question[:300], "options": opts})

    return MessageResponse(
        assistant_message=AssistantMessage(content=final_content, options=opts, options_type=otype),
        demand_points=to_demand_points(state),
        title=conv.title,
    )


async def _handle_click(
    db: AsyncSession, conv: Conversation, state: dict, history: list,
    turn: int, clicked_option, text: str,
) -> MessageResponse:
    """点击（UI 动作）→ 确定性执行（v2.1 红线6，不做文本匹配）：槽位直写 / 推荐采纳·拒绝·跳过 / 提交匹配（前端两步化确认框）。"""
    parsed = {"slot_delta": {}, "extended": []}
    # 1) SC-05 推荐选项（state._recommend 存在时）
    rec = state.get("_recommend")
    if rec:
        if clicked_option == "按建议填写":
            state.pop("_recommend", None)
            if rec.get("key"):
                state = agent.write_option(state, rec["key"], rec["value"])
                parsed = {"slot_delta": {rec["key"]: state[rec["key"]]}, "extended": []}
        elif clicked_option in ("我自己定", "我自己选", "我自己说"):
            state.pop("_recommend", None)
        elif clicked_option in ("跳过", "先不填", "不限"):
            state.pop("_recommend", None)
            _pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
            _nf = req_schema.next_slot(state, _pt)
            if _nf:
                # D6：不限/跳过 → 不写需求点（wildcard 不入档），降为 Agent 私有标记（不再追问）
                state["_confirmed_unlimited"] = list(dict.fromkeys(
                    state.get("_confirmed_unlimited", []) + [_nf["key"]]))
                parsed = {"slot_delta": {}, "extended": []}
    # 2) 槽位选项（pending.key 存在；多选=list，单选=str）
    elif (state.get("_pending") or {}).get("key"):
        pending = state["_pending"]
        sel = clicked_option if isinstance(clicked_option, list) else [clicked_option]
        valid = [o for o in sel if o in (pending.get("options") or [])]
        if valid:
            key = pending["key"]
            val = valid if len(valid) > 1 else valid[0]
            state = agent.write_option(state, key, val)
            parsed = {"slot_delta": {key: state[key]}, "extended": []}
    # 2') 品类锚点兜底（_pending 缺失时首个点击即品类，防御）
    elif not (state.get("product_type") or {}).get("value") and isinstance(clicked_option, str):
        state = agent.write_option(state, "product_type", clicked_option)
        parsed = {"slot_delta": {"product_type": state["product_type"]}, "extended": []}
    # 3) 未知点击（防御）→ 降级为自由文本走 LLM（防静默丢弃）
    else:
        return await message(db, str(conv.conversation_id), text, None)

    slot_delta = parsed.get("slot_delta", {})
    _bump_stall(state, bool(slot_delta))
    state = agent.reconcile(state)

    history.append({"role": "user", "content": text})
    summary = _delta_summary(slot_delta, state)
    if slot_delta:
        history.append({"role": "assistant", "content": summary, "options": []})

    next_key, question, opts, otype = agent.decide_question(state)
    state["_pending"] = {"key": next_key, "options": opts} if next_key else {}
    title = _title_of(state)
    if conv.title == "新会话" and title != "新会话":
        conv.title = title
    # D12：question 为空（无引导句）时用需求回执 summary 作气泡正文（有按钮承载动作）
    content = question or summary or ""
    history.append({"role": "assistant", "content": content, "options": opts, "options_type": otype})
    conv.current_slots = state
    conv.conversation_history = history
    await db.commit()
    if slot_delta:
        await _append_event(db, str(conv.conversation_id), "slot_updated", {"turn": turn, "delta": slot_delta})
    await _append_event(db, str(conv.conversation_id), "question", {"turn": turn, "question": (content or "")[:300], "options": opts})
    return MessageResponse(
        assistant_message=AssistantMessage(content=content, options=opts, options_type=otype),
        demand_points=to_demand_points(state), title=conv.title,
    )


async def _do_submit_from_message(
    db: AsyncSession, conv: Conversation, state: dict, history: list, turn: int, text: str,
) -> MessageResponse:
    """submit_request（LLM 识别提交意图）→ 执行提交（护栏：品类锚点缺失禁止；缺项警示 SC-25）。"""
    state = agent.reconcile(state)
    if not (state.get("product_type") or {}).get("value"):
        reply = AssistantMessage(content="请先明确要寻找的产品类型，才能提交匹配。", options=[])
        return MessageResponse(assistant_message=reply, demand_points=to_demand_points(state), title=conv.title)
    if not req_schema.validate_completion(state, (state.get("product_type") or {}).get("value"))["done"]:
        reply = AssistantMessage(content="还需补充需求点（如操作系统、认证、起订量等）才能提交匹配。", options=[])
        return MessageResponse(assistant_message=reply, demand_points=to_demand_points(state), title=conv.title)
    conv.current_slots = state  # 先持久化合并后的槽位，_do_confirm 快照取当前 state
    try:
        req, _run, warnings = await _do_confirm(db, conv)
    except Exception as exc:  # noqa: BLE001
        logger.warning("submit_request confirm failed: %s", exc)
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
    await _append_event(db, str(conv.conversation_id), "confirm",
                        {"turn": turn, "version": req.version, "request_id": str(req.request_id)})
    return MessageResponse(
        assistant_message=AssistantMessage(content=content, options=[]),
        demand_points=to_demand_points(state), title=conv.title,
        submitted=True, redirect_to=f"/customer/matches/{req.request_id}", warnings=warnings)


def _delta_summary(delta: dict, state: dict) -> str:
    """本轮需求点变化的自然语言回执（供历史气泡展示；正向点 + strictness，D7）。"""
    parts = []
    for k, sv in delta.items():
        if not isinstance(sv, dict):
            continue
        label = req_schema.label_of(k, (state.get("product_type") or {}).get("value") if state.get("product_type") else None)
        v = sv.get("value")
        if v in (None, [], ""):
            continue
        tag = "（必须）" if sv.get("strictness", "best-effort") == "strict" else ""
        parts.append(f"{label}{tag}已记录：{'、'.join(v) if isinstance(v, list) else v}")
    return "；".join(parts)


async def _next_version(db: AsyncSession, conversation_id: uuid.UUID) -> int:
    res = await db.execute(
        select(func.count()).select_from(CustomerRequest).where(CustomerRequest.conversation_id == conversation_id)
    )
    return int(res.scalar_one() or 0) + 1


async def _do_confirm(db: AsyncSession, conv: Conversation, demand_points=None) -> tuple[CustomerRequest, MatchRun, list[str]]:
    """确认提交（D7/D12）：两步化（确认框 strictness 可微调）+ 提交门槛校验。

    - 提交门槛（D12）：品类锚定 + 至少 1 个需求点（品类外 dimensions 或 extended 非空）→ 否则 400；
    - demand_points（可选，D7 两步化）：前端确认框回传的 strictness 微调，覆盖 Agent 判定；
    - 会话状态重新设计（第 10 章）：不再写 conv.status="confirmed"（提交是可重复事件，会话保持 active）。
    """
    state = dict(conv.current_slots or {})
    if not (state.get("product_type") or {}).get("value"):
        raise err_400("请先明确要寻找的产品类型")
    pt = (state.get("product_type") or {}).get("value")
    # D7 两步化：确认框可微调 strictness（前端回传覆盖）
    if demand_points:
        for dp in demand_points:
            sv = state.get(dp.key)
            if sv and dp.key != "extended":
                state[dp.key] = {**sv, "strictness": dp.strictness}
    if not req_schema.validate_completion(state, pt)["done"]:
        raise err_400("请补充需求点（如操作系统、认证、起订量等）后才能提交匹配")
    warnings: list[str] = []

    version = await _next_version(db, conv.conversation_id)
    req = CustomerRequest(
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


async def confirm(db: AsyncSession, conversation_id: str, user_id: str, demand_points=None) -> ConfirmResponse:
    """确认需求档案并提交匹配（单端点，SC-22/25；D7 两步化：demand_points 可微调 strictness）。"""
    conv = await _load_conv(db, conversation_id)
    req, _run, warnings = await _do_confirm(db, conv, demand_points)
    return ConfirmResponse(request_id=str(req.request_id), version=req.version,
                           redirect_to=f"/customer/matches/{req.request_id}", warnings=warnings)


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
            select(func.count()).select_from(CustomerRequest).where(
                CustomerRequest.conversation_id == c.conversation_id, CustomerRequest.deleted_at.is_(None)
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
        ConversationMessageItem(role=m["role"], content=m["content"], options=m.get("options", []),
                               options_type=m.get("options_type", "none"))
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
        select(CustomerRequest)
        .where(CustomerRequest.conversation_id == conv.conversation_id, CustomerRequest.deleted_at.is_(None))
        .order_by(CustomerRequest.version.asc())
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
    res = await db.execute(select(CustomerRequest).where(
        CustomerRequest.request_id == rid, CustomerRequest.conversation_id == conv.conversation_id
    ))
    req = res.scalar_one_or_none()
    if not req:
        raise err_404("需求档案不存在")
    req.deleted_at = datetime.utcnow()
    await db.commit()
    return {"id": request_id, "deleted": True, "deleted_at": req.deleted_at}
