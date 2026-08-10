"""M7 T7.3 性能自测：对话/匹配/解释 SLO 测量（留档）。

SLO：对话<2s / 匹配<5s / 解释<3s。结果存 tests/perf_report_v1.json。
"""
import asyncio
import json
import sys
import time
sys.path.insert(0, r"D:\code\xmsn-demo\xmsn-demo\backend")
import httpx

BASE = "http://127.0.0.1:8000"


async def main():
    report = {}
    async with httpx.AsyncClient(base_url=BASE, timeout=180) as c:
        t = time.perf_counter()
        r = await c.post("/api/v1/auth/login", json={"phone": "13912345678", "password": "buyer123"})
        report["login_ms"] = int((time.perf_counter() - t) * 1000)
        h = {"Authorization": f"Bearer {r.json()['data']['access_token']}"}

        r = await c.post("/api/v1/conversation/start", headers=h, json={"user_id": "0"})
        cid = r.json()["data"]["conversation_id"]

        # 对话（自由文本 → LLM 解析）
        t = time.perf_counter()
        await c.post("/api/v1/conversation/message", headers=h,
                     json={"conversation_id": cid, "message": "机顶盒"})
        t2 = time.perf_counter()
        await c.post("/api/v1/conversation/message", headers=h,
                     json={"conversation_id": cid, "message": "Linux，网口和USB，CE认证，3000台，20天"})
        report["message_ms"] = int((time.perf_counter() - t2) * 1000)

        r = await c.post("/api/v1/conversation/confirm", headers=h, json={"conversation_id": cid})
        rid = r.json()["data"]["request_id"]

        # 匹配
        t = time.perf_counter()
        r = await c.post("/api/v1/match/compute", headers=h, json={"request_id": rid})
        report["match_ms"] = int((time.perf_counter() - t) * 1000)
        mid = r.json()["data"]["match_results"][0]["match_id"]

        # 解释（异步生成 → poll ready）
        t = time.perf_counter()
        for _ in range(30):
            d = (await c.get(f"/api/v1/match/detail/{mid}", headers=h)).json()["data"]
            if d["explanation_status"] == "ready":
                break
            await asyncio.sleep(0.5)
        report["explain_ms"] = int((time.perf_counter() - t) * 1000)

    report["slo"] = {
        "对话<2000ms": report["message_ms"] < 2000,
        "匹配<5000ms": report["match_ms"] < 5000,
        "解释<3000ms": report["explain_ms"] < 3000,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    with open(r"D:\code\xmsn-demo\xmsn-demo\backend\tests\perf_report_v1.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


asyncio.run(main())
