"""文件存储抽象 + 本地盘实现（对齐架构 3.5 / 厂商解析 LLD 0.3 FileStorage）。

PoC 用本地盘模拟对象存储（/data/uploads，等价 bucket/vendor/...）；
演进 MinIO/OSS/S3 时仅替换实现，业务代码不变（ADR-07/09 同哲学）。
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings


class FileStorage(ABC):
    """文件存取抽象：save 返回 (file_id, url)；read/delete/exists 按 file_id。"""

    @abstractmethod
    async def save(self, data: bytes, name: str) -> tuple[str, str]: ...

    @abstractmethod
    async def read(self, file_id: str) -> bytes: ...

    @abstractmethod
    async def delete(self, file_id: str) -> None: ...

    @abstractmethod
    async def exists(self, file_id: str) -> bool: ...

    @abstractmethod
    async def name(self, file_id: str) -> str:
        """原始文件名（preview / 溯源展示用）。"""


class LocalFileStorage(FileStorage):
    """本地盘实现：`{upload_dir}/{file_id}.bin`（内容）+ `{file_id}.meta`（原始文件名）。"""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base = Path(base_dir or settings.upload_dir)

    def _bin(self, file_id: str) -> Path:
        return self._base / f"{file_id}.bin"

    def _meta(self, file_id: str) -> Path:
        return self._base / f"{file_id}.meta"

    async def save(self, data: bytes, name: str) -> tuple[str, str]:
        self._base.mkdir(parents=True, exist_ok=True)
        file_id = uuid.uuid4().hex
        self._bin(file_id).write_bytes(data)
        self._meta(file_id).write_text(name or "unnamed", encoding="utf-8")
        return file_id, f"/data/uploads/{file_id}.bin"

    async def read(self, file_id: str) -> bytes:
        return self._bin(file_id).read_bytes()

    async def delete(self, file_id: str) -> None:
        for p in (self._bin(file_id), self._meta(file_id)):
            if p.exists():
                p.unlink()

    async def exists(self, file_id: str) -> bool:
        return self._bin(file_id).exists()

    async def name(self, file_id: str) -> str:
        meta = self._meta(file_id)
        return meta.read_text(encoding="utf-8") if meta.exists() else "unnamed"


# 单例（应用进程内共享；演进多实例时按配置注入云实现）
storage: FileStorage = LocalFileStorage()
