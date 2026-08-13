"""LLM 调用统一封装（开发计划 2.3 纪律：一律经此，禁止散落直连）。

DeepSeek（主力）走 OpenAI 兼容 SDK；超时/重试由调用方按业务语义处理（重试次数
见 settings.llm_retry，用于厂商解析/匹配等）；Token 记录在 M6 审计接入 llm_call_logs。
"""
from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger("xmsn.llm")

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=60.0,
        )
    return _client


async def chat(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int = 2048,
    with_usage: bool = False,
):
    """调用对话模型并返回首个消息内容。

    with_usage=True 时返回 (content, usage_dict)（M6 审计：prompt/completion/total tokens）；
    其余调用方返回值不变（str）。
    """
    if not settings.deepseek_api_key:
        raise RuntimeError("deepseek_api_key 未配置")
    client = get_client()
    resp = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content or ""
    if with_usage:
        u = resp.usage
        usage = {
            "prompt_tokens": u.prompt_tokens,
            "completion_tokens": u.completion_tokens,
            "total_tokens": u.total_tokens,
        } if u else {}
        return content, usage
    return content


class ToolCallResult:
    """Tool Calling 返回：正文 + 工具调用（name/arguments dict）+ usage。"""

    __slots__ = ("content", "tool_calls", "usage")

    def __init__(self, content: str, tool_calls: list[dict], usage: dict | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls  # [{"name": str, "arguments": dict | None}]
        self.usage = usage


async def chat_tool(
    messages: list[dict],
    tools: list[dict],
    tool_choice: str | dict = "auto",
    temperature: float | None = None,
    max_tokens: int = 2048,
) -> ToolCallResult:
    """带工具调用的对话（代理详细设计 v2 4.2 / 9.4）。

    tools 为 OpenAI 工具定义列表；tool_choice 默认 "auto"（PoC 实证：填槽轮正常产出
    tool_call，纯答疑轮不误触工具）。返回 ToolCallResult（正文 + tool_calls + usage）。
    """
    if not settings.deepseek_api_key:
        raise RuntimeError("deepseek_api_key 未配置")
    client = get_client()
    resp = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=max_tokens,
    )
    msg = resp.choices[0].message
    content = msg.content or ""
    tool_calls: list[dict] = []
    for tc in msg.tool_calls or []:
        args = None
        try:
            args = json.loads(tc.function.arguments or "{}")
        except Exception:
            args = None
        tool_calls.append({"name": tc.function.name, "arguments": args})
    u = resp.usage
    usage = {
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
        "total_tokens": u.total_tokens,
    } if u else None
    return ToolCallResult(content, tool_calls, usage)
