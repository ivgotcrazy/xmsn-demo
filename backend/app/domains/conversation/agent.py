"""对话 Agent 核心（代理详细设计 v2 8/9 章）：意图路由 / 推理节点(Tool Calling) / 合并与修剪 / 完成判定 / 追问。

路径A（评审确认 2026-08-13）：意图 = f(话语, 状态, 历史, 阶段)。
- 意图路由 route_intent：确定性层**只拦无歧义命令**（option_click/confirm/help/accept·decline·skip_recommend[状态条件]）
- 弱收尾/引导(B·C)/推荐(SC-05)/答疑 → 推理节点在完整上下文中判定（classify_turn 结构化 intent）
- 推理节点 agent_reasoning：双工具（update_requirement_slots + classify_turn）一次推断 reply_text + slot_delta + intent
- B/C 合规后置保险 guide_override_for（正文强制引导，不参与主路由）
- reconcile 状态修剪（依赖/级联清理）+ 动态 Validator（hard/soft/optional）+ pending_slots 追问
- 熔断 _stall_counter：连续无进展换方式/引导人工
"""
from __future__ import annotations

import json
import logging
import re

from app.domains.conversation import schema as req_schema
from app.domains.conversation.schema import SlotTriState
from app.llm.client import chat, chat_tool

logger = logging.getLogger("xmsn.agent")

EXTRACT_PROMPT = """你是需脉AI选型助手的意图解析器。用户正在描述代工需求（可能是补充、纠正或排除某项能力）。
请从用户消息中提取/更新需求槽位。规则：仅在消息明确提到的槽位才输出；对已有值：补充则合并、纠正则覆盖、
排除（如"不要XX""排除XX""不要求XX"）则标记 excluded；无法确定的语义放 extra_constraints；不要编造。
可参考行业背景知识做出更专业的槽位值归一（如别名→标准名）。

# 槽位 Schema（当前品类：{category}）
{fields}

{knowledge}

# 当前用户画像（历史需求偏好，引导用；可据此不重复询问已知信息）
{user_profile}
# 输出 JSON（严格，只含本次变更）
{{
  "slot_delta": {{
    "os": {{"value": ["Linux", "Android"], "state": "set"}},
    "interfaces": {{"value": [], "state": "excluded"}},
    "moq": {{"value": 5000, "state": "set"}}
  }},
  "extra_constraints": ["外壳黑色"]
}}

# 纠正规则：若用户是纠正已有值（如"改成XX""不对，是XX"），对该字段输出 "merge": "replace"（覆盖旧值）；
# 否则默认追加合并（多选去重）。排除（"不要XX"）用 state=excluded。

# 用户消息
{message}
"""

# 完成态 confirm / 开放引导文案（统一"确认并提交匹配"标签 + 开放引导）
CONFIRM_TEXT = "核心需求已明确，确认并提交匹配？还是继续补充？"
OPEN_GUIDE_TEXT = "好的，您还想补充什么？例如工艺、外观、预算、包装等，直接告诉我；或点「确认并提交匹配」结束。"

# 继续补充的短填充语（完成态下直接开放引导，跳过 LLM）
_CONTINUATION = ("还有", "继续", "还要", "补充", "其他", "别的", "再来")

# 强命令（明确授权直接提交，SC-22）
CONFIRM_COMMANDS = ("确认并提交匹配", "确认并提交", "提交匹配", "提交需求", "完成需求", "确认完成")

# B/C 档合规安全覆盖模式（后置保险，不参与主路由；SC-29/34/35）
_REDIRECT_PAT = re.compile(
    r"哪家|谁(更好|合适|能|比)|更好|更合适|对比|比一下|比较|"
    r"推荐.{0,6}(厂商|厂家|家)|这家|那家|A厂|B厂|上面.{0,4}(厂|家)|"
    r"结果.{0,4}(好|准)|几个厂商", re.I)
_OFFTOPIC_PAT = re.compile(
    r"^(你好|您好|在吗|在不在|你是(谁|什么)|今天天气|你会做|你能做|介绍一下你|"
    r"讲个笑话|什么是物联网|人工智能趋势)", re.I)
# 明确"看结果"信号（结果查看 → 引导，合规兜底）
_RESULT_VIEW_PAT = ("看结果", "匹配结果", "结果呢", "结果怎么样", "查结果")

# SC-05 顾问反推：采纳/拒绝/跳过建议（仅 _recommend 存在时的状态条件命令）
ACCEPT_RECOMMEND_PAT = ("按建议", "采纳", "按推荐", "就按你说的", "按你说的", "按这个")
# 行业默认配置（无画像/知识时给 grounded 建议值；L2 SC-05）
_CATEGORY_DEFAULTS: dict[str, dict] = {
    "机顶盒": {"os": ["Linux"], "interfaces": ["网口", "HDMI"], "certifications": ["CE"],
               "moq": 5000, "lead_time_days": 30, "decode_capability": ["H.265"],
               "soc_platform": "Amlogic", "wireless": ["WiFi"]},
    "智能音箱": {"os": ["Linux"], "interfaces": ["WiFi", "蓝牙"], "certifications": ["CE"],
                "mic_array": "4麦", "speaker_power": "5W", "wireless": ["WiFi", "蓝牙"]},
    "IoT设备": {"os": ["RTOS"], "interfaces": ["WiFi"], "certifications": ["CE"],
                "comm_protocol": ["WiFi"], "power_supply": "电池", "ip_rating": "无"},
}
# 画像维度名 → 槽位 key（build_profile_context 输出 "维度名:值1、值2；…"）
_PROFILE_DIM_MAP = {"os": "偏好操作系统", "interfaces": "常用接口", "certifications": "常备认证", "product_type": "行业焦点"}


def is_continuation(text: str) -> bool:
    """是否"想继续补充"的短填充语 → 完成态下直接开放引导（省一次 LLM 调用）。"""
    t = text.strip()
    return 0 < len(t) <= 8 and any(w in t for w in _CONTINUATION)


def route_intent(message: str | None, clicked_option: str | None, state: dict) -> str:
    """意图路由（路径A，评审确认 2026-08-13）：只拦**无歧义命令**；弱收尾/引导(B·C)/推荐(SC-05)/答疑
    由推理节点在完整上下文中判定（intent 结构化输出）。

    返回：option_click / confirm_command / help / accept_recommend / decline_recommend / skip_current / free_text
    """
    if clicked_option:
        return "option_click"
    if message is None:
        return "confirm_command"
    m = message.strip()
    if not m:
        return "free_text"
    # 强命令（明确授权）→ 直接提交（SC-22/25）
    if re.match(r"^/done$", m, re.I) or any(c in m for c in CONFIRM_COMMANDS):
        return "confirm_command"
    if m in ("帮助", "help", "?") or m.startswith("/help"):
        return "help"
    # 采纳/拒绝/跳过建议（仅 _recommend 存在时的状态条件命令，无歧义）
    if state.get("_recommend"):
        if any(w in m for w in ACCEPT_RECOMMEND_PAT):
            return "accept_recommend"
        if m in ("我自己定", "我自己选", "我自己说"):
            return "decline_recommend"
        if m in ("跳过", "先不填", "不限"):
            return "skip_current"
    # 其余一律 free_text → 推理节点（语义由上下文中判定，不按关键词分流）
    return "free_text"


def guide_override_for(text: str) -> str | None:
    """B/C 合规后置保险（不参与主路由）：原文强命中厂商/结果/闲聊 → 强制引导，防模型越界评价厂商。"""
    if _REDIRECT_PAT.search(text) or any(w in text for w in _RESULT_VIEW_PAT):
        return "guide_result"
    if _OFFTOPIC_PAT.match(text):
        return "guide_back"
    return None


def guide_to_results(category: str | None = None) -> str:
    """SC-26/27：厂商/结果 → 引导去匹配详情（不代答、不评价）。"""
    return "匹配结果请到「匹配详情」页查看参数判定与原文溯源；我这边可以继续帮您补充需求。"


def guide_back(category: str | None = None) -> str:
    """SC-28~35：无关/闲聊 → 守门拉回主线。"""
    c = category or "您的"
    return f"我们专注于帮您梳理{c}代工需求，继续吧。"


def _fmt_val(v) -> str:
    if isinstance(v, list):
        return "、".join(str(x) for x in v)
    return str(v)


def _extract_profile_vals(profile_ctx: str) -> dict[str, list[str]]:
    """从画像串（"维度名:值1、值2；…"）提取各槽位偏好值。"""
    out: dict[str, list[str]] = {}
    if not profile_ctx:
        return out
    for slot_key, dim_name in _PROFILE_DIM_MAP.items():
        m = re.search(re.escape(dim_name) + r":([^；]+)", profile_ctx)
        if m:
            vals = [x.strip() for x in m.group(1).split("、") if x.strip()]
            if vals:
                out[slot_key] = vals
    return out


def build_recommendation(state: dict, profile_ctx: str = "") -> dict | None:
    """SC-05 顾问反推：为当前待填维度给建议值（画像 → 行业默认 → 枚举首项），grounded 不替用户决定。

    返回 {key, value, label, reason}；无待填（完成态）返回 None。
    """
    pt = _product_type(state)
    pvals = _extract_profile_vals(profile_ctx)
    if not pt:
        focus = (pvals.get("product_type") or ["机顶盒"])[0]
        return {"key": "product_type", "value": focus, "label": "产品类型",
                "reason": f"「{focus}」是您历史常关注的品类，且平台厂商资源较全"}
    nf = req_schema.next_slot(state, pt)
    if not nf:
        return None
    key, kind = nf["key"], nf.get("kind")
    suggested = None
    source = ""
    pv = pvals.get(key)
    if pv:
        suggested = pv if kind == "multi" else pv[0]
        source = "您历史需求偏好"
    else:
        dflt = _CATEGORY_DEFAULTS.get(pt, {}).get(key)
        if dflt is not None:
            suggested = dflt
            source = "该品类行业常见配置"
        elif nf.get("options"):
            suggested = [nf["options"][0]] if kind == "multi" else nf["options"][0]
            source = "行业常用选项"
    if suggested is None:
        return None
    reason = f"基于{source}，{nf['label']}建议选「{_fmt_val(suggested)}」" if source else ""
    return {"key": key, "value": suggested, "label": nf["label"], "reason": reason}


def write_option(state: dict, key: str, value) -> dict:
    """选项点击直写（确定性，三态 SET）。多选合并。"""
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    f = next((x for x in req_schema.fields_for(pt) if x["key"] == key), None)
    prev = (state.get(key) or {}).get("value") if state.get(key) else None
    if f and f["kind"] == "multi":
        combined = list(value) if isinstance(value, list) else [value]
        if isinstance(prev, list):
            for v in prev:
                if v not in combined:
                    combined.append(v)
        state[key] = {"value": combined, "state": SlotTriState.SET.value}
    else:
        state[key] = {"value": value, "state": SlotTriState.SET.value}
    return state


def merge_slot(state: dict, slot_delta: dict, extra: list[str] | None = None) -> dict:
    """三态合并（LLD 6.4）：delta 覆盖/合并当前。

    - 排除（EXCLUDED）→ 置排除（负向过滤）
    - 多选：merge=replace 覆盖旧值（纠正）；默认 append 去重追加
    - 自创字段（不在当前品类 Schema）→ 归入 extra_constraints（UC-10），不入固定槽位
    """
    cur_pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    d_pt = (slot_delta or {}).get("product_type")
    delta_pt = d_pt.get("value") if isinstance(d_pt, dict) else None
    pt = delta_pt or cur_pt  # 同一条消息同时给品类+扩展字段时，按新品类校验合法 key
    valid_keys = {f["key"] for f in req_schema.fields_for(pt)} | {"product_type", "extra_constraints"}
    for key, sv in (slot_delta or {}).items():
        if not isinstance(sv, dict):
            continue
        if key not in valid_keys:
            # UC-10：LLM 自创字段 → 归入 extra_constraints 或丢弃
            v = sv.get("value")
            if v not in (None, [], ""):
                vals = v if isinstance(v, list) else [v]
                state["extra_constraints"] = list(dict.fromkeys(
                    state.get("extra_constraints", []) + [str(x) for x in vals]))
            continue
        st = sv.get("state", SlotTriState.SET.value)
        val = sv.get("value")
        if st == SlotTriState.EXCLUDED.value:
            # 保留被排除的值（负向硬过滤用，匹配详细设计 4.5）
            state[key] = {"value": val, "state": SlotTriState.EXCLUDED.value}
        elif st == SlotTriState.WILDCARD.value:
            state[key] = {"value": None, "state": SlotTriState.WILDCARD.value}
        else:
            prev = (state.get(key) or {}).get("value")
            if isinstance(val, list):
                if sv.get("merge", "append") == "replace":
                    combined = list(val)  # 纠正：覆盖旧值
                else:
                    combined = list(val)
                    if isinstance(prev, list):
                        for v in prev:
                            if v not in combined:
                                combined.append(v)
                state[key] = {"value": combined, "state": SlotTriState.SET.value}
            else:
                state[key] = {"value": val, "state": SlotTriState.SET.value}
    if extra:
        state["extra_constraints"] = list(dict.fromkeys(state.get("extra_constraints", []) + extra))
    return state


def _fields_prompt(product_type: str | None) -> str:
    lines = []
    for f in req_schema.fields_for(product_type):
        if f.get("optional"):
            continue
        opts = f" 枚举: {'/'.join(f['options'])}" if f.get("options") else ""
        lines.append(f"- {f['key']}（{f['label']}，{f['kind']}）{opts}")
    return "\n".join(lines)


async def extract_slots(state: dict, message: str, db=None, meta: dict | None = None) -> dict:
    """自由文本 → LLM 解析 slot_delta + extra_constraints（LLD 2.3 extract_slots）。

    db 提供时注入领域知识（T3.4 RAG，第 4 区块）并记录 LLM 调用事实（T3.3 llm_call_logs）；
    检索失败静默降级（不阻塞对话）。meta 可带 conversation_id/turn（事实数据用）。
    """
    product_type = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    knowledge = ""
    if db is not None:
        try:
            from app.domains.conversation.retriever import build_knowledge_section, build_rag_query, retrieve
            hits = await retrieve(db, build_rag_query(state), product_type)
            knowledge = build_knowledge_section(hits)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rag inject failed (降级): %s", exc)
    prompt = EXTRACT_PROMPT.format(
        category=product_type or "未定",
        fields=_fields_prompt(product_type),
        knowledge=knowledge or "（无）",
        user_profile=(meta or {}).get("user_profile") or "（无）",
        message=message[:2000],
    )
    import time as _time
    from app.core.config import settings as _settings
    from app.db.models import LlmCallLog
    t0 = _time.perf_counter()
    raw = ""
    usage: dict = {}
    ok = False
    try:
        raw, usage = await chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=512,
                                with_usage=True)
        data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
        ok = True
        return {
            "slot_delta": data.get("slot_delta", {}),
            "extra_constraints": data.get("extra_constraints", []),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("extract_slots failed: %s", exc)
        return {"slot_delta": {}, "extra_constraints": []}
    finally:
        if db is not None:
            try:
                db.add(LlmCallLog(
                    conversation_id=(meta or {}).get("conversation_id"),
                    turn=(meta or {}).get("turn"),
                    task="extract_slots",
                    input_full={"prompt": prompt},
                    output_raw={"raw": raw[:4000]},
                    model=_settings.deepseek_model,
                    latency_ms=int((_time.perf_counter() - t0) * 1000),
                    tokens=usage,
                    status="ok" if ok else "error",
                ))
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("llm_call_log write failed: %s", exc)


def _product_type(state: dict) -> str | None:
    return (state.get("product_type") or {}).get("value") if state.get("product_type") else None


def completion_ready(state: dict) -> bool:
    """完成判定（动态 Validator 9.3）：active 且 hard 约束 100% 覆盖。"""
    return req_schema.validate_completion(state, _product_type(state))["done"]


def decide_question(state: dict) -> tuple[str | None, str, list[str]]:
    """返回 (追问字段 key|None, 文案, 选项)；完成则 None + 确认/开放引导；熔断触发给换方式话术。"""
    pt = _product_type(state)
    # 熔断：连续无进展 ≥3 轮 → 换方式/引导人工（SC-37/38/33）
    if state.get("_stall_counter", 0) >= 3:
        return None, stall_text(), ["确认并提交匹配", "继续补充"]
    if not pt:
        f = req_schema.FIXED_FIELDS[0]  # product_type
        return "product_type", f"请告诉我您需要找什么类型的代工厂？", list(f.get("options", []))
    verdict = req_schema.validate_completion(state, pt)
    if verdict["done"]:
        # 仅首次提示确认；再次进入完成态 → 开放引导（不再重复 confirm）
        if state.get("_confirm_prompted"):
            return None, OPEN_GUIDE_TEXT, ["确认并提交匹配", "继续补充"]
        state["_confirm_prompted"] = True
        return None, CONFIRM_TEXT, ["确认并提交匹配", "继续补充"]
    nf = req_schema.next_slot(state, pt)
    if not nf:
        return None, OPEN_GUIDE_TEXT, ["确认并提交匹配", "继续补充"]
    opts = list(nf.get("options", []))
    level = nf.get("level", req_schema.LEVEL_SOFT)
    prefix = "（可选）" if level == req_schema.LEVEL_OPTIONAL else ""
    question = f"{prefix}请问您需要哪些{nf['label']}？" if nf["kind"] == "multi" else f"{prefix}请填写{nf['label']}："
    return nf["key"], question, opts


# ---- 代理详细设计 v2 8/9：推理节点 / 状态修剪 / 引导模板 ----

_MD_PAT = re.compile(r"(\*\*|__|`|#{1,6}\s*|^\s*\d+[\.、]|\* |\- )", re.M)


def _clean_text(s: str, limit: int = 150) -> str:
    """文本卫生：去 markdown 标记、折叠空白、限长（答疑/引导/建议正文统一用）。"""
    if not s:
        return ""
    t = _MD_PAT.sub("", s)
    t = " ".join(t.split()).strip()
    return t[:limit]


# 非填槽轮意图分类工具（路径A：语义判定下沉推理节点）
CLASSIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "classify_turn",
        "description": "当用户本轮**没有给出可写入的需求槽位信息**，而是：领域答疑(qa)、询问厂商/匹配结果(guide_result)、"
                       "闲聊/无关(guide_back)、要收尾(weak_close)、拿不定主意要推荐(recommend) 时调用，给出意图与一句话回复。"
                       "若用户在填槽（给了明确槽位值）——即使同时有收尾/闲聊成分（如「就这样吧，接口加个USB」），"
                       "也请调用 update_requirement_slots，不要调用本工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {"type": "string",
                           "enum": ["qa", "guide_result", "guide_back", "weak_close", "recommend"]},
                "reply_text": {"type": "string",
                               "description": "给用户的一句话回复（答疑/引导/复述/建议，限150字，勿用markdown标记）"},
            },
            "required": ["intent", "reply_text"],
        },
    },
}


def build_tool_schema(active_fields: list[dict]) -> dict:
    """allowed_set → update_requirement_slots 的 tool JSON Schema（设计 9.4 + __states__ 三态）。"""
    props: dict = {}
    for f in active_fields:
        key = f["key"]
        if f.get("kind") == "multi":
            p: dict = {"type": "array", "items": {"type": "string"}}
            if f.get("options"):
                p["items"]["enum"] = f["options"]
        elif f.get("kind") == "number":
            p = {"type": "integer"}
        else:
            p = {"type": "string"}
            if f.get("options"):
                p["enum"] = f["options"]
        props[key] = p
    props["extra_constraints"] = {"type": "array", "items": {"type": "string"},
                                  "description": "用户提出的未预定义维度（如'外壳黑色'）"}
    props["__states__"] = {"type": "object",
                           "description": "三态覆盖（仅出现时才写）：{'<key>':'excluded'} 排除某能力、"
                                          "{'<key>':'wildcard'} 不限；未出现 = 正常指定 set。"}
    return {
        "type": "function",
        "function": {
            "name": "update_requirement_slots",
            "description": "更新用户代工需求槽位。仅在用户明确提到时才写；纠正（改成/不对）覆盖旧值；"
                           "排除（不要X）把值写入该槽位并在 __states__ 标记 excluded；不限/跳过 → __states__ 标 wildcard；"
                           "无法归入固定槽位的归入 extra_constraints。不要编造。",
            "parameters": {"type": "object", "properties": props, "required": []},
        },
    }


def _render_slots(state: dict) -> str:
    lines = []
    for k, sv in state.items():
        if k.startswith("_") or not isinstance(sv, dict) or "state" not in sv:
            continue
        st = sv["state"]
        v = sv.get("value")
        val = "、".join(v) if isinstance(v, list) else v
        lines.append(f"- {k}: state={st}, value={val}")
    return "\n".join(lines) if lines else "（无）"


def _allowed_lines(active_fields: list[dict]) -> str:
    lines = []
    for f in active_fields:
        opts = " /".join(f.get("options", []))
        lines.append(f"- {f['key']}（{f['label']}，{f.get('level')}）{opts}")
    return "\n".join(lines) if lines else "（无）"


async def agent_reasoning(state: dict, message: str, db=None, meta: dict | None = None) -> dict:
    """推理节点（④）：一次推断 reply_text + tool_call(slot_delta/extra) + intent（Tool Calling）。

    返回 {reply_text, slot_delta, extra_constraints, intent, has_tool}；
    intent: extract（有槽位）/ qa·guide_result·guide_back·weak_close·recommend（classify_turn 结构化判定）/
           empty（异常/空）。reply_text 已去 markdown 并限长。
    """
    import time as _time
    from app.core.config import settings as _settings
    from app.db.models import LlmCallLog

    pt = _product_type(state)
    active = req_schema.active_fields(state, pt)
    if not pt:
        # 品类未定时放行全部品类扩展字段（SC-04 一次给全含扩展字段）；merge 后 reconcile 修剪失效品类字段
        all_ext: list[dict] = []
        for cat_fields in req_schema.CATEGORY_EXTENSIONS.values():
            all_ext.extend(cat_fields)
        active = active + all_ext
    nf = req_schema.next_slot(state, pt)
    tool = build_tool_schema(active)

    knowledge = ""
    if db is not None:
        try:
            from app.domains.conversation.retriever import build_knowledge_section, build_rag_query, retrieve
            hits = await retrieve(db, build_rag_query(state), pt)
            knowledge = build_knowledge_section(hits)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rag inject failed (降级): %s", exc)

    next_hint = f"{nf['label']}" if nf else "（无，可围绕当前需求自然收尾）"
    sys_prompt = (
        "你是需脉AI选型助手，专注 B2B 代工制造需求萃取。\n"
        f"当前品类：{pt or '未定'}\n"
        f"本轮建议追问维度：{next_hint}（你可围绕它自然提问；若用户已提供其他合法槽位也可顺带写入）\n"
        "# 当前可填槽位（allowed_set）\n" + _allowed_lines(active) + "\n"
        "# 当前已填槽位（三态）\n" + _render_slots(state) + "\n"
        "# 工具选择规则\n"
        "A. 用户本轮给出了明确槽位信息（含补充/纠正/排除/不限）→ 调用 update_requirement_slots 写入；可在正文给简短回执。\n"
        "B. 用户本轮没有槽位信息，而是：\n"
        "   - 领域知识提问（Linux与Android区别等）→ classify_turn(intent=qa)，正文≤3~5句、可注明「依据：…」、末尾引导回槽位；\n"
        "   - 询问厂商比较/推荐厂商/查匹配结果 → classify_turn(intent=guide_result)，正文不评价厂商；\n"
        "   - 闲聊/与需求无关 → classify_turn(intent=guide_back)，正文礼貌拉回；\n"
        "   - 表示收尾（就这样吧/差不多了）→ classify_turn(intent=weak_close)；\n"
        "   - 拿不定主意要推荐（你推荐/随便/不知道选什么）→ classify_turn(intent=recommend)，正文说明想推荐的方向。\n"
        "C. 无论是否调用工具，都要在正文（reply_text 或 content）给出一句简短自然回应，勿用 markdown 标记。\n"
        "D. 若用户**同时**给出槽位信息和提问/推荐请求（如「放在家庭中使用，你推荐什么工艺？」）→ "
        "可同时调用 update_requirement_slots（写入槽位，如 application_scenario=家庭）和 classify_turn（回答问题）。\n"
        + (knowledge or "") + "\n"
        + ("# 当前用户画像\n" + ((meta or {}).get("user_profile") or "（无）") + "\n")
    )
    t0 = _time.perf_counter()
    raw_tool_calls: list[dict] = []
    raw_content = ""
    ok = False
    usage: dict = {}
    try:
        res = await chat_tool(
            [{"role": "system", "content": sys_prompt},
             {"role": "user", "content": message[:2000]}],
            [tool, CLASSIFY_TOOL], tool_choice="auto", temperature=0.1, max_tokens=1024,
        )
        raw_content = res.content
        raw_tool_calls = res.tool_calls
        usage = res.usage or {}
        ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("agent_reasoning failed: %s", exc)

    slot_delta: dict = {}
    extra: list[str] = []
    has_tool = False
    classify_intent: str | None = None
    classify_reply = ""
    allowed_keys = {f["key"] for f in active} | {"product_type"}
    kinds = {f["key"]: f.get("kind") for f in active}
    for tc in raw_tool_calls:
        name = tc["name"]
        args = tc["arguments"] or {}
        if name == "classify_turn":
            ci = args.get("intent")
            if ci in ("qa", "guide_result", "guide_back", "weak_close", "recommend"):
                classify_intent = ci
            cr = args.get("reply_text")
            if isinstance(cr, str) and cr.strip():
                classify_reply = cr.strip()
            continue
        if name != "update_requirement_slots":
            continue
        has_tool = True
        states = args.get("__states__") or {}
        for k, v in args.items():
            if k == "__states__":
                continue
            if k == "extra_constraints":
                ex = v if isinstance(v, list) else [v]
                extra = list(dict.fromkeys(str(x) for x in ex if x not in (None, "")))
                continue
            if k not in allowed_keys:
                # 自创/非法 key → 归 extra_constraints
                vals = v if isinstance(v, list) else [v]
                extra.extend(str(x) for x in vals if x not in (None, ""))
                continue
            st = states.get(k, "set")
            # 数字字段强转（模型常输出字符串 "5000" → int）
            if kinds.get(k) == "number" and not isinstance(v, int):
                try:
                    v = int(str(v).strip())
                except Exception:
                    v = v  # 保持原值，交由 merge/校验处理
            if st == "excluded":
                slot_delta[k] = {"value": v, "state": SlotTriState.EXCLUDED.value}
            elif st == "wildcard":
                slot_delta[k] = {"value": None, "state": SlotTriState.WILDCARD.value}
            else:
                slot_delta[k] = {"value": v, "state": SlotTriState.SET.value}
    extra = list(dict.fromkeys(extra))

    # 意图判定（路径A）：填槽 > 结构化分类 > 兜底
    if slot_delta:
        intent = "extract"
    elif classify_intent:
        intent = classify_intent
    elif raw_content.strip():
        intent = "qa"
    else:
        intent = "empty"

    # 正文卫生：优先 classify_turn 的 reply_text，其次模型 content
    reply_text = _clean_text(classify_reply or raw_content)

    if db is not None:
        try:
            db.add(LlmCallLog(
                conversation_id=(meta or {}).get("conversation_id"),
                turn=(meta or {}).get("turn"),
                task="agent_reasoning",
                input_full={"prompt": sys_prompt, "tools": [tool, CLASSIFY_TOOL]},
                output_raw={"content": raw_content[:2000], "tool_calls": raw_tool_calls[:5]},
                model=_settings.deepseek_model,
                latency_ms=int((_time.perf_counter() - t0) * 1000),
                tokens=usage,
                status="ok" if ok else "error",
            ))
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm_call_log write failed: %s", exc)

    return {"intent": intent, "reply_text": reply_text, "slot_delta": slot_delta,
            "extra_constraints": extra, "has_tool": has_tool}


def reconcile(state: dict) -> dict:
    """⑤ 状态修剪：Schema 依赖/级联清理（确定性）——失效依赖/旧品类扩展字段清空。"""
    pt = _product_type(state)
    active_keys = {f["key"] for f in req_schema.active_fields(state, pt)}
    for key in list(state.keys()):
        if key.startswith("_"):
            continue
        if key in ("product_type", "extra_constraints"):
            continue
        if key not in active_keys:
            del state[key]
    return state


def weak_close_recap(state: dict) -> str:
    """SC-22b：档案摘要 + 高亮缺项 + 引导确认（不直接提交）。"""
    pt = _product_type(state)
    verdict = req_schema.validate_completion(state, pt)
    parts = []
    for f in req_schema.active_fields(state, pt):
        sv = state.get(f["key"])
        if sv and sv.get("state") == SlotTriState.SET.value and sv.get("value") not in (None, [], ""):
            v = sv["value"]
            parts.append(f"{f['label']}={'、'.join(v) if isinstance(v, list) else v}")
    extras = state.get("extra_constraints", [])
    if extras:
        parts.append(f"扩展需求={'、'.join(extras)}")
    missing = [req_schema.label_of(k, pt) for k in verdict["missing_hard"]]
    summary = "好的，当前需求档案：" + ("；".join(parts) if parts else "（空）")
    if missing:
        summary += f"。还差：{'、'.join(missing)}"
    summary += "。确认并提交匹配，还是继续补充？"
    return summary


def help_text() -> str:
    """SC-32：能力说明 + 拉回。"""
    return ("我可以帮您梳理代工需求：产品类型、操作系统、接口、认证、起订量、交期、预算等；"
            "也可以解答与选型相关的领域问题（如 Linux 与 Android 区别）。请告诉我您的需求。")


def stall_text() -> str:
    """熔断：换方式 / 引导人工（SC-37/38/33）。"""
    return ("看起来我有些没跟上您的需求。要不换种方式描述？例如直接说'我要做5000台机顶盒，Linux系统'；"
            "或者联系人工客服继续。")
