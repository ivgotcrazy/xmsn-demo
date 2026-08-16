"""Stage3 打分（AI核心 §5.3.4，D10）：需求点等权平均，四档 100/50/30/0。

- match_score = round(Σ需求点匹配度档位 / 需求点数)（0-100；分母=已指定点数，D12 已拦 0 点提交）
- 阈值 60（D10）；semantic_score 只做召回不进最终分（Stage1 产出）
- 无权重（D10）；importance 由 strictness 表达（strict 未满足 → strict_ok=false 供 Stage4 risk_warning）
"""
from __future__ import annotations

from .judger import MATCHED, PARTIAL, MISSING, UNMATCHED

VERDICT_SCORE = {MATCHED: 100, PARTIAL: 50, MISSING: 30, UNMATCHED: 0}
MIN_MATCH_SCORE = 60.0  # 阈值 60（D10）


def score(judgements: list[dict]) -> dict:
    """match_score = round(Σ档位 / 需求点数)；无需求点 → 0（不应发生，D12 已拦 0 点）。"""
    if not judgements:
        return {"match_score": 0.0}
    total = sum(VERDICT_SCORE.get(j.get("verdict"), 0) for j in judgements)
    return {"match_score": round(total / len(judgements))}

