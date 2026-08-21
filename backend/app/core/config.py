"""全局配置（12-factor：配置外置，env/ConfigMap 读取）。对齐架构 11.4。"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env（与启动目录无关，基于本文件位置定位）
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # 应用
    app_name: str = "需脉枢纽 API"
    debug: bool = False

    # 数据库
    database_url: str = "postgresql+asyncpg://xumai:xumai@localhost:5432/xumai"

    # 向量数据库
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # 文档存储（本地盘模拟对象存储，FileStorage）
    upload_dir: str = "/data/uploads"
    max_upload_size_mb: int = 20

    # 大模型（主力 DeepSeek，备选 Gemini/ChatGPT）
    llm_provider: str = "deepseek"          # deepseek / openai / zhipu
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Embedding（智谱 embedding-2，1024 维）
    embedding_api_key: str = ""
    embedding_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    embedding_model: str = "embedding-2"
    embedding_dim: int = 1024

    # 认证（JWT）
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7    # 游客会话（匿名体验）：token 有效期 24h；匿名数据 TTL 清理（小时）
    guest_expire_minutes: int = 60 * 24
    guest_cleanup_hours: int = 24    # 验证码：PoC 无短信/邮件网关时关闭（false=仅发送日志）；接入网关后开启
    verify_code_required: bool = False

    # 业务常量
    llm_temperature: float = 0.2
    llm_retry: int = 2
    rag_top_k: int = 3
    rag_min_score: float = 0.6
    match_top_k: int = 50
    match_min_semantic: float = 0.35


settings = Settings()
