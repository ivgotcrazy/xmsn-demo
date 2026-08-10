"""匹配引擎主流程（T4.3/T4.4）——《匹配详细设计》第 2/6/7/8 章。

compute(request_id)：
1. 加载 buyer_requests 快照 + match_runs（confirm 已建 running 占位）
2. 幂等：已 done/empty 秒回现有结果（02A 确认弹窗与 02B 加载重复调用不重算）
3. 通道A：需求向量 ANN（embedding 失败 → 标签检索兜底 hybrid）
4. 排除项硬过滤（4.5）→ 通道B judge → 综合打分 + 阈值 30 过滤
5. 排序 → 清旧结果 → 落库 match_results（verdict 三组）→ 更新 match_runs（done/empty + 物化统计）
"""
from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BuyerRequest, MatchResult, MatchRun, Vendor, VendorCapability
from app.domains.conversation import schema as req_schema
from app.domains.match_service import judger, retriever, scorer
from app.schemas.common import err_404
from app.schemas.conversation import DemandPoint
from app.schemas.match import (
    MatchComputeResponse,
    MatchDetailResponse,
    MatchItem,
    MatchParam,
    MatchRun as MatchRunSchema,
)

logger = logging.getLogger("xmsn.match")


# ---------- 工具 ----------

def _norm_slot(sv):
    """兼容三态 dict({value,state}) / 纯值 / excluded 标记({excluded:True,value}) → (value, state)。"""
    if isinstance(sv, dict):
        if "state" in sv:
            return sv.get("value"), sv.get("state")
        if sv.get("excluded"):
            return sv.get("value"), "excluded"
        return sv, "set"
    return sv, "set"


def _demand_points(demand: dict) -> list[DemandPoint]:
    """structured_demand → DemandPoint 列表（02B 左栏展示）。"""
    pts: list[DemandPoint] = []
    for k, sv in (demand or {}).items():
        v, st = _norm_slot(sv)
        if st != "set":
            continue
        if v in (None, "", []):
            continue
        if isinstance(v, list):
            v = [str(x) for x in v]
        else:
            v = str(v)
        pts.append(DemandPoint(key=k, label=req_schema.label_of(k, None),
                               value=v, confidence=1.0))
    extra = demand.get("extra_constraints")
    if isinstance(extra, list):
        for c in extra:
            pts.append(DemandPoint(key="extra_constraints", label="扩展需求",
                                   value=str(c), confidence=0.9))
    return pts


def _match_param(j: dict) -> MatchParam:
    """ParamJudgement/解释条目 → 前端 MatchParam（label 规范化 + note + source 溯源）。"""
    dv = j.get("demand_value")
    sv = j.get("supply_value") or "未声明"
    value = f"需求 {dv} / 厂商 {sv}"
    note = j.get("note")
    if note:
        value += f"（{note}）"
    src = j.get("source") or {}
    src = src if isinstance(src, dict) else {}
    return MatchParam(
        key=j["param"],
        label=req_schema.label_of(j["param"], None),
        value=value,
        verdict=j["verdict"],
        source_doc_id=src.get("doc_id"),
        source_doc_name=src.get("doc_name"),
        source_page=src.get("page"),
        source_text=src.get("chunk_text"),
    )


def _excluded_hard_filter(demand: dict, tags: dict) -> bool:
    """排除项硬过滤（4.5）：厂商能力命中排除值 → 直接淘汰。"""
    for param, _w, d_field, s_field, _k, _c in judger.PARAM_MAP:
        if not s_field:
            continue
        ex = judger.excluded_values(demand, d_field)
        if not ex:
            continue
        s_val = tags.get(s_field)
        if s_val is None:
            continue
        s_set = set(s_val) if isinstance(s_val, list) else {str(s_val)}
        if any(str(x) in s_set for x in ex):
            return True
    return False


async def _run_of(db: AsyncSession, request_id: uuid.UUID) -> MatchRun:
    res = await db.execute(select(MatchRun).where(MatchRun.request_id == request_id))
    run = res.scalar_one_or_none()
    if not run:
        run = MatchRun(request_id=request_id, status="running", total_vendors=0, computation_time_ms=0)
        db.add(run)
        await db.commit()
        await db.refresh(run)
    return run


async def _load_caps(db: AsyncSession, vendor_ids: list[str]) -> dict[str, VendorCapability]:
    if not vendor_ids:
        return {}
    vids = [uuid.UUID(v) for v in vendor_ids]
    res = await db.execute(select(VendorCapability).where(VendorCapability.vendor_id.in_(vids)))
    return {str(c.vendor_id): c for c in res.scalars().all()}


async def _load_vendors(db: AsyncSession, vendor_ids: list[str]) -> dict[str, Vendor]:
    if not vendor_ids:
        return {}
    vids = [uuid.UUID(v) for v in vendor_ids]
    res = await db.execute(select(Vendor).where(Vendor.vendor_id.in_(vids)))
    return {str(v.vendor_id): v for v in res.scalars().all()}


async def _build_items(db: AsyncSession, rows: list[dict]) -> list[MatchItem]:
    """rows（含 vendor_id）→ 联厂商/档案 → MatchItem。"""
    caps = await _load_caps(db, [r["vendor_id"] for r in rows])
    vendors = await _load_vendors(db, [r["vendor_id"] for r in rows])
    items: list[MatchItem] = []
    for r in rows:
        v = vendors.get(r["vendor_id"])
        cap = caps.get(r["vendor_id"])
        matched = [j for j in r["judgements"] if j["verdict"] == judger.MATCHED]
        unmatched = [j for j in r["judgements"] if j["verdict"] == judger.UNMATCHED]
        items.append(MatchItem(
            match_id=r["match_id"],
            vendor_id=r["vendor_id"],
            company_name=v.company_name if v else "未知厂商",
            location=v.location if v else None,
            summary=(cap.summary_text if cap else None),
            match_score=r["match_score"],
            semantic_score=r["semantic_score"],
            param_hit_rate=r["param_hit_rate"],
            critical_fail=r["critical_fail"],
            match_source=r["match_source"],
            matched_count=len(matched),
            unmatched_count=len(unmatched),
        ))
    return items


# ---------- 主流程 ----------

async def compute(db: AsyncSession, request_id: str) -> MatchComputeResponse:
    t0 = time.perf_counter()
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise err_404("需求档案不存在")
    req = await db.get(BuyerRequest, rid)
    if not req or req.deleted_at is not None:
        raise err_404("需求档案不存在")
    demand = req.structured_demand or {}
    run = await _run_of(db, rid)

    # 幂等：已 done/empty → 秒回现有结果（02A 确认弹窗与 02B 加载重复调用不重算）
    if run.status in ("done", "empty"):
        rows = await _load_existing_rows(db, rid, run)
        items = await _build_items(db, rows)
        # 补触发未解释的（幂等秒回也保证解释生成：历史/新结果 detail 不永久 pending）
        await _enqueue_missing_explains(db, rid)
        return MatchComputeResponse(run=_run_schema(run), match_results=items,
                                    demand_points=_demand_points(demand))

    # 清旧结果（重匹配覆盖，7.3）
    await db.execute(delete(MatchResult).where(MatchResult.request_id == rid))
    await db.commit()

    # 通道A（embedding 失败 → hybrid 标签兜底）
    a_source = "llm"
    try:
        cands = await retriever.retrieve(demand)
        if not cands:
            a_source = "llm"
    except Exception as exc:  # noqa: BLE001
        logger.warning("channelA embed failed, tag fallback: %s", exc)
        cands = await retriever.tag_search(demand)
        a_source = "hybrid"

    caps = await _load_caps(db, [c["vendor_id"] for c in cands])
    rows: list[dict] = []
    for cand in cands:
        cap = caps.get(cand["vendor_id"])
        if not cap or not cap.structured_tags:
            continue
        tags = cap.structured_tags
        if _excluded_hard_filter(demand, tags):
            continue  # 排除项硬过滤（4.5）
        judgements, b_source = await judger.judge(demand, tags)
        source = "rule" if b_source == "rule" else a_source  # 通道B 降级优先标注
        sc = scorer.score(cand["semantic_score"], judgements)
        if sc["match_score"] < scorer.MIN_MATCH_SCORE:
            continue  # 阈值 30 剔除
        rows.append({
            "vendor_id": cand["vendor_id"],
            "match_score": sc["match_score"],
            "semantic_score": round(cand["semantic_score"], 4),
            "param_hit_rate": sc["param_hit_rate"],
            "critical_fail": sc["critical_fail"],
            "match_source": source,
            "judgements": judgements,
        })

    rows.sort(key=lambda r: -r["match_score"])
    computation_ms = int((time.perf_counter() - t0) * 1000)

    # 落库 match_results（verdict 三组，打分用）
    top_match_ids: list[str] = []
    for r in rows:
        mr = MatchResult(
            run_id=run.run_id, request_id=rid, vendor_id=uuid.UUID(r["vendor_id"]),
            match_score=r["match_score"], semantic_score=r["semantic_score"],
            param_hit_rate=r["param_hit_rate"], critical_fail=r["critical_fail"],
            match_source=r["match_source"],
            matched_params=[j for j in r["judgements"] if j["verdict"] == judger.MATCHED],
            partial_params=[j for j in r["judgements"] if j["verdict"] in (judger.PARTIAL, judger.MISSING)],
            unmatched_params=[j for j in r["judgements"] if j["verdict"] == judger.UNMATCHED],
        )
        db.add(mr)
        await db.flush()  # 取 match_id（异步解释触发用）
        top_match_ids.append(str(mr.match_id))
    # 更新 match_runs 物化统计
    run.status = "done" if rows else "empty"
    run.total_vendors = len(rows)
    run.best_score = float(rows[0]["match_score"]) if rows else None
    run.computation_time_ms = computation_ms
    await db.commit()

    # 异步触发 Top-5 解释（T5.2，TaskQueue；不阻塞 compute）
    if top_match_ids:
        from app.core.queue import queue
        for mid in top_match_ids[:5]:
            await queue.enqueue("match_explain", {"match_id": mid})

    if rows:
        saved = await _load_existing_rows(db, rid, run)
        items = await _build_items(db, saved)
    else:
        items = []
    return MatchComputeResponse(run=_run_schema(run), match_results=items,
                                demand_points=_demand_points(demand))


async def _enqueue_missing_explains(db: AsyncSession, rid: uuid.UUID) -> None:
    """幂等秒回时补触发 ai_comment 未生成的匹配解释（M5，避免历史结果永久 pending）。"""
    from app.core.queue import queue

    res = await db.execute(
        select(MatchResult.match_id).where(MatchResult.request_id == rid, MatchResult.ai_comment.is_(None))
    )
    for (mid,) in res.all():
        await queue.enqueue("match_explain", {"match_id": str(mid)})


async def _load_existing_rows(db: AsyncSession, rid: uuid.UUID, run: MatchRun) -> list[dict]:
    """读已落库 match_results → rows 结构（含 judgement 三组拼回）。"""
    res = await db.execute(
        select(MatchResult).where(MatchResult.request_id == rid).order_by(MatchResult.match_score.desc())
    )
    rows: list[dict] = []
    for mr in res.scalars().all():
        judgements = (mr.matched_params or []) + (mr.partial_params or []) + (mr.unmatched_params or [])
        rows.append({
            "vendor_id": str(mr.vendor_id),
            "match_id": str(mr.match_id),
            "match_score": mr.match_score or 0,
            "semantic_score": mr.semantic_score or 0,
            "param_hit_rate": mr.param_hit_rate or 0,
            "critical_fail": mr.critical_fail,
            "match_source": mr.match_source,
            "judgements": judgements,
        })
    return rows


def _run_schema(run: MatchRun) -> MatchRunSchema:
    return MatchRunSchema(
        run_id=str(run.run_id), request_id=str(run.request_id), status=run.status,
        total_vendors=run.total_vendors, best_score=run.best_score,
        computation_time_ms=run.computation_time_ms, created_at=run.created_at,
    )


async def detail(db: AsyncSession, match_id: str) -> MatchDetailResponse:
    """匹配详情：verdict 三组（M4 判定已就绪）；AI 评语/原文溯源 M5 补。"""
    try:
        mid = uuid.UUID(match_id)
    except ValueError:
        raise err_404("匹配结果不存在")
    mr = await db.get(MatchResult, mid)
    if not mr:
        raise err_404("匹配结果不存在")
    vendor = await db.get(Vendor, mr.vendor_id)
    # M5 异步解释：ai_comment 生成后 ready；未生成返回 pending（前端轮询显示"理由生成中…"）
    ready = mr.ai_comment is not None
    return MatchDetailResponse(
        match_id=str(mr.match_id),
        request_id=str(mr.request_id),
        vendor_id=str(mr.vendor_id),
        company_name=vendor.company_name if vendor else "未知厂商",
        matched_params=[_match_param(j) for j in (mr.matched_params or [])],
        partial_params=[_match_param(j) for j in (mr.partial_params or [])],
        unmatched_params=[_match_param(j) for j in (mr.unmatched_params or [])],
        ai_comment=mr.ai_comment,
        explanation_status="ready" if ready else "pending",
    )
