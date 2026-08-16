"""匹配侧单测（D1/D7/D10 + Stage0-3）：judge 四档 + strict_ok + scorer 等权 + demand_embedding_text + stage0 SQL。"""
import json

import pytest  # noqa: F401

from app.domains import ontology
from app.domains.match_service import judger, retriever, scorer, stage0


def _smart_speaker_field(key):
    return ontology.field_by_key(key, "智能音箱")


def test_judge_enum_subset():
    f = _smart_speaker_field("os")
    assert judger._judge_by_value_type(f, ["RTOS"], ["RTOS", "Android"]) == "matched"
    assert judger._judge_by_value_type(f, ["RTOS"], ["Android"]) == "unmatched"
    assert judger._judge_by_value_type(f, ["RTOS", "Linux"], ["RTOS"]) == "partial"
    assert judger._judge_by_value_type(f, ["RTOS"], None) == "missing"


def test_judge_scalar_no_partial():
    f = ontology.field_by_key("product_type")
    assert judger._judge_by_value_type(f, "智能音箱", ["智能音箱"]) == "matched"
    assert judger._judge_by_value_type(f, "智能音箱", ["机顶盒"]) == "unmatched"
    assert judger._judge_by_value_type(f, "智能音箱", None) == "missing"


def test_judge_number_direction_tolerance():
    f = ontology.field_by_key("lead_time_days")
    assert judger._judge_by_value_type(f, 30, 20) == "matched"   # 厂商≤需求
    assert judger._judge_by_value_type(f, 30, 35) == "partial"   # ≤1.5x
    assert judger._judge_by_value_type(f, 30, 60) == "unmatched"
    assert judger._judge_by_value_type(f, 30, None) == "missing"


def test_scorer_equal_weight():
    """D10 等权：match_score = round(Σ档位/N)。"""
    js = [{"verdict": "matched"}, {"verdict": "partial"}, {"verdict": "missing"}, {"verdict": "unmatched"}]
    assert scorer.score(js) == {"match_score": round((100 + 50 + 30 + 0) / 4)}
    assert scorer.score([{"verdict": "matched"}, {"verdict": "matched"}]) == {"match_score": 100}
    assert scorer.score([]) == {"match_score": 0.0}


def test_demand_embedding_text_natural():
    """D9：自然语言模板，含 label + 值 + extended。"""
    demand = {"schema_ref": "category:智能音箱@v1",
              "dimensions": {"product_type": {"value": "智能音箱", "strictness": "strict"},
                             "os": {"value": ["RTOS", "Android"], "strictness": "best-effort"}},
              "extended": [{"label": "外观", "value": "外壳黑色", "strictness": "strict"}]}
    t = retriever.demand_embedding_text(demand)
    assert "智能音箱" in t and "RTOS" in t and "外壳黑色" in t


def test_stage0_sql_enum_and_number():
    """Stage0：strict 受控维度进硬筛；best-effort 不进；品类恒硬条件（参数化）。"""
    demand = {"dimensions": {
        "product_type": {"value": "智能音箱", "strictness": "strict"},
        "certifications": {"value": ["CCC", "SRRC"], "strictness": "strict"},
        "lead_time_days": {"value": 30, "strictness": "strict"},
        "os": {"value": ["RTOS"], "strictness": "best-effort"},
    }}
    sql, params = stage0._build_sql(demand, "智能音箱")
    assert sql is not None
    assert ":pt_tag" in sql and "tag_certifications" in sql and "lead_time_days" in sql
    assert "os" not in sql  # best-effort 不进硬筛
    assert json.loads(params["pt_tag"]) == {"product_types": ["智能音箱"]}
    assert json.loads(params["tag_certifications"]) == {"certifications": ["CCC", "SRRC"]}
    assert params["num_lead_time_days"] == 30


def test_stage0_sql_only_category():
    demand = {"dimensions": {"product_type": {"value": "智能音箱", "strictness": "strict"}}}
    sql, params = stage0._build_sql(demand, "智能音箱")
    assert sql is not None and ":pt_tag" in sql
    assert json.loads(params["pt_tag"]) == {"product_types": ["智能音箱"]}


def test_stage0_sql_no_dimensions():
    sql, _ = stage0._build_sql({}, None)
    assert sql is None
