"""TaskQueue 抽象 + 进程内实现（ADR-09）。

业务代码只依赖 TaskQueue 接口；演进到多进程/多机时替换为
Redis Stream / RabbitMQ 实现，业务代码不变。
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("xmsn.queue")

TaskHandler = Callable[[str, dict], Awaitable[None]]


class TaskQueue(ABC):
    @abstractmethod
    async def enqueue(self, task: str, payload: dict) -> None: ...

    @abstractmethod
    async def start(self, handler: TaskHandler) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...


class LocalTaskQueue(TaskQueue):
    """进程内队列（PoC）：任务幂等、失败重试由调用方保证（快照可重放）。"""

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue(maxsize=maxsize)
        self._worker: asyncio.Task | None = None

    async def enqueue(self, task: str, payload: dict) -> None:
        await self._queue.put((task, payload))

    async def start(self, handler: TaskHandler) -> None:
        self._worker = asyncio.create_task(self._run(handler))

    async def _run(self, handler: TaskHandler) -> None:
        while True:
            task, payload = await self._queue.get()
            try:
                await handler(task, payload)
            except Exception:  # noqa: BLE001
                logger.exception("task failed: %s %s", task, payload)

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass


# 单例（应用进程内共享）
queue: TaskQueue = LocalTaskQueue()
