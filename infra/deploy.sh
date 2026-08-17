#!/usr/bin/env bash
# 需脉枢纽 · 一键部署（唯一部署入口）
#
# 保证：每次部署 = 数据全铲（down -v 清空全部数据卷 PG/Milvus/uploads）→
#       全新构建启动（api 启动时 create_all 建全新空表）→ 全量重灌演示数据。
# 数据重灌只发生在此部署动作中，容器日常重启不重灌。
#
# 用法（docker 在 WSL 内，需在 WSL 中执行）：
#   wsl -d Ubuntu-22.04 -- bash infra/deploy.sh
# 或在 WSL 内：cd /mnt/d/code/xmsn/xmsn-demo/infra && bash deploy.sh
set -euo pipefail

cd "$(dirname "$0")"

echo "==> [1/4] 全铲：删除全部数据卷（PG / Milvus / uploads）..."
docker compose down -v

echo "==> [2/4] 全新构建镜像（api / web）..."
docker compose build

echo "==> [3/4] 启动服务（api 启动时 create_all 建全新空表）..."
docker compose up -d

echo "==> 等待 api healthy ..."
s=""
for i in $(seq 1 60); do
  s=$(docker inspect xmsn-api --format '{{.State.Health.Status}}' 2>/dev/null || echo "gone")
  [ "$s" = "healthy" ] && break
  sleep 3
done
[ "$s" = "healthy" ] || { echo "api 未就绪: $s"; exit 1; }

echo "==> [4/4] 全量重灌演示数据（seed_curated --reset）..."
docker exec xmsn-api python scripts/seed_curated.py --reset

echo ""
echo "==> 部署完成 ✅  http://localhost"
echo "    客户  13912345678 / customer123"
echo "    管理员 13800000000 / 123456"
echo "    厂家  13800000001~10 / vendor123"
