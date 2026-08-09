"""导出后端 openapi.json 到前端契约快照（架构 5.4 Code-First）。

产物：frontend/packages/api/openapi/openapi.json（快照提交仓库，可离线生成、可 diff）。
运行：python scripts/export_openapi.py（cwd=backend）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

FRONTEND_OPENAPI = Path(__file__).resolve().parents[2] / "frontend" / "packages" / "api" / "openapi" / "openapi.json"


def main() -> None:
    spec = app.openapi()
    FRONTEND_OPENAPI.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_OPENAPI.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})
    print(f"openapi exported -> {FRONTEND_OPENAPI}")
    print(f"paths={len(paths)} schemas={len(schemas)}")


if __name__ == "__main__":
    main()
