"""pytest 根配置：将 backend 加入 sys.path，使 `app` 可导入。"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
