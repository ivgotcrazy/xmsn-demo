"""需求侧单测（D5-D8/D12）：正向点 + strictness + extended 结构化 + 提交门槛。纯逻辑，无 LLM/DB。"""
from app.domains.conversation import agent, service, schema as req_schema


def _pt_state():
    return {"product_type": {"value": "智能音箱", "state": "set", "strictness": "best-effort"}}


def test_merge_slot_positive_point_with_strictness():
    st = _pt_state()
    agent.merge_slot(st, {"os": {"value": ["RTOS"], "strictness": "strict"}})
    assert st["os"] == {"value": ["RTOS"], "state": "set", "strictness": "strict"}


def test_merge_slot_no_excluded_wildcard():
    """D6/D7：excluded/wildcard 不再产生（state 恒 set；value None 不入快照）。"""
    st = _pt_state()
    agent.merge_slot(st, {"interfaces": {"value": None, "state": "wildcard"}})
    assert "interfaces" not in st or st["interfaces"]["state"] == "set"


def test_merge_slot_extended_structured():
    st = _pt_state()
    agent.merge_slot(st, {}, [{"label": "外观", "value": "外壳黑色", "strictness": "strict"}])
    assert st["extended"] == [{"label": "外观", "value": "外壳黑色", "strictness": "strict"}]


def test_merge_slot_unknown_key_to_extended():
    st = _pt_state()
    agent.merge_slot(st, {"custom_color": {"value": "红色", "strictness": "best-effort"}})
    assert any(e["value"] == "红色" for e in st["extended"])


def test_write_option_strictness_default():
    st = _pt_state()
    agent.write_option(st, "mic_array", "4麦")
    assert st["mic_array"]["strictness"] == "best-effort"
    agent.write_option(st, "os", ["RTOS"], strictness="strict")
    assert st["os"]["strictness"] == "strict"


def test_snapshot_forward_points():
    """D6/D7/D8：快照 = schema_ref + dimensions{value,strictness} + extended 结构化，无 state。"""
    st = _pt_state()
    st["os"] = {"value": ["RTOS"], "state": "set", "strictness": "strict"}
    st["extended"] = [{"label": "物流", "value": "送货上门", "strictness": "best-effort"}]
    snap = service._slots_snapshot(st)
    assert snap["schema_ref"] == "category:智能音箱@v1"
    assert snap["dimensions"]["os"] == {"value": ["RTOS"], "strictness": "strict"}
    assert "state" not in snap["dimensions"]["os"]
    assert snap["extended"][0]["value"] == "送货上门"


def test_snapshot_excludes_empty_and_private():
    """快照只存明确指定点：wildcard（value None）不落档；_ 私有态不落档（D6）。"""
    st = _pt_state()
    st["os"] = {"value": None, "state": "wildcard"}
    st["_pending"] = {"key": "os", "options": []}
    snap = service._slots_snapshot(st)
    assert "os" not in snap["dimensions"]
    assert "_pending" not in snap["dimensions"]


def test_completion_gate_d12():
    """D12 门槛：仅品类 → 不满足（0 需求点）；品类+≥1 点（dimensions 或 extended）→ 满足。"""
    only_cat = _pt_state()
    assert req_schema.validate_completion(only_cat, "智能音箱")["done"] is False
    with_os = _pt_state()
    with_os["os"] = {"value": ["RTOS"], "state": "set"}
    assert req_schema.validate_completion(with_os, "智能音箱")["done"] is True
    with_ext = _pt_state()
    with_ext["extended"] = [{"label": "外观", "value": "外壳黑色", "strictness": "strict"}]
    assert req_schema.validate_completion(with_ext, "智能音箱")["done"] is True


def test_count_demand_points():
    st = _pt_state()
    st["os"] = {"value": ["RTOS"], "state": "set"}
    st["extended"] = [{"label": "外观", "value": "外壳黑色", "strictness": "strict"}]
    assert req_schema.count_demand_points(st, "智能音箱") == 2


def test_next_unfilled_skips_confirmed_unlimited():
    """D6：已确认不限的维度不再追问（_confirmed_unlimited 私有标记）。"""
    st = _pt_state()
    st["_confirmed_unlimited"] = ["certifications"]
    assert req_schema.next_unfilled(st, "智能音箱")["key"] != "certifications"


def test_to_demand_points_strictness():
    st = _pt_state()
    st["os"] = {"value": ["RTOS"], "state": "set", "strictness": "strict"}
    pts = service.to_demand_points(st)
    os_pt = next(p for p in pts if p.key == "os")
    assert os_pt.strictness == "strict"
