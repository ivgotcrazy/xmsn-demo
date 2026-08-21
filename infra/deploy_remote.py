#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""需脉枢纽 · 远程一键部署（对齐架构第 11 章）

部署策略（用户确认 2026-08-19）：
  1) 前置检查远端 prerequisite（逐项 [OK]/[FAIL] 打印，任一不满足则提示并退出）；
  2) 上传部署最小集（compose×2 + nginx.conf + .env，远端不做任何构建）；
  3) 本地构建镜像 → docker save 打包 → scp 上传 → 远端 docker load → 运行；
  4) 远端 compose up -d（默认非破坏式；clean=true 才 down -v）；
  5) /healthz 探活；种子数据由 deploy_remote.ini 显式控制 seed=always|never（无默认探测）。

运行（本机 Python3，需 ssh/scp 与本地 docker，均可在 WSL 内执行）：
  python infra/deploy_remote.py
  python infra/deploy_remote.py --host 1.2.3.4 --user root --seed always --backup
"""
from __future__ import annotations

import argparse
import base64
import configparser
import gzip
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

INFRA_DIR = Path(__file__).resolve().parent
ENV_FILE = INFRA_DIR / ".env"
INI_FILE = INFRA_DIR / "deploy_remote.ini"
LOCAL_COMPOSE = "docker-compose.local.yml"
REMOTE_COMPOSE = "docker-compose.remote.yml"
REMOTE_DIR_DEFAULT = "/opt/xmsn-demo"
IMAGE_TAR_NAME = "xmsn-images.tar"
JWT_PLACEHOLDER = "change-me-in-prod"
ADMIN_PWD_PLACEHOLDER = "admin123456"
HEALTH_TRIES = 60
HEALTH_DELAY = 3

# ---- 远端前置检查脚本（在远端 bash 执行；@DIR@ 占位替换）----
PRECHECK_SCRIPT = r'''set -u
DIR="@DIR@"
fail=0
chk() { if [ "$2" = ok ]; then echo "[OK]   $1"; else echo "[FAIL] $1"; fail=1; fi; }

if command -v docker >/dev/null 2>&1 && docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  chk "docker 可用" ok
else
  chk "docker 可用（远端需安装 Docker Engine）" fail
fi

if docker compose version >/dev/null 2>&1; then
  chk "docker compose 插件" ok
else
  chk "docker compose 插件（需 docker-compose-plugin）" fail
fi

compose_ver=$(docker compose version 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+' | head -1 | tr -d 'v')
major=$(echo "$compose_ver" | cut -d. -f1)
minor=$(echo "$compose_ver" | cut -d. -f2)
if [ "$major" -ge 2 ] 2>/dev/null && [ "$minor" -ge 24 ] 2>/dev/null; then
  chk "docker compose >=2.24（支持 !reset 端口收敛，当前 $compose_ver）" ok
else
  chk "docker compose >=2.24（当前 ${compose_ver:-未知}；需 v2.24+ 支持 !reset）" fail
fi

if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ':80$'; then
  echo "[info] 端口 80 当前被占用（部署流程将先自动停止旧服务，不阻塞）"
else
  chk "端口 80 空闲" ok
fi

disk_kb=$(df -P "$DIR" 2>/dev/null | awk 'NR==2{print $4}')
disk_need=$((@DISK_GB@ * 1024 * 1024))
if [ -n "$disk_kb" ] && [ "$disk_kb" -ge "$disk_need" ]; then
  chk "磁盘剩余 >=@DISK_GB@GB" ok
else
  chk "磁盘剩余 >=@DISK_GB@GB（当前 $(( ${disk_kb:-0} / 1024 / 1024 ))GB）" fail
fi

mem_mb=$(free -m 2>/dev/null | awk '/^Mem:/{print $7}')
if [ -n "$mem_mb" ] && [ "$mem_mb" -ge @MEM_MB@ ]; then
  chk "可用内存 >=@MEM_MB@MB" ok
else
  chk "可用内存 >=@MEM_MB@MB（当前 ${mem_mb:-未知} MB）" fail
fi

if mkdir -p "$DIR" && touch "$DIR/.xmsn_wtest" && rm -f "$DIR/.xmsn_wtest"; then
  chk "部署目录可写（$DIR）" ok
else
  chk "部署目录可写（$DIR）" fail
fi

exit $fail
'''


@dataclass
class RemoteConfig:
    host: str = ""
    user: str = ""
    ssh_port: int = 22
    ssh_key: str = ""
    password: str = ""
    sshpass_cmd: list[str] | None = None
    path: str = REMOTE_DIR_DEFAULT
    domain: str = ""
    env_force: bool = False
    seed: str = "never"
    backup: bool = False
    clean: bool = False
    compress: bool = False
    min_mem_mb: int = 512
    min_disk_gb: int = 2
    http_proxy: str = ""
    https_proxy: str = ""
    remote_http_proxy: str = ""
    remote_https_proxy: str = ""


def log(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"[错误] {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def q(s: str) -> str:
    return shlex.quote(s)


# ---- 本地命令 ----

def resolve_docker_cmd() -> list[str]:
    """本地 docker：优先原生 CLI，兜底 WSL 内 docker；需含 compose 插件（本地构建镜像用）。"""
    for cand in (["docker"], ["wsl", "-e", "docker"]):
        try:
            v = subprocess.run(
                cand + ["version", "--format", "{{.Server.Version}}"],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
            c = subprocess.run(
                cand + ["compose", "version"], capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            continue
        if v.returncode == 0 and v.stdout.strip() and c.returncode == 0:
            log(f"[OK] 本地 docker + compose 插件可用（server {v.stdout.strip()}）")
            return cand
    die("本地未找到可用的 docker compose（本地构建镜像需要它）。\n"
        "  ① 安装 Docker Desktop；或\n"
        "  ② 在 WSL 内安装 compose 插件：sudo apt install docker-compose-v2\n"
        "     （然后在 WSL 内运行本脚本，确认 `docker compose version` 可用）")


def run_local(cmd: list[str], cwd: Path | None = None, capture: bool = False,
              check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                          capture_output=capture, text=True,
                          encoding="utf-8", errors="replace", env=env)
    if check and proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        die(f"本地命令失败：{' '.join(cmd)}\n{err}")
    return proc


# ---- 远端命令（ssh / scp）----

def to_wsl_path(p: Path) -> str:
    """Windows 盘符路径 → WSL /mnt/<盘>/...；POSIX 路径原样返回（密码模式经 WSL 用 sshpass 时用）。"""
    s = str(p.resolve())
    m = re.match(r"^([A-Za-z]):(.*)$", s)
    if m:
        return f"/mnt/{m.group(1).lower()}{m.group(2).replace(chr(92), '/')}"
    return s


def resolve_sshpass(cfg: RemoteConfig) -> list[str]:
    """密码认证：用 sshpass 透传密码（优先原生，兜底 WSL 内）。找不到则报错退出。"""
    for cand in (["sshpass", "-V"], ["wsl", "-e", "sshpass", "-V"]):
        try:
            p = subprocess.run(cand, capture_output=True, text=True, timeout=15,
                               encoding="utf-8", errors="replace")
        except Exception:
            continue
        if p.returncode == 0:
            if cand[0] == "wsl":
                return ["wsl", "-e", "sshpass", "-p", cfg.password]
            return ["sshpass", "-p", cfg.password]
    die("已配置 password 但本地找不到 sshpass（密码认证需要它）。\n"
        "  安装：在 WSL 内执行 sudo apt install sshpass")


def ssh_base(cfg: RemoteConfig) -> list[str]:
    if cfg.password:
        assert cfg.sshpass_cmd is not None
        base = cfg.sshpass_cmd + ["ssh", "-p", str(cfg.ssh_port),
                "-o", "BatchMode=no",
                "-o", "PreferredAuthentications=password,keyboard-interactive",
                "-o", "PubkeyAuthentication=no",
                "-o", "NumberOfPasswordPrompts=1",
                "-o", "ConnectTimeout=15",
                "-o", "StrictHostKeyChecking=accept-new"]
        base.append(f"{cfg.user}@{cfg.host}")
        return base
    base = ["ssh", "-p", str(cfg.ssh_port),
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
            "-o", "StrictHostKeyChecking=accept-new"]
    if cfg.ssh_key:
        base += ["-i", str(Path(cfg.ssh_key).expanduser())]
    base.append(f"{cfg.user}@{cfg.host}")
    return base


def remote_bash(cfg: RemoteConfig, script: str, capture: bool = False,
                check: bool = True) -> subprocess.CompletedProcess:
    """在远端执行一段 bash 脚本。

    用 base64 内联传输（单行、纯 ASCII），规避两个坑：
      ① 脚本经 stdin + sshpass 时，sshpass 的 pty 会破坏换行（LF→CR，实测 set 报错、if 块 unexpected EOF）；
      ② 中文经 Windows 文本模式按 GBK 编码传给远端。
    配置了 remote_*_proxy 时，脚本开头 export 代理环境（供远端 docker pull 等使用）。
    """
    script = script.replace("\r\n", "\n").replace("\r", "\n")
    proxy = cfg.remote_http_proxy or cfg.remote_https_proxy
    if proxy:
        script = (f"export http_proxy={q(proxy)} https_proxy={q(proxy)} "
                  f"HTTP_PROXY={q(proxy)} HTTPS_PROXY={q(proxy)} "
                  f"all_proxy={q(proxy)} ALL_PROXY={q(proxy)};\n" + script)
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    cmd = ssh_base(cfg) + [f"echo {b64} | base64 -d | bash"]
    proc = subprocess.run(cmd, text=True, capture_output=capture,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        die(f"远端命令失败（rc={proc.returncode}）\n{proc.stdout or ''}{proc.stderr or ''}")
    return proc


def scp_to(cfg: RemoteConfig, local: Path, remote_path: str) -> None:
    if cfg.password:
        assert cfg.sshpass_cmd is not None
        cmd = cfg.sshpass_cmd + ["scp", "-P", str(cfg.ssh_port),
                "-o", "BatchMode=no",
                "-o", "PreferredAuthentications=password,keyboard-interactive",
                "-o", "PubkeyAuthentication=no",
                "-o", "NumberOfPasswordPrompts=1",
                "-o", "ConnectTimeout=15",
                to_wsl_path(local),
                f"{cfg.user}@{cfg.host}:{remote_path}"]
        run_local(cmd)
        return
    cmd = ["scp", "-P", str(cfg.ssh_port), "-o", "BatchMode=yes",
           "-o", "ConnectTimeout=15"]
    if cfg.ssh_key:
        cmd += ["-i", str(Path(cfg.ssh_key).expanduser())]
    cmd += [str(local), f"{cfg.user}@{cfg.host}:{remote_path}"]
    run_local(cmd)


# ---- 配置 ----

def load_config(args: argparse.Namespace) -> RemoteConfig:
    cfg = RemoteConfig()
    ini_path = Path(args.ini) if args.ini else INI_FILE
    if ini_path.exists():
        # inline_comment_prefixes：识别行内 `# / ;` 注释（配置模板大量使用），否则值会带上注释
        parser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
        parser.read(ini_path, encoding="utf-8")
        if parser.has_section("remote"):
            s = parser["remote"]
            cfg.host = s.get("host", "").strip()
            cfg.user = s.get("user", "").strip()
            cfg.ssh_port = int(s.get("ssh_port", "22").strip())
            cfg.ssh_key = s.get("ssh_key", "").strip()
            cfg.password = s.get("password", "").strip()
            cfg.path = s.get("path", REMOTE_DIR_DEFAULT).strip() or REMOTE_DIR_DEFAULT
            cfg.domain = s.get("domain", "").strip()
            cfg.env_force = s.getboolean("env_force", False)
            cfg.seed = s.get("seed", "never").strip().lower()
            cfg.backup = s.getboolean("backup", False)
            cfg.clean = s.getboolean("clean", False)
            cfg.compress = s.getboolean("compress", False)
            cfg.min_mem_mb = int(s.get("min_mem_mb", "512"))
            cfg.min_disk_gb = int(s.get("min_disk_gb", "2"))
            cfg.http_proxy = s.get("http_proxy", "").strip()
            cfg.https_proxy = s.get("https_proxy", "").strip()
            cfg.remote_http_proxy = s.get("remote_http_proxy", "").strip()
            cfg.remote_https_proxy = s.get("remote_https_proxy", "").strip()
    # CLI 覆盖（仅当显式给出）
    overrides = {
        "host": args.host, "user": args.user, "ssh_port": args.port,
        "ssh_key": args.key, "path": args.path, "domain": args.domain,
        "env_force": args.force_env, "backup": args.backup,
        "clean": args.clean, "compress": args.compress,
    }
    for attr, val in overrides.items():
        if val is not None:
            setattr(cfg, attr, val)
    if args.seed:
        cfg.seed = args.seed
    if not cfg.host or not cfg.user:
        die("缺少远端 host/user：请在 infra/deploy_remote.ini 配置，或用 --host/--user 指定")
    if cfg.seed not in ("always", "never"):
        die("seed 只能为 always 或 never（显式配置，无自动探测）")
    # 密码认证：ini 未配置时可用环境变量提供（避免密钥落盘）；ssh_key 与 password 二选一
    if not cfg.password:
        cfg.password = os.environ.get("XMSN_SSH_PASSWORD", "")
    if cfg.password:
        cfg.sshpass_cmd = resolve_sshpass(cfg)
    return cfg


# ---- 远端 .env 治理 + 安全加固 ----

def harden_env(text: str) -> tuple[str, list[str]]:
    """JWT_SECRET/ADMIN_INIT_PASSWORD 为占位符或空时，替换为随机值。"""
    changes: list[str] = []
    nonlocal_text = [text]

    def replace_match(pattern: str, label: str) -> None:
        m = re.search(pattern, nonlocal_text[0])
        if not m:
            return
        value = (m.group(1) or "").strip()
        if label == "JWT_SECRET" and (not value or value == JWT_PLACEHOLDER):
            nonlocal_text[0] = nonlocal_text[0][:m.start(1)] + secrets.token_urlsafe(32) + nonlocal_text[0][m.end(1):]
            changes.append("JWT_SECRET")
        elif label == "ADMIN_INIT_PASSWORD" and value == ADMIN_PWD_PLACEHOLDER:
            nonlocal_text[0] = nonlocal_text[0][:m.start(1)] + secrets.token_urlsafe(16) + nonlocal_text[0][m.end(1):]
            changes.append("ADMIN_INIT_PASSWORD")

    replace_match(r"(?m)^JWT_SECRET\s*=\s*(\S*)\s*$", "JWT_SECRET")
    replace_match(r"(?m)^ADMIN_INIT_PASSWORD\s*=\s*(\S*)\s*$", "ADMIN_INIT_PASSWORD")
    return nonlocal_text[0], changes


def ensure_env(cfg: RemoteConfig) -> None:
    if not ENV_FILE.exists():
        die(f"本地缺少 {ENV_FILE}：请先按 .env.example 创建并填写 LLM/Embedding Key")
    env_path = f"{q(cfg.path)}/.env"
    exists = remote_bash(
        cfg, f"test -f {env_path} && echo yes || echo no", capture=True
    ).stdout.strip() == "yes"
    if exists and not cfg.env_force:
        log("[info] 远端已存在 .env → 保留远端配置（--force-env 可覆盖）")
        env_text = remote_bash(cfg, f"cat {env_path}", capture=True, check=False).stdout
    else:
        if exists:
            log("[info] --force-env：用本地 infra/.env 覆盖远端 .env")
        else:
            log("[info] 远端无 .env → 上传本地 infra/.env")
        env_text = ENV_FILE.read_text(encoding="utf-8")
    hardened, changes = harden_env(env_text)
    for c in changes:
        log(f"[OK] 远端 .env 安全加固：{c} 已替换为随机值")
    tmp_dir = INFRA_DIR / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_local = tmp_dir / ".env.deploy"
    tmp_local.write_text(hardened, encoding="utf-8")
    scp_to(cfg, tmp_local, f"{cfg.path}/.env.tmp")
    remote_bash(cfg, f"mv -f {q(cfg.path)}/.env.tmp {env_path} && chmod 600 {env_path}")
    log("[OK] 远端 .env 就绪")


# ---- 备份（可选）----

def backup_pg(cfg: RemoteConfig) -> None:
    log("==> 备份 PostgreSQL（pg_dump）...")
    backups = INFRA_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = backups / f"xmsn_{ts}.sql"
    script = (f"cd {q(cfg.path)} && docker compose -f {LOCAL_COMPOSE} -f {REMOTE_COMPOSE} "
              f"exec -T postgres pg_dump -U xumai -d xumai")
    proc = subprocess.run(ssh_base(cfg) + [script], capture_output=True)
    if proc.returncode != 0:
        die(f"备份失败：{proc.stderr.decode(errors='replace')[:500]}")
    out.write_bytes(proc.stdout)
    log(f"[OK] 备份完成：{out}（{out.stat().st_size} 字节）")


# ---- 本地构建 → 上传 → 远端 load ----

def build_and_push_images(cfg: RemoteConfig, docker_cmd: list[str]) -> None:
    log("==> 本地构建镜像（api / web）...")
    build_cmd = docker_cmd + ["compose", "-f", LOCAL_COMPOSE, "build"]
    build_env = None
    if cfg.http_proxy or cfg.https_proxy:
        # 注意：--build-arg 代理只管 Dockerfile 内部（pip/npm 等）；基础镜像拉取仍走 daemon 代理/镜像加速器
        build_env = os.environ.copy()
        if cfg.http_proxy:
            build_cmd += ["--build-arg", f"HTTP_PROXY={cfg.http_proxy}",
                          "--build-arg", f"http_proxy={cfg.http_proxy}"]
            build_env["HTTP_PROXY"] = build_env["http_proxy"] = cfg.http_proxy
        if cfg.https_proxy:
            build_cmd += ["--build-arg", f"HTTPS_PROXY={cfg.https_proxy}",
                          "--build-arg", f"https_proxy={cfg.https_proxy}"]
            build_env["HTTPS_PROXY"] = build_env["https_proxy"] = cfg.https_proxy
        log("[info] 本地构建已启用代理（--build-arg + 构建环境）")
    run_local(build_cmd, cwd=INFRA_DIR, env=build_env)

    # 只打包「本地 build」的服务镜像（api/web）；postgres/milvus 属外部基础镜像，
    # 由远端自行拉取/已存在，不放进上传包（避免数 GB 无谓上传）。
    # 注：compose config JSON 中 build 服务没有 image 字段，镜像名按 `{project}-{service}` 推导。
    app_images: list[str] = []
    try:
        pj = run_local(docker_cmd + ["compose", "-f", LOCAL_COMPOSE, "config", "--format", "json"],
                       cwd=INFRA_DIR, capture=True)
        d = json.loads(pj.stdout)
        project = d.get("name", "xmsn-demo")
        services = d.get("services", {})
        seen: set[str] = set()
        for svc, s in services.items():
            if isinstance(s, dict) and "build" in s:
                img = s.get("image") or f"{project}-{svc}"
                if img and img not in seen:
                    seen.add(img)
                    app_images.append(img)
    except Exception as exc:  # noqa: BLE001
        # 回退：无法解析 JSON 时，仅排除已知外部基础镜像
        log(f"[warn] 解析 compose 服务镜像失败（{exc}），回退为排除已知基础镜像")
        INFRA_IMAGES = {"postgres:16", "milvusdb/milvus:v2.4.9"}
        p = run_local(docker_cmd + ["compose", "-f", LOCAL_COMPOSE, "config", "--images"],
                      cwd=INFRA_DIR, capture=True)
        all_images = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
        app_images = [img for img in all_images if img not in INFRA_IMAGES]

    if not app_images:
        die("未从 compose 解析到本地构建的应用镜像（请确认 api/web 服务有 build 配置）")
    images = [img for img in app_images
              if run_local(docker_cmd + ["image", "inspect", img], cwd=INFRA_DIR,
                           capture=True, check=False).returncode == 0]
    if not images:
        die("没有本地已构建的镜像可上传（请确认 docker compose build 成功）")
    log(f"[OK] 本地已存在镜像：{', '.join(images)}（postgres/milvus 由远端拉取，不进上传包）")

    tmp_dir = INFRA_DIR / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tar = tmp_dir / IMAGE_TAR_NAME
    log("==> docker save 打包镜像 ...")
    with tar.open("wb") as f:
        proc = subprocess.run(docker_cmd + ["save"] + images, stdout=f, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        die(f"docker save 失败：{proc.stderr.decode(errors='replace')[:500]}")

    if cfg.compress:
        gz = tmp_dir / (IMAGE_TAR_NAME + ".gz")
        log("==> gzip 压缩镜像包 ...")
        with tar.open("rb") as fin, gzip.open(gz, "wb", compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout)
        tar.unlink()
        tar = gz
    log(f"[OK] 镜像包：{tar}（{tar.stat().st_size} 字节）")

    log(f"==> 上传镜像包到远端 {cfg.host}:{cfg.path}/ ...")
    scp_to(cfg, tar, f"{cfg.path}/{tar.name}")

    log("==> 远端 docker load ...")
    remote_bash(cfg, f"docker load -i {q(cfg.path)}/{tar.name}")
    log("[OK] 远端镜像加载完成")

    shutil.rmtree(tmp_dir, ignore_errors=True)


# ---- 远端启动 / 探活 / 种子 ----

def remote_up(cfg: RemoteConfig) -> None:
    script = f"cd {q(cfg.path)}"
    if cfg.clean:
        log("==> clean=true：远端 docker compose down -v（清空数据卷）...")
        script += f" && docker compose -f {LOCAL_COMPOSE} -f {REMOTE_COMPOSE} down -v"
    else:
        log("==> 停止远端旧服务（down，保留数据卷）...")
        script += f" && (docker compose -f {LOCAL_COMPOSE} -f {REMOTE_COMPOSE} down 2>/dev/null || true)"
    script += f" && docker compose -f {LOCAL_COMPOSE} -f {REMOTE_COMPOSE} up -d"
    log("==> 远端 docker compose up -d ...")
    remote_bash(cfg, script)


def wait_healthy(cfg: RemoteConfig) -> None:
    base = cfg.domain or cfg.host
    url = f"http://{base}/healthz"
    log(f"==> 等待服务健康（{url}）...")
    for i in range(1, HEALTH_TRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status == 200:
                    log(f"[OK] 健康检查通过（第 {i} 次）")
                    return
        except Exception:
            pass
        if i % 5 == 0 or i == HEALTH_TRIES:
            log(f"  等待服务就绪 {i}/{HEALTH_TRIES} ...")
        time.sleep(HEALTH_DELAY)
    die(f"健康检查超时：{url}")


def seed_remote(cfg: RemoteConfig) -> None:
    log("==> 灌入演示数据（seed_curated --reset，seed=always）...")
    script = (f"cd {q(cfg.path)} && docker compose -f {LOCAL_COMPOSE} -f {REMOTE_COMPOSE} "
              f"exec -T api python scripts/seed_curated.py --reset")
    remote_bash(cfg, script)
    log("[OK] 种子数据完成")


# ---- 入口 ----

def main() -> None:
    parser = argparse.ArgumentParser(
        description="需脉枢纽 远程一键部署（本地构建镜像 → 上传 → load → 运行）")
    parser.add_argument("--ini", default=None, help="配置文件路径（默认 infra/deploy_remote.ini）")
    parser.add_argument("--host", help="远端 IP/域名")
    parser.add_argument("--user", help="远端 SSH 用户")
    parser.add_argument("--port", type=int, help="SSH 端口")
    parser.add_argument("--key", help="SSH 私钥路径")
    parser.add_argument("--path", help="远端部署目录")
    parser.add_argument("--domain", help="对外访问域名（用于最终 URL，默认用 --host）")
    parser.add_argument("--force-env", action="store_true", help="用本地 infra/.env 覆盖远端 .env")
    parser.add_argument("--seed", choices=["always", "never"], help="是否重灌演示数据（覆盖配置）")
    parser.add_argument("--backup", action="store_true", help="部署前先 pg_dump 备份回本地")
    parser.add_argument("--clean", action="store_true", help="先 docker compose down -v（清数据，慎用）")
    parser.add_argument("--compress", action="store_true", help="镜像包先 gzip 再上传")
    args = parser.parse_args()

    cfg = load_config(args)
    log("=" * 60)
    log(f"需脉枢纽 远程部署 → {cfg.user}@{cfg.host}:{cfg.ssh_port}  目录 {cfg.path}")
    log("=" * 60)
    if cfg.password:
        log("[OK] 密码认证已启用（sshpass）")

    docker_cmd = resolve_docker_cmd()

    # [1/9] 远端前置检查（任一不满足则退出；流式输出，连接/认证出错时也能看到具体报错）
    log("==> [1/9] 远端前置检查 ...")
    pre_script = (PRECHECK_SCRIPT
                  .replace("@DIR@", cfg.path)
                  .replace("@MEM_MB@", str(cfg.min_mem_mb))
                  .replace("@DISK_GB@", str(cfg.min_disk_gb)))
    proc = remote_bash(cfg, pre_script, capture=False, check=False)
    if proc.returncode != 0:
        die("远端前置检查未通过，请按上方 [FAIL] 提示修复后重试")

    # [2/9] 停止远端旧服务（若存在；数据卷保留，避免端口/容器名冲突）
    log("==> [2/9] 停止远端旧服务（若存在）...")
    remote_bash(cfg, (f"mkdir -p {q(cfg.path)} && cd {q(cfg.path)} && "
                      f"(docker compose -f {LOCAL_COMPOSE} -f {REMOTE_COMPOSE} down 2>/dev/null || true)"))
    log("[OK] 旧服务已停止（数据卷保留）")

    # [3/9] 上传部署文件（compose×2 + nginx.conf）
    log("==> [3/9] 上传部署文件（compose×2 / nginx.conf）...")
    remote_bash(cfg, f"mkdir -p {q(cfg.path)}/nginx")
    scp_to(cfg, INFRA_DIR / LOCAL_COMPOSE, f"{cfg.path}/{LOCAL_COMPOSE}")
    scp_to(cfg, INFRA_DIR / REMOTE_COMPOSE, f"{cfg.path}/{REMOTE_COMPOSE}")
    scp_to(cfg, INFRA_DIR / "nginx" / "nginx.conf", f"{cfg.path}/nginx/nginx.conf")
    log("[OK] 部署文件已上传")

    # [4/9] 远端 .env 治理与安全加固
    log("==> [4/9] 远端 .env 治理与安全加固 ...")
    ensure_env(cfg)

    # [5/9] 备份（可选）
    if cfg.backup:
        log("==> [5/9] 备份 ...")
        backup_pg(cfg)
    else:
        log("==> [5/9] 备份：已跳过（backup=false）")

    # [6/9] 本地构建 → 上传 → 远端 load
    log("==> [6/9] 本地构建镜像 → 上传 → 远端 load ...")
    build_and_push_images(cfg, docker_cmd)

    # [7/9] 远端启动（clean=true 时 down -v；否则先 down 保留数据卷）
    log("==> [7/9] 远端启动服务 ...")
    remote_up(cfg)

    # [8/9] 健康检查
    log("==> [8/9] 健康检查 ...")
    wait_healthy(cfg)

    # [9/9] 种子数据（显式配置）
    if cfg.seed == "always":
        log("==> [9/9] 种子数据（seed=always）...")
        seed_remote(cfg)
    else:
        log("==> [9/9] 种子数据：已跳过（seed=never，可用 --seed always 重灌）")

    # 完成
    log("==> 完成 ✅")
    base = cfg.domain or cfg.host
    print()
    print(f"  买家/厂商端: http://{base}/")
    print(f"  管理后台:    http://{base}/admin/")
    print(f"  API 文档:    http://{base}/docs")
    print("  演示账号: 客户 13912345678/customer123 · 管理员 13800000000/123456 · 厂家 13800000001~10/vendor123")
    print("  下一步: 生产环境建议配置 HTTPS（如 certbot --nginx）")


if __name__ == "__main__":
    main()
