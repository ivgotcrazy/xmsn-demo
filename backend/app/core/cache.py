"""缓存接口 + 进程内 LRU（ADR-09）。演进引入 Redis 时替换实现。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any


class Cache(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...


class LocalLRUCache(Cache):
    """进程内 LRU（PoC）；多实例/多机时换 RedisCache。"""

    def __init__(self, capacity: int = 4096) -> None:
        self._store: OrderedDict[str, tuple[Any, float | None]] = OrderedDict()
        self._capacity = capacity

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        value, expire_at = self._store[key]
        if expire_at is not None and expire_at < _now():
            self.delete(key)
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expire_at = _now() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, expire_at)
        self._store.move_to_end(key)
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


def _now() -> float:
    import time

    return time.monotonic()


# 单例
cache: Cache = LocalLRUCache()
