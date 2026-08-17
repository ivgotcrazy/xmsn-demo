# 需脉枢纽 后端镜像（M8 T8.1）
# 基础：Python 3.12-slim —— 与本地开发环境一致（3.12.10），
#       pymilvus/bcrypt(abi3)/asyncpg 等 wheel 兼容最稳；如确需 3.13 可换 python:3.13-slim。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 依赖层（先 COPY 锁文件，利用 Docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码 + 运维脚本 + 入口脚本（开发阶段建表走 create_all，见 docker-entrypoint.sh）
COPY app ./app
COPY scripts ./scripts
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 上传目录（LocalFileStorage 本地盘；compose 挂 volume uploads）
RUN mkdir -p /data/uploads

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
