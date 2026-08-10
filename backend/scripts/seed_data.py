"""M7.1 种子数据（架构 11.5 / 开发计划 T7.1）：100 家 passed 厂商 + 领域知识库 + 演示账号 + 双轨向量。

- 幂等：按 credit_code / 手机号 / 知识 content 检查，已存在跳过；可重复执行。
- 运行：python scripts/seed_data.py（cwd=backend）；约 110+ 次 embedding（智谱），耗时数分钟。
"""
from __future__ import annotations

import asyncio
import random
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import KnowledgeItem, User, Vendor, VendorCapability
from app.db.session import SessionLocal
from app.llm.embedding import embed
from app.vector import indexer as vector
from app.vector.client import KNOWLEDGE_COLLECTION, get_client

random.seed(20260811)

CITIES = ["东莞", "深圳", "广州", "惠州", "中山", "佛山", "苏州", "宁波", "青岛", "厦门",
          "成都", "重庆", "武汉", "合肥", "天津"]
CORES = ["电子", "科技", "智能制造", "精密制造", "电路", "半导体", "智能", "电器", "通讯", "数码"]
SUFFIX = ["有限公司", "股份有限公司", "有限责任公司"]

# 品类 → 能力模板（真实风格）
CATALOG = {
    "机顶盒": {
        "os_support": ["Linux", "Android", "Linux/Android"],
        "interfaces": [["网口", "USB", "HDMI"], ["网口", "USB"], ["网口", "HDMI", "AV"]],
        "certifications": [["CE", "FCC", "SRRC"], ["CE", "ISO9001"], ["CE", "FCC"], ["CCC", "SRRC"]],
        "process_types": ["SMT贴片、组装测试", "SMT贴片、老化测试、组装", "组装测试、老化测试"],
        "product_types": ["机顶盒"],
        "application_scenarios": ["家庭娱乐", "酒店IPTV", "运营商终端"],
        "summary": "专注{pt}ODM，{proc}，支持{os}，月产能{cap}万台，交期{lead}天。",
    },
    "智能音箱": {
        "os_support": ["Android", "RTOS", "Android/RTOS"],
        "interfaces": [["蓝牙", "WiFi", "Type-C"], ["蓝牙", "WiFi"], ["WiFi", "Type-C"]],
        "certifications": [["CE", "FCC"], ["CE"], ["SRRC", "CE"]],
        "process_types": ["SMT贴片、声学测试、组装", "声学测试、组装", "SMT贴片、组装、煲机测试"],
        "product_types": ["智能音箱"],
        "application_scenarios": ["家庭", "智能家居", "酒店客房"],
        "summary": "专注{pt}方案，{proc}，支持{os}，月产能{cap}万台，交期{lead}天。",
    },
    "IoT设备": {
        "os_support": ["RTOS", "FreeRTOS"],
        "interfaces": [["LoRa", "NB-IoT", "BLE"], ["BLE", "WiFi", "Zigbee"], ["NB-IoT", "4G"]],
        "certifications": [["SRRC", "CE"], ["CE"], ["FCC", "SRRC"]],
        "process_types": ["SMT贴片、防水测试、组装", "SMT贴片、环境测试", "组装、老化测试"],
        "product_types": ["IoT设备"],
        "application_scenarios": ["智能家居", "工业监测", "智慧农业", "资产追踪"],
        "summary": "专注{pt}终端，{proc}，支持{os}，月产能{cap}万台，交期{lead}天。",
    },
}
CATEGORIES = ["机顶盒", "智能音箱", "IoT设备"]

KNOWLEDGE = [
    # (content, category, industry)
    ("出口欧盟的机顶盒必须通过CE认证，且建议提前准备RoHS与REACH报告。", "dependency", "机顶盒"),
    ("Amlogic S905X4 支持4K AV1解码，是高端机顶盒主流主控方案。", "terminology", "机顶盒"),
    ("机顶盒SMT贴片一般需要8-12层PCB，封装最小0402，三防漆可选。", "trap", "机顶盒"),
    ("机顶盒出口中东需要SRRC？不，SRRC为中国无线电型号核准，中东常用GCC认证。", "faq", "机顶盒"),
    ("智能音箱远场拾音对麦克风阵列有要求，4麦及以上才能覆盖8米内语音唤醒。", "dependency", "智能音箱"),
    ("智能音箱喇叭功率常见3W/5W/10W，10W以上多用于户外/大客厅场景。", "terminology", "智能音箱"),
    ("智能音箱整机测试需含声学响应、蓝牙吞吐、WiFi共存与待机功耗。", "trap", "智能音箱"),
    ("智能音箱出口美国需FCC，带蓝牙WiFi需做模块认证（FCC ID）。", "faq", "智能音箱"),
    ("IoT设备低功耗通信常选NB-IoT/LoRa，室内穿墙场景蓝牙Mesh更稳定。", "dependency", "IoT设备"),
    ("NB-IoT适合低频小数据上报（每日几次），实时高频交互选4G/WiFi。", "terminology", "IoT设备"),
    ("IoT设备防水等级常见IP54/IP65，户外设备建议IP65并做盐雾测试。", "trap", "IoT设备"),
    ("IoT设备出口欧盟需CE-RED指令（含无线），比普通CE多了射频要求。", "faq", "IoT设备"),
]

DEMO_USERS = [
    # (phone, password, role, email)
    ("13912345678", "buyer123", "buyer", "buyer@xmsn.demo"),
    ("13800000000", "123456", "admin", "admin@xmsn.demo"),
    ("18812345678", "vendor123", "vendor", "vendor@xmsn.demo"),
]


def _gen_vendor(i: int) -> tuple[dict, dict]:
    """生成一家真实风格厂商：(vendor 字段, capability tags 字段)。"""
    city = random.choice(CITIES)
    name = f"{city}{random.choice(CORES)}{'' if random.random() > 0.3 else random.choice(SUFFIX)}"
    if not name.endswith("公司") and random.random() > 0.5:
        name += "有限公司" if random.random() > 0.5 else "科技有限公司"
    cat = random.choice(CATEGORIES)
    tpl = CATALOG[cat]
    tags = {
        "os_support": random.choice(tpl["os_support"]),
        "interfaces": random.choice(tpl["interfaces"]),
        "certifications": random.choice(tpl["certifications"]),
        "process_types": random.choice(tpl["process_types"]),
        "product_types": [tpl["product_types"][0]],
        "application_scenarios": random.choice(tpl["application_scenarios"]),
        "moq": random.choice([500, 1000, 2000, 3000, 5000, 10000]),
        "lead_time_days": random.choice([15, 20, 25, 30, 35, 45]),
        "monthly_capacity": random.choice([10, 20, 30, 50, 80, 100]),
        "customization": random.choice(["ODM", "OEM", "ODM/OEM"]),
    }
    summary = tpl["summary"].format(
        pt=tags["product_types"][0], proc=tags["process_types"],
        os=tags["os_support"], cap=tags["monthly_capacity"], lead=tags["lead_time_days"],
    )
    credit = f"91{i:08d}{i:04d}K"  # 15 位，≤ VARCHAR(18)
    vendor = {
        "company_name": name,
        "location": f"广东{city}" if city in ("东莞", "深圳", "广州", "惠州", "中山", "佛山") else f"{city}",
        "main_industry": random.choice(["消费电子代工", "电子制造服务", "智能硬件代工"]),
        "credit_code": credit,
        "audit_status": "passed",
    }
    return vendor, {"tags": tags, "summary": summary, "industry": cat}


async def _seed_users(db) -> None:
    for phone, pwd, role, email in DEMO_USERS:
        exists = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
        if exists:
            # 幂等收敛：已存在则重置密码为演示密码（保证演示账号可登录）
            exists.password_hash = hash_password(pwd)
            print(f"  user update: {phone} ({role}) 密码重置为演示密码")
            continue
        db.add(User(phone=phone, email=email, role=role,
                    password_hash=hash_password(pwd), is_active=True))
        print(f"  user create: {phone} ({role})")
    await db.commit()


async def _seed_vendors(db) -> None:
    """100 家 passed 厂商 + 能力档案 + 双轨向量（幂等：按 credit_code）。"""
    created = 0
    for i in range(1, 101):
        vdata, cdata = _gen_vendor(i)
        exists = (await db.execute(select(Vendor).where(Vendor.credit_code == vdata["credit_code"]))).scalar_one_or_none()
        if exists:
            continue
        vendor = Vendor(**vdata)
        db.add(vendor)
        await db.flush()
        cap = VendorCapability(
            vendor_id=vendor.vendor_id,
            structured_tags=cdata["tags"],
            summary_text=cdata["summary"],
            completeness=1.0,
            source_type="seed",
            version=1,
            doc_count=1,
            doc_refs=[{"name": f"{vdata['company_name']}能力介绍.md", "file_id": f"seed_{vendor.vendor_id}"}],
        )
        db.add(cap)
        await db.flush()
        # 双轨向量：代表向量 + 简化原文块（溯源展示用）
        await vector.index_representative(str(vendor.vendor_id), cdata["tags"], cdata["summary"])
        page_text = "".join(
            f"{k}:{'、'.join(v) if isinstance(v, list) else v}\n" for k, v in cdata["tags"].items()
        )
        await vector.index_doc_chunks(str(vendor.vendor_id), f"seed_{vendor.vendor_id}",
                                      f"{vdata['company_name']}能力介绍.md", [page_text])
        created += 1
        if created % 20 == 0:
            print(f"  vendors seeded: {created}/100")
    await db.commit()
    print(f"  vendors created: {created}（其余已存在，幂等跳过）")


async def _seed_knowledge(db) -> None:
    """领域知识库：预置 12 条 + knowledge_base 向量。"""
    created = 0
    for content, category, industry in KNOWLEDGE:
        exists = (await db.execute(select(KnowledgeItem).where(KnowledgeItem.content == content))).scalar_one_or_none()
        if exists:
            continue
        item = KnowledgeItem(content=content, category=category, industry=industry, source="seed")
        db.add(item)
        await db.flush()
        created += 1
    await db.commit()
    # 向量化全部种子知识（upsert：按主键覆盖/追加，与 PG 一致；幂等）
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


async def seed() -> None:
    async with SessionLocal() as db:
        print("=== 种子数据 ===")
        await _seed_users(db)
        await _seed_vendors(db)
        await _seed_knowledge(db)
        print("=== 完成 ===")


if __name__ == "__main__":
    asyncio.run(seed())
