"""精选演示数据（curated v2，2026-08-16）：单一品类「智能音箱」+ 真实 PDF 能力文档 + 账号。

定位（对外演示 / 体验）：
- 自测用 seed_data.py（100 家模板厂商）；本脚本 = 演示用精选数据（curated-only，体验更佳）。
- 单一品类：智能音箱 10 家（虚构公司名 + 真实行业参数），覆盖 matched / partial / missing / niche。
- 每家 1 份真实 PDF 能力文档（scripts/data/curated_capabilities/），走真实解析管线。
- 账号：1 买家 + 1 管理员 + 10 厂家（每家可登录厂商端看自己的档案）。
- 知识：10 条智能音箱行业知识（答疑 / 推荐 / 认证避坑）。

导入（方案A，等价"后台手动导入"的自动化）：
- 复用厂商注册 register_vendor + 能力上传 upload_capability + 异步解析 worker._parse_capability
  同一条生产管线（storage 落盘 + pypdf 解析 + LLM 提取 + 校验 + 双轨向量），与线上一致、可复现。

运行：
- 演示环境（推荐，在 api 容器内执行，--reset 先清空自测/旧演示数据再导入 curated-only）：
      docker exec xmsn-api python scripts/seed_curated.py --reset
- 本地开发（连 localhost 库，需已配置 .env 的 LLM/Embedding Key）：
      python scripts/seed_curated.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, text  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.models import (  # noqa: E402
    KnowledgeItem,
    User,
    Vendor,
    VendorCapability,
)
from app.db.session import SessionLocal  # noqa: E402
from app.domains.file_service.storage import storage  # noqa: E402
from app.domains.vendor_service import service as vendor_service  # noqa: E402
from app.llm.embedding import embed  # noqa: E402
from app.schemas.vendor import VendorRegisterRequest  # noqa: E402
from app.vector import indexer as vector  # noqa: E402
from app.vector.client import (  # noqa: E402
    CHUNK_COLLECTION,
    KNOWLEDGE_COLLECTION,
    REP_COLLECTION,
    ensure_collections,
    get_client,
)
from app.worker import _parse_capability  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"
CAP_DIR = DATA / "curated_capabilities"

# 演示账号：1 买家 + 1 管理员（厂家账号按 curated_vendors.json 每家 1 个）
DEMO_ACCOUNTS = [
    # (phone, password, role, email)
    ("13912345678", "buyer123", "buyer", "buyer@xmsn.demo"),
    ("13800000000", "123456", "admin", "admin@xmsn.demo"),
]

# golden 校验的 core 键（与匹配/校验器对齐）
_VERIFY_KEYS = [
    "process_types", "certifications", "os", "interfaces", "moq", "lead_time_days",
    "monthly_capacity", "product_types", "application_scenarios", "customization",
]
# 重置时清理的表（外键安全顺序）
_RESET_TABLES = [
    "match_results", "match_runs", "buyer_requests", "conversation_events",
    "conversations", "llm_call_logs", "admin_logs", "user_profiles",
    "profile_schemas", "vendor_capabilities", "vendors", "knowledge_items", "users",
]


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


async def _upsert_user(db, phone: str, pwd: str, role: str, email: str) -> User:
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if user is None:
        user = User(phone=phone, email=email, role=role,
                    password_hash=hash_password(pwd), status="active")
        db.add(user)
        await db.flush()
        print(f"  user create: {phone} ({role})")
    else:
        user.password_hash = hash_password(pwd)
        user.role = role
        user.status = "active"
        print(f"  user update: {phone} ({role}) 密码重置为演示密码")
    return user


async def _reset_demo(db) -> None:
    """清空演示数据（curated-only）：存储文件 + 向量 + 库表 + 账号。"""
    caps = (await db.execute(select(VendorCapability))).scalars().all()
    for cap in caps:
        for ref in cap.doc_refs or []:
            try:
                await storage.delete(ref["file_id"])
            except Exception:  # noqa: BLE001
                pass
    for vid in (await db.execute(select(Vendor.vendor_id))).scalars().all():
        await vector.delete_vendor_vectors(str(vid))
    for tbl in _RESET_TABLES:
        await db.execute(text(f'DELETE FROM "{tbl}"'))
    await db.commit()
    client = get_client()
    for col in (REP_COLLECTION, CHUNK_COLLECTION, KNOWLEDGE_COLLECTION):
        try:
            client.drop_collection(col)
        except Exception:  # noqa: BLE001 - 集合可能不存在
            pass
    await ensure_collections()
    print("  reset: 演示数据已清空（厂商/能力/知识/会话/匹配/账号 + 向量 + 存储）")


async def _seed_vendor(db, item: dict) -> None:
    """厂家账号 → 厂商注册 → 能力文档上传 → 真实解析 → golden 校验。"""
    vd = item["vendor"]
    acct = item["account"]
    fac = await _upsert_user(db, acct["phone"], acct["password"], "vendor", acct["email"])

    exists = (await db.execute(select(Vendor).where(Vendor.credit_code == vd["credit_code"]))).scalar_one_or_none()
    if exists:
        # 幂等 + 自愈：已存在但能力档案为空/解析失败（如 LLM 临时 402）→ 重新上传 + 解析
        cap = (await db.execute(
            select(VendorCapability).where(VendorCapability.vendor_id == exists.vendor_id)
        )).scalar_one_or_none()
        need_reparse = cap is None or not (cap.structured_tags or {}).get("product_types")
        if not need_reparse:
            print(f"  vendor exists: {vd['company_name']}（能力档案完整，跳过）")
            return
        print(f"  vendor exists: {vd['company_name']}（能力档案不完整，重试解析）")
        doc_file = item["capability"]["doc_file"]
        pdf = (CAP_DIR / doc_file).read_bytes()
        cap_out = await vendor_service.upload_capability(db, str(exists.vendor_id), [(pdf, doc_file)])
        await _parse_capability(str(cap_out.capability_id))
        await _verify_golden(db, str(exists.vendor_id), item)
        return

    payload = VendorRegisterRequest(
        company_name=vd["company_name"], location=vd["location"],
        main_industry=vd["main_industry"], credit_code=vd["credit_code"],
    )
    vendor = await vendor_service.register_vendor(db, str(fac.user_id), payload)
    # 模拟后台审核通过（演示就绪）
    row = (await db.execute(select(Vendor).where(Vendor.vendor_id == uuid.UUID(vendor.vendor_id)))).scalar_one()
    row.audit_status = "passed"
    await db.commit()
    print(f"  vendor created: {vd['company_name']}")

    doc_file = item["capability"]["doc_file"]
    pdf = (CAP_DIR / doc_file).read_bytes()
    cap = await vendor_service.upload_capability(db, str(vendor.vendor_id), [(pdf, doc_file)])
    await _parse_capability(str(cap.capability_id))
    await _verify_golden(db, str(vendor.vendor_id), item)


async def _verify_golden(db, vendor_id: str, item: dict) -> None:
    """解析结果 vs golden 校验（core 匹配字段），不一致仅告警不阻断。"""
    cap = (await db.execute(
        select(VendorCapability).where(VendorCapability.vendor_id == uuid.UUID(vendor_id))
    )).scalar_one_or_none()
    if cap is None:
        print(f"  [verify] {item['id']}: 无能力档案（解析失败？）")
        return
    # 解析在独立 Session 提交，本 session 身份映射可能读到陈旧值 → 强制刷新
    await db.refresh(cap)
    tags = cap.structured_tags or {}
    golden = item["capability"]["golden"]
    issues: list[str] = []
    for k in _VERIFY_KEYS:
        gv, tv = golden.get(k), tags.get(k)
        parsed_str = ""
        if isinstance(tv, list):
            parsed_str = "、".join(str(x) for x in tv)
        elif tv is not None:
            parsed_str = str(tv)
        if isinstance(gv, (int, float)):
            ok = gv == tv
        else:
            gvals = gv if isinstance(gv, list) else [gv]
            ok = all(str(x) in parsed_str for x in gvals if str(x))
        if not ok:
            issues.append(f"{k}: golden={gv} vs parsed={parsed_str or '∅'}")
    flag = "OK" if not issues else "MISMATCH"
    print(f"  [verify] {item['id']} {item['vendor']['company_name']}: completeness={cap.completeness} {flag}")
    for i in issues[:8]:
        print(f"      ! {i}")


async def _seed_knowledge(db) -> None:
    data = _load("curated_knowledge.json")
    created = 0
    for k in data["knowledge"]:
        exists = (await db.execute(select(KnowledgeItem).where(KnowledgeItem.content == k["content"]))).scalar_one_or_none()
        if exists:
            continue
        db.add(KnowledgeItem(content=k["content"], category=k["category"], industry=k["industry"],
                             source=f"curated:{k['usage']}"))
        created += 1
    await db.commit()
    # 全量知识向量 upsert（与 seed_data 一致，幂等）
    rows = (await db.execute(select(KnowledgeItem))).scalars().all()
    texts = [r.content for r in rows]
    vecs = await embed(texts)
    client = get_client()
    client.upsert(KNOWLEDGE_COLLECTION, data=[
        {"id": f"k_{r.knowledge_id}", "knowledge_id": str(r.knowledge_id),
         "category": r.category, "industry": r.industry, "embedding": v}
        for r, v in zip(rows, vecs)
    ])
    print(f"  knowledge created: {created}（库内共 {len(rows)} 条，向量已 upsert）")


async def seed(reset: bool = False) -> None:
    async with SessionLocal() as db:
        print("=== 精选演示数据（智能音箱 · curated v2）===")
        if reset:
            await _reset_demo(db)
        # 1) 账号：买家 + 管理员
        for phone, pwd, role, email in DEMO_ACCOUNTS:
            await _upsert_user(db, phone, pwd, role, email)
        await db.commit()
        # 2) 厂商（10 家，每家含厂家账号 + PDF 能力文档）
        data = _load("curated_vendors.json")
        for item in data["vendors"]:
            await _seed_vendor(db, item)
        # 3) 知识（10 条）
        await _seed_knowledge(db)
        # 4) 汇总
        await _summary(db)
        print("=== 完成 ===")


async def _summary(db) -> None:
    nv = len((await db.execute(select(Vendor))).scalars().all())
    nc = len((await db.execute(select(VendorCapability))).scalars().all())
    nk = len((await db.execute(select(KnowledgeItem))).scalars().all())
    nb = len((await db.execute(select(User).where(User.role == "buyer"))).scalars().all())
    na = len((await db.execute(select(User).where(User.role == "admin"))).scalars().all())
    nf = len((await db.execute(select(User).where(User.role == "vendor"))).scalars().all())
    print(f"  厂商 {nv}（能力档案 {nc}）｜知识 {nk}｜账号 buyer {nb} / admin {na} / factory {nf}")
    print("  登录：买家 13912345678/buyer123 ｜ 管理员 13800000000/123456 ｜ 厂家 13800000001~10/vendor123")


def main() -> None:
    parser = argparse.ArgumentParser(description="精选演示数据导入（智能音箱 curated-only）")
    parser.add_argument("--reset", action="store_true",
                        help="先清空演示数据（自测/旧演示数据）再导入，保证 curated-only")
    args = parser.parse_args()
    asyncio.run(seed(reset=args.reset))


if __name__ == "__main__":
    main()
