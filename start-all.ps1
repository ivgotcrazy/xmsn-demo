# 需脉枢纽 · 一键启动（M7.4）

# 用法：右键「使用 PowerShell 运行」或在仓库根目录执行  .\start-all.ps1
# 前置：Docker Desktop 运行中；前端依赖已安装（pnpm install）；后端 .venv 已建（requirements.txt）
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== 需脉枢纽 一键启动 ===" -ForegroundColor Cyan

# 1/4 基础设施（PostgreSQL + Milvus）
Write-Host "[1/4] 基础设施 PostgreSQL+Milvus（docker compose）..."
Push-Location "$root\infra"
docker compose up -d
Pop-Location

# 2/4 后端 API（127.0.0.1:8000）
Write-Host "[2/4] 后端 FastAPI :8000 ..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& `"$root\.venv\Scripts\python.exe`" -m uvicorn app.main:app --app-dir `"$root\backend`" --host 127.0.0.1 --port 8000"
)

# 3/4 前端（买家端 :5173 / 管理后台 :5174，真实 API 模式）
Write-Host "[3/4] 前端（真实 API 模式，VITE_USE_MOCK=false）..."
$env:VITE_USE_MOCK = "false"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location `"$root\frontend\apps\user-web`"; npm run dev"
)
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location `"$root\frontend\apps\admin-web`"; npm run dev"
)

# 4/4 提示
Write-Host "[4/4] 启动完成" -ForegroundColor Green
Write-Host ""
Write-Host "  买家端   : http://localhost:5173   (buyer  13912345678 / buyer123)"
Write-Host "  管理后台 : http://localhost:5174   (admin  13800000000 / 123456)"
Write-Host "  厂商端   : http://localhost:5173   (vendor 18812345678 / vendor123)"
Write-Host "  API 文档 : http://localhost:8000/docs"
Write-Host ""
Write-Host "首次运行请预置种子数据（100 家厂商 + 知识库 + 双轨向量）："
Write-Host "  cd backend; ..\.venv\Scripts\python.exe scripts\seed_data.py" -ForegroundColor Yellow
