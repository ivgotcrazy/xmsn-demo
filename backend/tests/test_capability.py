"""能力侧单测（D1 同 key / D3 soft_tags / D9 summary）：纯逻辑，无 LLM/DB。"""
from app.domains.vendor_service import extractor, validator


def test_extractor_prompt_same_key():
    """D1：PROMPT 用 os 而非 os_support；D9 summary ≤400 字；D3 soft_tags。"""
    assert "os_support" not in extractor.PROMPT_PARSE
    assert '"os": ["string"]' in extractor.PROMPT_PARSE
    assert "400字" in extractor.PROMPT_PARSE
    assert "soft_tags" in extractor.PROMPT_PARSE


def test_validator_same_key_normalize():
    """D1 同 key 归一 + D3 soft_tags 透传 + D4 source 溯源。"""
    extracted = {
        "structured_tags": {"os": ["RTOS", "Android"], "moq": 500},
        "soft_tags": ["远场拾音", "可定制外壳"],
        "summary_text": "专注智能音箱方案，支持RTOS/Android，月产能50万台。",
        "sources": {"os": {"doc_id": "d1", "doc_name": "n", "page": 1, "chunk_text": "t", "confidence": 0.9}},
    }
    tags, completeness, source_map, summary, soft_tags = validator.validate(extracted)
    assert tags["os"] == ["RTOS", "Android"]
    assert "os_support" not in tags
    assert soft_tags == ["远场拾音", "可定制外壳"]
    assert summary == "专注智能音箱方案，支持RTOS/Android，月产能50万台。"
    assert source_map["os"]["doc_id"] == "d1"


def test_validator_completeness_counts_os():
    """os 计入 HARD_FIELDS（completeness 分母=7）。"""
    extracted = {
        "structured_tags": {
            "process_types": ["SMT"], "certifications": ["CE"], "os": ["RTOS"],
            "interfaces": ["USB"], "moq": 500, "lead_time_days": 20, "monthly_capacity": 50,
        },
        "soft_tags": [],
        "summary_text": "s",
    }
    tags, completeness, *_ = validator.validate(extracted)
    assert completeness == 1.0
    assert tags["os"] == ["RTOS"]


def test_validator_missing_hard_os_empty():
    """os 缺失 → 置空数组，不计完备度。"""
    extracted = {"structured_tags": {}, "soft_tags": [], "summary_text": "s"}
    tags, completeness, *_ = validator.validate(extracted)
    assert tags["os"] == []
    assert completeness < 1.0
