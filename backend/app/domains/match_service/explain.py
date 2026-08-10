"""匹配解释生成（T5.1/T5.2）——《匹配详细设计》第 8.5 章。

- 与打分解耦（8.3）：compute 只打分，解释由异步 worker 生成
- 输入：需求快照 + 单厂商能力 + 候选原文块（doc_chunks 溯源）
- 输出：params 三组（带 note + source）+ ai_comment；verdict 枚举校验；非法整条丢弃
- source 用于"查看原文"定位（doc_id/page/chunk_text）
"""
from __future__ import annotations

import json
import logging
import re

from app.llm.client import chat

logger = logging.getLogger("xmsn.match")

_VALID = {"matched", "partial", "missing", "unmatched"}

EXPLAIN_PROMPT = """你是一个供需匹配分析专家。给定买家的需求和一个厂商的能力，分析匹配情况并生成解释。

# 买家需求
{demand_json}

# 厂商能力
{capability_json}

# 厂商原文片段（用于溯源，可选；判定可引用其中的片段）
{chunks}

# 输出格式（严格遵循 JSON，不要输出其他文字）
{{
  "params": [
    {{
      "param": "参数名",
      "demand_value": "需求值",
      "supply_value": "供给值",
      "verdict": "matched | partial | missing | unmatched",
      "note": "差异说明（partial标注'需协商'，missing标注'厂商未声明'）",
      "source": {{"doc_id": "...", "doc_name": "...", "page": 3, "chunk_text": "原文片段"}}
    }}
  ],
  "ai_comment": "一句话综合评语，20-50字"
}}

# 规则
1. matched=完全满足；partial=需协商（如交期30 vs 45）；missing=厂商未声明该能力；unmatched=明确不满足
2. 每个判定尽量附 source（从厂商原文片段中选取对应出处；找不到可置 null）
3. ai_comment 要客观，指出优势和不足
"""


def _render_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return "（无）"
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(
            f"[{i}] 文档ID={c.get('doc_id')} 文档名={c.get('doc_name')} 页={c.get('page')} "
            f"内容：{str(c.get('chunk_text', ''))[:300]}"
        )
    return "\n".join(lines)


async def generate(demand: dict, capability: dict, chunks: list[dict]) -> dict:
    """LLM 生成解释。失败/非法 → 返回空 params + None ai_comment（调用方降级保留打分判定）。"""
    try:
        prompt = EXPLAIN_PROMPT.format(
            demand_json=json.dumps(demand, ensure_ascii=False),
            capability_json=json.dumps(capability, ensure_ascii=False),
            chunks=_render_chunks(chunks),
        )
        raw = await chat([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=1200)
        data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
        params = []
        for p in data.get("params", []):
            if p.get("verdict") not in _VALID:
                continue
            src = p.get("source") or {}
            params.append({
                "param": p.get("param", ""),
                "demand_value": p.get("demand_value"),
                "supply_value": p.get("supply_value"),
                "verdict": p["verdict"],
                "note": p.get("note", ""),
                "source": {
                    "doc_id": src.get("doc_id"),
                    "doc_name": src.get("doc_name"),
                    "page": src.get("page"),
                    "chunk_text": src.get("chunk_text"),
                } if isinstance(src, dict) and src.get("doc_id") else None,
            })
        return {"params": params, "ai_comment": data.get("ai_comment")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("explain generation failed: %s", exc)
        return {"params": [], "ai_comment": None}
