"""T4.5 匹配侧评估：对已确认需求快照跑 compute，记录结果 + 稳定性基线（9.3）。

- 覆盖：每条 buyer_requests 的匹配结果（命中/分数/来源）
- 稳定性：挑一条 done 快照强制重算 N 次 → best_score 标准差 ≤2 / Top-5 Jaccard ≥90%
（判定缓存 + 确定性规则保证稳定；报告存 tests/eval_match_report_v1.json）
"""
import asyncio
import json
import statistics
import sys
sys.path.insert(0, r"D:\code\xmsn-demo\xmsn-demo\backend")

from sqlalchemy import delete, select

from app.db.models import BuyerRequest, MatchResult, MatchRun
from app.db.session import SessionLocal
from app.domains.match_service import service as match_service


def _has_anchor(demand: dict | None) -> bool:
    """正向点快照（D6/D7/D8）：品类锚点 = dimensions.product_type；兼容旧扁平快照。"""
    dims = (demand or {}).get("dimensions") or {}
    pt = (dims.get("product_type") or {}).get("value")
    if pt:
        return True
    return bool((demand or {}).get("product_type"))


async def main():
    async with SessionLocal() as db:
        reqs = (await db.execute(
            select(BuyerRequest).where(BuyerRequest.deleted_at.is_(None))
        )).scalars().all()
        reqs = [r for r in reqs if _has_anchor(r.structured_demand)]
        print(f"需求快照: {len(reqs)} 条（含品类锚点）")

        cases = []
        for r in reqs:
            resp = await match_service.compute(db, str(r.request_id))
            cases.append({
                "request_id": str(r.request_id),
                "status": resp.run.status,
                "total": resp.run.total_vendors,
                "best_score": resp.run.best_score,
                "time_ms": resp.run.computation_time_ms,
                "top_vendors": [it.vendor_id for it in resp.match_results[:5]],
                "sources": sorted({it.match_source for it in resp.match_results}),
            })
        for c in cases:
            print(f"  req={c['request_id'][:8]} status={c['status']} total={c['total']} "
                  f"best={c['best_score']} src={c['sources']}")

        # 稳定性：对第一条有结果的快照强制重算 N=3
        done = [c for c in cases if c["status"] == "done"]
        stability = None
        if done:
            rid = done[0]["request_id"]
            runs = []
            for _ in range(3):
                async with SessionLocal() as d2:
                    await d2.execute(delete(MatchResult).where(MatchResult.request_id == __import__("uuid").UUID(rid)))
                    run = (await d2.execute(select(MatchRun).where(MatchRun.request_id == __import__("uuid").UUID(rid)))).scalar_one()
                    run.status = "running"
                    await d2.commit()
                    resp = await match_service.compute(d2, rid)
                    runs.append({"best": resp.run.best_score,
                                 "top": [it.vendor_id for it in resp.match_results[:5]]})
            scores = [r["best"] for r in runs if r["best"] is not None]
            tops = [set(r["top"]) for r in runs]
            jac = (len(tops[0] & tops[1]) / len(tops[0] | tops[1]) if tops and tops[0] | tops[1] else 1.0)
            stability = {
                "n": len(runs),
                "best_scores": scores,
                "score_std": round(statistics.pstdev(scores), 4) if len(scores) >= 2 else None,
                "top5_jaccard": round(jac, 4),
            }
            print(f"\n稳定性({stability['n']} 次重算): scores={scores} std={stability['score_std']} "
                  f"jaccard={stability['top5_jaccard']}")

    report = {"version": "v1", "cases": cases, "stability": stability}
    with open(r"D:\code\xmsn-demo\xmsn-demo\backend\tests\eval_match_report_v1.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print("\n报告已存: tests/eval_match_report_v1.json")


asyncio.run(main())
