#!/usr/bin/env sh
# 需脉枢纽 后端容器入口（M8 T8.1）
# 顺序：等 PostgreSQL → 等 Milvus → 应用迁移 → exec 启动 uvicorn
# 说明：compose 的 depends_on(healthy) 已保证基础顺序，此处为兜底重试（更稳）。
set -e

echo "[xmsn] 等待 PostgreSQL 就绪 ..."
python - <<'PY'
import asyncio
import os

import asyncpg

url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://xumai:xumai@postgres:5432/xumai")
if url.startswith("postgresql+asyncpg://"):
    url = "postgresql://" + url[len("postgresql+asyncpg://"):]


async def wait_pg() -> None:
    for i in range(60):
        try:
            conn = await asyncpg.connect(url, timeout=5)
            await conn.close()
            print("  PostgreSQL 就绪")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"  PostgreSQL 未就绪({i}): {type(exc).__name__}")
            await asyncio.sleep(2)
    raise SystemExit("PostgreSQL 长时间未就绪")


asyncio.run(wait_pg())
PY

echo "[xmsn] 等待 Milvus 就绪 ..."
python - <<'PY'
import os
import time

from pymilvus import MilvusClient

uri = f"http://{os.environ.get('MILVUS_HOST', 'milvus')}:{os.environ.get('MILVUS_PORT', '19530')}"

for i in range(90):
    try:
        client = MilvusClient(uri=uri)
        client.list_collections()
        print("  Milvus 就绪")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"  Milvus 未就绪({i}): {type(exc).__name__}")
        time.sleep(2)
else:
    raise SystemExit("Milvus 长时间未就绪")
PY

echo "[xmsn] 初始化数据库表结构 (create_all) ..."
python - <<'PY'
import asyncio

from app.db.base import Base
from app.db.session import engine
import app.db.models  # noqa: F401  # 注册全部模型到 Base.metadata


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(init_db())
PY

echo "[xmsn] 启动 uvicorn: $@"
exec "$@"
