# xmsn-demo · 需脉枢纽

B2B 代工制造供需智能语义匹配平台（种子轮 PoC：真实数据、真实运行、真实效果）。

## 仓库结构（monorepo）
```
xmsn-demo/
├── frontend/   # 前端 monorepo（pnpm workspace：apps/user-web + apps/admin-web + packages/*）
├── backend/    # 后端 FastAPI（模块化单体，域 = 未来微服务）
├── infra/      # 部署与运维（docker-compose / nginx / 脚本 / .env.example）
├── doc/        # 文档体系（产品三文档 + 系统文档）
└── README.md
```

## 快速开始
- 基础设施：`cd infra && docker compose up -d`（PostgreSQL + Milvus）
- 后端：`cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
- 前端：`cd frontend && pnpm install && pnpm dev:user` / `pnpm dev:admin`

## 文档索引
- 产品：`doc/产品/`
- 系统：`doc/系统/`（架构 / 核心需求 / 前端规范 / 用户画像 / 代理 / 匹配 / 厂商解析 / 开发计划）
