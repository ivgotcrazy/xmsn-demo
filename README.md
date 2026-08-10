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

## 一键启动（M7）
```powershell
# 1) 预置种子数据（100 家 passed 厂商 + 领域知识库 + 演示账号 + 双轨向量；幂等可重跑）
cd backend
..\.venv\Scripts\python.exe scripts\seed_data.py

# 2) 一键拉起（基础设施 + 后端 + 买家端 + 管理后台）
.\start-all.ps1
```

## 演示账号（种子数据预置，passed）
| 角色 | 手机号 | 密码 | 入口 |
| --- | --- | --- | --- |
| 买家 | 13912345678 | buyer123 | http://localhost:5173（对话萃取→提交匹配→结果→查看原文） |
| 厂商 | 18812345678 | vendor123 | http://localhost:5173（上传文档→AI 能力档案） |
| 管理员 | 13800000000 | 123456 | http://localhost:5174（数据概览/需求/厂商/买家/日志） |

## 手工启动（替代 start-all.ps1）
- 基础设施：`cd infra && docker compose up -d`（PostgreSQL :5432 + Milvus :19530）
- 后端：`cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`
- 买家端：`cd frontend/apps/user-web && $env:VITE_USE_MOCK="false"; npm run dev`（:5173）
- 管理后台：`cd frontend/apps/admin-web && $env:VITE_USE_MOCK="false"; npm run dev`（:5174）
- API 文档：http://localhost:8000/docs

## 里程碑（M1-M7 已完成 ✅，M8 部署容器化规划中）
| M | 内容 | 状态 |
| --- | --- | --- |
| M1 | 前端优先 + 契约先行（monorepo/契约/mock/全部页面 01A~03D） | ✅ |
| M2 | 基础业务（auth/文件/厂商解析/双轨向量/审核） | ✅ |
| M3 | 对话 Agent（Schema/会话/编排/RAG/快照/画像/评估） | ✅ |
| M4 | 匹配引擎（双通道打分/兜底/评估） | ✅ |
| M5 | 解释生成（异步 AI 评语/三组判定/查看原文） | ✅ |
| M6 | 知识库与后台（知识管理/画像注入/审计/概览） | ✅ |
| M7 | 联调与种子数据（100 家厂商/50 家匹配/性能/一键启动/收尾） | ✅ |
| M8 | 部署容器化（补充：后端/前端镜像 + compose 全量一键，任务可扩展） | 🔧 |

## 文档索引
- 产品：`doc/产品/`
- 系统：`doc/系统/`（架构 / 核心需求 / 前端规范 / 用户画像 / 代理 / 匹配 / 厂商解析 / 开发计划）
