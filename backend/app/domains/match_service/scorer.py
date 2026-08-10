"""综合打分（T4.3）——《匹配详细设计》第 5 章。

- param_hit_rate：分母=已指定参数权重和（4.4），VERDICT_SCORE matched1.0/partial0.5/missing0.3/unmatched0.0
- score：⌊100×(0.4·s_sem + 0.6·s_param)⌋；关键参数 unmatched → critical_fail → 封顶 50（5.2）
- 阈值 30 过滤在 service 执行
"""
from __future__ import annotations

from .judger import CRITICAL, MATCHED, PARTIAL, MISSING, UNMATCHED

VERDICT_SCORE = {MATCHED: 1.0, PARTIAL: 0.5, MISSING: 0.3, UNMATCHED: 0.0}
BLEND_SEM = 0.4
BLEND_PARAM = 0.6
CRITICAL_CAP = 50.0
MIN_MATCH_SCORE = 30.0


def param_hit_rate(judgements: list[dict]) -> float:
    """分母=已指定参数权重和；无已指定参数 → 1.0（不稀释）。"""
    num = sum(j.get("weight", 0.0) * VERDICT_SCORE.get(j.get("verdict"), 0.0) for j in judgements)
    den = sum(j.get("weight", 0.0) for j in judgements)
    return num / den if den > 0 else 1.0


def score(semantic: float, judgements: list[dict]) -> dict:
    """综合打分 + 关键参数封顶。返回 {match_score, param_hit_rate, critical_fail}。"""
    rate = param_hit_rate(judgements)
    raw = 100.0 * (BLEND_SEM * semantic + BLEND_PARAM * rate)
    crit = any(
        j.get("param") in CRITICAL and j.get("verdict") == UNMATCHED
        for j in judgements
    )
    if crit:
        raw = min(raw, CRITICAL_CAP)
    return {
        "match_score": int(raw // 1),
        "param_hit_rate": round(rate, 4),
        "critical_fail": crit,
    }
