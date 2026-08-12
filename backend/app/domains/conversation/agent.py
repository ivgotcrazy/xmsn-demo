"""对话 Agent 核心（T3.3）：意图路由 / 槽位合并 / 完成判定 / 追问。

实现以《代理详细设计》LLD v1.1 为准（2 章状态机 / 0.4 完成判定）：
- 选项点击确定性直写；自由文本 LLM 解析 → merge_slot 三态合并（补充/纠正/排除）
- 完成判定双通道：品类锚点（product_type）+ 关键维度（os/interfaces/certifications）
- 追问顺序来自需求 Schema（固定 + 品类扩展）
"""
from __future__ import annotations

import json
import logging
import re

from app.domains.conversation import schema as req_schema
from app.domains.conversation.schema import SlotTriState
from app.llm.client import chat

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

# 完成态 confirm / 开放引导文案（继续补充去重 + 开放引导）
CONFIRM_TEXT = "核心需求已明确，确认完成？还是继续补充？"
OPEN_GUIDE_TEXT = "好的，您还想补充什么？例如工艺、外观、预算、包装等，直接告诉我；或点「确认完成」结束。"

# 继续补充的短填充语（完成态下直接开放引导，跳过 LLM）
_CONTINUATION = ("还有", "继续", "还要", "补充", "其他", "别的", "再来")


def is_continuation(text: str) -> bool:
    """是否"想继续补充"的短填充语 → 完成态下直接开放引导（省一次 LLM 调用）。"""
    t = text.strip()
    return 0 < len(t) <= 8 and any(w in t for w in _CONTINUATION)


def route_intent(message: str | None, clicked_option: str | None, state: dict) -> str:
    """意图分类（LLD 2.2）：option_click / confirm / done / help / free_text。"""
    if clicked_option:
        return "option_click"
    if message is None:
        return "confirm"
    m = message.strip()
    if re.match(r"^/done$", m, re.I) or "完成需求" in m or "就这样" in m or "可以了" in m:
        return "done"
    if "确认" in m and state.get("product_type"):
        return "confirm"
    if m in ("帮助", "help", "?") or m.startswith("/help"):
        return "help"
    return "free_text"


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
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
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


def completion_ready(state: dict) -> bool:
    """完成判定（LLD 0.4 prompt_on_anchor_and_key）：锚点 + 关键维度已覆盖。"""
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    if not pt:
        return False
    field_keys = [f["key"] for f in req_schema.fields_for(pt)]
    for d in req_schema.KEY_DIMS:
        if d in field_keys:
            sv = state.get(d)
            if not sv or sv.get("state") != SlotTriState.SET.value or not sv.get("value"):
                return False
    return True


def decide_question(state: dict) -> tuple[str | None, list[str]]:
    """返回下一个追问（字段 key + 文案）与选项；完成则返回 None。"""
    pt = (state.get("product_type") or {}).get("value") if state.get("product_type") else None
    if not pt:
        f = req_schema.FIXED_FIELDS[0]  # product_type
        return "product_type", f"请告诉我您需要找什么类型的代工厂？", list(f.get("options", []))
    if completion_ready(state):
        # 仅首次提示确认；再次进入完成态 → 开放引导（不再重复 confirm）
        if state.get("_confirm_prompted"):
            return None, OPEN_GUIDE_TEXT, ["确认完成"]
        state["_confirm_prompted"] = True
        return None, CONFIRM_TEXT, ["确认完成", "继续补充"]
    nf = req_schema.next_unfilled(state, pt)
    if not nf:
        return None, OPEN_GUIDE_TEXT, ["确认完成"]
    opts = list(nf.get("options", []))
    question = f"请问您需要哪些{nf['label']}？" if nf["kind"] == "multi" else f"请填写{nf['label']}："
    return nf["key"], question, opts
