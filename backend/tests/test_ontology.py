"""本体（D1）与需求 Schema（本体数据源）单测：纯逻辑，无 LLM/DB。

覆盖：本体版本/品类闭集、general 维度、品类展开（extends 共享）、
schema.py 数据源切换、label/value_type、depends_on 保留、状态机（兼容层）。
"""
import pytest  # noqa: F401  (pytest 使用)

from app.domains import ontology
from app.domains.conversation import schema as req_schema


def test_ontology_version():
    assert ontology.version() == "v1"


def test_category_closed_set_no_other():
    """D6 品类闭集：本体与 schema 均无"其他"品类。"""
    assert "其他" not in ontology.category_names()
    assert "其他" not in req_schema.CATEGORY_EXTENSIONS


def test_general_eleven_dims():
    """供需Schema §3.4 通用 11 维，product_type 居首。"""
    keys = [f["key"] for f in ontology.general_fields()]
    assert len(keys) == 11
    assert keys[0] == "product_type"
    assert {"moq", "lead_time_days", "monthly_capacity", "certifications"} <= set(keys)


def test_category_expansion_counts():
    """品类 Schema = general(11) + 消费电子通用(3) + 品类字段。"""
    assert len(ontology.fields_for("智能音箱")) == 17
    assert len(ontology.fields_for("机顶盒")) == 19
    assert len(ontology.fields_for("IoT设备")) == 18


def test_consumer_electronics_shared():
    """os/interfaces/wireless 经 extends 共享（§9 决策1 归品类）。"""
    for cat in ["智能音箱", "机顶盒", "IoT设备"]:
        keys = [f["key"] for f in ontology.category_fields(cat)]
        assert {"os", "interfaces", "wireless"} <= set(keys)


def test_schema_uses_ontology():
    """schema.py 数据源切换：FIXED_FIELDS=general、fields_for=本体展开。"""
    assert req_schema.FIXED_FIELDS == ontology.general_fields()
    assert req_schema.fields_for("智能音箱") == ontology.fields_for("智能音箱")


def test_label_of():
    assert req_schema.label_of("os", "智能音箱") == "操作系统"
    assert req_schema.label_of("moq") == "起订量"
    assert req_schema.label_of("unknown_key") == "unknown_key"


def test_value_type_of():
    assert ontology.value_type_of("moq") == "number"
    assert ontology.value_type_of("os", "智能音箱") == "enum"


def test_depends_on_preserved():
    """output_interfaces 依赖 interfaces=HDMI（显式声明不被品类锚点覆盖）。"""
    f = ontology.field_by_key("output_interfaces", "机顶盒")
    assert f is not None
    assert f["depends_on"] == [{"key": "interfaces", "values": ["HDMI"]}]


def test_category_field_anchor_dependency():
    """品类字段未显式 depends_on → 自动补品类锚点依赖。"""
    f = ontology.field_by_key("mic_array", "智能音箱")
    assert f is not None
    assert {"key": "product_type", "values": ["智能音箱"]} in f["depends_on"]


def test_state_machine_smart_speaker():
    """兼容层：状态机在智能音箱品类下正常（Step 3 前过渡）。"""
    state = {
        "product_type": {"value": "智能音箱", "state": "set"},
        "os": {"value": ["RTOS"], "state": "set"},
    }
    assert req_schema.next_unfilled(state, "智能音箱")["key"] == "certifications"
    active = [f["key"] for f in req_schema.active_fields(state, "智能音箱")]
    assert "mic_array" in active and "product_type" in active
    assert req_schema.validate_completion(state, "智能音箱")["done"] is True
