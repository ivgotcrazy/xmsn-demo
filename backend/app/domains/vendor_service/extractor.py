"""LLM 能力提取（厂商解析 LLD 4）：文档文本 → 能力档案 + 字段级置信度 + 溯源。

实现以《厂商解析详细设计》4.1 Prompt 为准：按能力 Schema（硬 7 项 + 软 3 项）
输出 structured_tags + summary_text + sources（每字段 doc/page/chunk_text/confidence）；
无总体 parse_confidence（2026-08-10 决策：字段级置信度随 source_map）。
"""
from __future__ import annotations

import json
import logging
import re

from app.core.config import settings
from app.llm.client import chat
from app.schemas.common import err_501

logger = logging.getLogger("xmsn.vendor.extractor")

PROMPT_PARSE = """你是一个制造业能力解析专家。你的任务是分析厂商上传的文档，提取结构化的制造能力标签。

# 输出Schema（严格 JSON）
{{
  "structured_tags": {{
    "process_types": ["string"], "certifications": ["string"], "os_support": ["string"],
    "interfaces": ["string"], "moq": number, "lead_time_days": number, "monthly_capacity": number,
    "product_types": ["string"], "application_scenarios": ["string"], "customization": "string"
  }},
  "summary_text": "一句话摘要，不超过50字",
  "sources": {{
    "process_types": {{"doc_id": "...", "doc_name": "...", "page": 1, "chunk_text": "...", "confidence": 0.92}}
  }}
}}

# 输入资料
文档内容：{document_text}

请解析并输出符合Schema的JSON。如果某项信息在文档中不存在，使用空数组或null（不猜测补全）。
硬能力（工艺/认证/OS/接口/起订量/交期/月产能）缺失时，sources 中不包含该字段。
confidence 表示该字段的把握程度（0-1），字段缺失则无对应 sources 条目。
"""


async def extract(document_text: str) -> dict:
    """调用 LLM 提取；返回 {structured_tags, summary_text, sources}。"""
    if not settings.deepseek_api_key:
        raise err_501("AI 解析服务未配置（deepseek_api_key）")
    prompt = PROMPT_PARSE.format(document_text=(document_text or "")[:16000])
    raw = await chat([{"role": "user", "content": prompt}])
    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("LLM 输出无 JSON")
    return json.loads(match.group(0))
