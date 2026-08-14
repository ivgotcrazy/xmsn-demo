"""对话 Agent 核心（代理详细设计 v2 8/9 章，v2.1 收敛）：意图判定全在推理节点（LLM），程序只做执行。

v2.1（评审定案 2026-08-13）：
- 意图路由 route_intent：仅 `clicked_option ? option_click : free_text`；**不做任何字符串匹配**（红线6）
- 推理节点 agent_reasoning：**三工具**（update_requirement_slots / classify_turn / submit_request）一次推断
  reply_text + slot_delta + intent（extract/qa/guide_result/guide_back/weak_close/recommend/submit/empty）
- 提交 = UI 按钮（confirm 端点）或 submit_request（LLM 识别提交意图 → 程序执行 _do_confirm 带护栏）
- 合规（不评价厂商）= 指令约束 + 评测验证；无正则兜底（删 guide_override_for）
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

# v2.1：删除文本命令/正则常量（红线6，不做字符串匹配语义）——
# _CONTINUATION / CONFIRM_COMMANDS / _REDIRECT_PAT / _OFFTOPIC_PAT / _RESULT_VIEW_PAT / ACCEPT_RECOMMEND_PAT 已移除。
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


def route_intent(message: str | None, clicked_option: str | None, state: dict) -> str:
    """意图路由（v2.1 收敛，红线6）：仅区分**UI 动作** vs **自由文本**；不做任何字符串匹配。

    返回：option_click（点击=UI 动作，确定性执行） / free_text（一切自由文本 → 推理节点判定语义）
    """
    if clicked_option:
        return "option_click"
    return "free_text"


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
    """选项点击直写（确定性，三态 SET）。多选=整集合替换（checkbox 全量提交，可移除）。"""
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    f = next((x for x in req_schema.fields_for(pt) if x["key"] == key), None)
    if f and f["kind"] == "multi":
        # 多选：以本次选择为最终完整集合（不再追加旧值，支持取消勾选移除）
        state[key] = {"value": list(value) if isinstance(value, list) else [value],
                      "state": SlotTriState.SET.value}
    else:
        state[key] = {"value": value, "state": SlotTriState.SET.value}
    return state


def merge_slot(state: dict, slot_delta: dict, extra: list[str] | None = None) -> dict:
    """三态合并（LLD 6.4）：delta 覆盖/合并当前。

    - 排除（EXCLUDED）→ 置排除（负向过滤）
    - 多选：默认**整集合替换**（LLM 输出完整最终集，规则 A1）；`__merge__` 可覆盖为 append（补充）/ remove（移除项）
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
                # 多选默认 REPLACE（LLM 输出完整最终集）；__merge__ 覆盖为 append / remove
                m = sv.get("merge", "replace")
                if m == "append":
                    combined = list(val)
                    if isinstance(prev, list):
                        for v in prev:
                            if v not in combined:
                                combined.append(v)
                elif isinstance(m, dict) and "remove" in m:
                    removed = set(m["remove"])
                    combined = list(val)
                    if isinstance(prev, list):
                        for v in prev:
                            if v not in combined and v not in removed:
                                combined.append(v)
                else:  # replace：整字段替换为本次值
                    combined = list(val)
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


def decide_question(state: dict) -> tuple[str | None, str, list[str], str]:
    """返回 (追问字段 key|None, 文案, 选项, options_type)；完成则 None + 确认/开放引导；熔断触发给换方式话术。"""
    actions = ["确认并提交匹配", "继续补充"]
    pt = _product_type(state)
    # 熔断：连续无进展 ≥3 轮 → 换方式/引导人工（SC-37/38/33）
    if state.get("_stall_counter", 0) >= 3:
        return None, stall_text(), actions, "actions"
    if not pt:
        f = req_schema.FIXED_FIELDS[0]  # product_type
        return "product_type", f"请告诉我您需要找什么类型的代工厂？", list(f.get("options", [])), "single"
    verdict = req_schema.validate_completion(state, pt)
    if verdict["done"]:
        # 仅首次提示确认；再次进入完成态 → 开放引导（不再重复 confirm）
        if state.get("_confirm_prompted"):
            return None, OPEN_GUIDE_TEXT, actions, "actions"
        state["_confirm_prompted"] = True
        return None, CONFIRM_TEXT, actions, "actions"
    nf = req_schema.next_slot(state, pt)
    if not nf:
        return None, OPEN_GUIDE_TEXT, actions, "actions"
    opts = list(nf.get("options", []))
    level = nf.get("level", req_schema.LEVEL_SOFT)
    prefix = "（可选）" if level == req_schema.LEVEL_OPTIONAL else ""
    question = f"{prefix}请问您需要哪些{nf['label']}？" if nf["kind"] == "multi" else f"{prefix}请填写{nf['label']}："
    otype = "multi" if nf.get("kind") == "multi" else ("single" if opts else "none")
    return nf["key"], question, opts, otype


# ---- 代理详细设计 v2 8/9：推理节点 / 状态修剪 / 引导模板 ----

_MD_PAT = re.compile(r"(\*\*|__|`|#{1,6}\s*|^\s*\d+[\.、]|\* |\- )", re.M)


def _clean_text(s: str) -> str:
    """文本卫生：去 markdown 标记、折叠空白（答疑/引导/建议正文统一用）。

    不做长度截断——回复是否简短由提示词约束模型（v2.1 原则：大模型=大脑，程序只执行；
    截断会腰斩模型语义产出，属程序篡改模型输出；异常兜底后续再议）。
    """
    if not s:
        return ""
    t = _MD_PAT.sub("", s)
    return " ".join(t.split()).strip()


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
                               "description": "给用户的一句话回复（答疑/引导/复述/建议，简短3~5句、答完拉回主线，勿用markdown标记）"},
            },
            "required": ["intent", "reply_text"],
        },
    },
}


# 提交意图工具（v2.1：LLM 识别"要结束并提交" → 程序执行 _do_confirm 带护栏）
SUBMIT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_request",
        "description": "仅当用户明确表示要结束需求整理并提交匹配（如「确认并提交匹配」「可以提交了」「帮我提交吧」）时调用；"
                       "程序将生成需求档案快照并触发匹配。若用户只是在确认某个槽位值（如「确认接口要USB」），不要调用。",
        "parameters": {"type": "object", "properties": {}, "required": []},
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
    props["__merge__"] = {"type": "object",
                           "description": "多选字段覆盖语义（可选）：{'<key>':'append'} 追加（补充某项，保留旧值）；"
                                          "{'<key>':{'remove':['值1']}} 从当前移除指定项；缺省=整字段替换（输出完整集合）。"}
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

    返回 {reply_text, slot_delta, extra_constraints, intent, has_tool, submit_request}；
    intent: extract（有槽位）/ submit（submit_request）/ qa·guide_result·guide_back·weak_close·recommend（classify_turn 结构化判定）/
           empty（异常/空）。reply_text 已去 markdown 并折叠空白（不截断）。
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
        "A1. **多选字段（os/interfaces/certifications 等）**：纠正/重新声明/排除某项 → 输出**最终完整集合**整体替换——"
        "如「只要Android」→ os=['Android']；「把Linux去掉」且当前 ['Linux','Android'] → os=['Android']。"
        "补充/追加某项（如「再加RTOS」）→ 可仅给新增项并设 __merge__:{'<key>':'append'}（保留旧值）。"
        "务必：不遗漏已有值、不添加用户未提到的值。\n"
        "B. 用户本轮没有槽位信息，而是：\n"
        "   - 领域知识提问（Linux与Android区别等）→ classify_turn(intent=qa)，正文≤3~5句、可注明「依据：…」、末尾引导回槽位；\n"
        "   - 询问厂商比较/推荐厂商/查匹配结果 → classify_turn(intent=guide_result)，正文不评价厂商；\n"
        "   - 闲聊/与需求无关 → classify_turn(intent=guide_back)，正文礼貌拉回；\n"
        "   - 表示收尾（就这样吧/差不多了）→ classify_turn(intent=weak_close)；\n"
        "   - 拿不定主意要推荐（你推荐/随便/不知道选什么）→ classify_turn(intent=recommend)，正文说明想推荐的方向。\n"
        "C. 无论是否调用工具，都要在正文（reply_text 或 content）给出一句简短自然回应，勿用 markdown 标记。\n"
        "D. 若用户**同时**给出槽位信息和提问/推荐请求（如「放在家庭中使用，你推荐什么工艺？」）→ "
        "可同时调用 update_requirement_slots（写入槽位，如 application_scenario=家庭）和 classify_turn（回答问题）。\n"
        "E. 用户明确表示要结束并提交匹配（如「确认并提交匹配」「可以提交了」「帮我提交吧」）→ 调用 submit_request；"
        "勿与填槽混淆（「确认接口要USB」是确认槽位值，应调 update_requirement_slots）。\n"
        "F. **一会话一产品（SC-31）**：若「当前品类」已确定，而用户表达了**切换到另一产品类型**的意图"
        "（如当前机顶盒、改做智能音箱）→ 不要在 update_requirement_slots 里修改 product_type，也不写新品类专属字段；"
        "正文用引导语提示：检测到您提到「新品类」，当前会话已聚焦「原品类」，如需咨询新品类建议新建会话。\n"
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
            [tool, CLASSIFY_TOOL, SUBMIT_TOOL], tool_choice="auto", temperature=0.1, max_tokens=1024,
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
    submit_request = False
    classify_intent: str | None = None
    classify_reply = ""
    allowed_keys = {f["key"] for f in active} | {"product_type"}
    kinds = {f["key"]: f.get("kind") for f in active}
    for tc in raw_tool_calls:
        name = tc["name"]
        args = tc["arguments"] or {}
        if name == "submit_request":
            submit_request = True
            continue
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
        merges = args.get("__merge__") or {}
        for k, v in args.items():
            if k in ("__states__", "__merge__"):
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
                mg = merges.get(k)
                slot_delta[k] = {"value": v, "state": SlotTriState.SET.value,
                                 **({"merge": mg} if mg else {})}
    extra = list(dict.fromkeys(extra))

    # 意图判定（v2.1）：填槽 > 提交 > 结构化分类 > 兜底
    if slot_delta:
        intent = "extract"
    elif submit_request:
        intent = "submit"
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
                input_full={"prompt": sys_prompt, "tools": [tool, CLASSIFY_TOOL, SUBMIT_TOOL]},
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
            "extra_constraints": extra, "has_tool": has_tool, "submit_request": submit_request}


def category_switch(state: dict, slot_delta: dict) -> tuple[str, str] | None:
    """SC-31 一会话一产品：会话已聚焦品类 cur，推理节点提出不同品类 new → 返回 (cur, new)。

    语义判定由推理节点完成（slot_delta.product_type 是其结构化输出）；此处仅执行不变式——
    不覆盖品类、不写入新品类扩展字段，提示新建会话（产品原型设计 02A 关键交互⑥）。
    None = 无冲突（正常填槽）。
    """
    cur = _product_type(state)
    if not cur:
        return None
    d_pt = (slot_delta or {}).get("product_type")
    new = d_pt.get("value") if isinstance(d_pt, dict) else None
    if not new or new == cur:
        return None
    return (cur, new)


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
