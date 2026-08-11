# 需脉枢纽 · 一键启动（M8 容器化：compose 全量拉起）

# 用法：右键「使用 PowerShell 运行」或在仓库根目录执行  .\start-all.ps1
# 前置：Docker 引擎运行中（本机 Docker Desktop，或 WSL 内 docker）。
# 首次运行自动从模板创建 infra\.env（请编辑填写 LLM/Embedding Key，AI 链路依赖）。
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== 需脉枢纽 一键启动（M8 容器化）===" -ForegroundColor Cyan

# 1/3 密钥文件
if (-not (Test-Path "$root\infra\.env")) {
    Write-Host "[!] 未找到 infra\.env，已从模板创建；请填写 LLM/Embedding Key 后重新运行或继续（基础功能不受影响）" -ForegroundColor Yellow
    Copy-Item "$root\infra\.env.example" "$root\infra\.env"
}

# 2/3 构建 + 拉起（PostgreSQL + Milvus + 后端 api + 前端 web）
Write-Host "[1/3] 构建并拉起全栈（PG + Milvus + api + web）..."
Push-Location "$root\infra"
docker compose up -d --build
Pop-Location

# 3/3 提示
Write-Host "[2/3] 服务已启动" -ForegroundColor Green
Write-Host ""
Write-Host "  买家/厂商端 : http://localhost/          (演示账号见 README)"
Write-Host "  管理后台    : http://localhost/admin/    (admin 13800000000 / 123456)"
Write-Host "  API 文档    : http://localhost/docs"
Write-Host ""
Write-Host "首次运行请预置种子数据（需 infra\.env 已配置 LLM/Embedding Key）："
Write-Host "  cd infra; docker compose exec api python scripts/seed_data.py" -ForegroundColor Yellow
