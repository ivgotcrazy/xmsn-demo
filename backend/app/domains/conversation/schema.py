"""需求 Schema（T3.1）：固定字段 + 品类扩展 + 三态。实现以架构 6.6 / 代理 LLD 0.1 为准。

- 固定字段（共通维度，参与通道B计分）
- 品类扩展（按 product_type 加载：机顶盒/智能音箱/IoT设备/其他）
- 开放扩展（extra_constraints）不在此静态 Schema，见对话合并逻辑
- 三态：set（已指定）/ wildcard（未指定通配）/ excluded（明确排除）
"""
from __future__ import annotations

from enum import Enum


class SlotTriState(str, Enum):
    SET = "set"
    WILDCARD = "wildcard"
    EXCLUDED = "excluded"


# 固定字段（架构 6.6.1）
FIXED_FIELDS: list[dict] = [
    {"key": "product_type", "label": "产品类型", "kind": "single", "required": True,
     "options": ["机顶盒", "智能音箱", "IoT设备", "其他"]},
    {"key": "os", "label": "操作系统", "kind": "multi", "options": ["Linux", "Android", "RTOS", "其他"]},
    {"key": "interfaces", "label": "接口", "kind": "multi", "options": ["网口", "USB", "HDMI", "GPIO", "其他"]},
    {"key": "certifications", "label": "认证", "kind": "multi", "options": ["CE", "FCC", "CCC", "SRRC", "ISO9001", "其他"]},
    {"key": "moq", "label": "起订量", "kind": "number"},
    {"key": "lead_time_days", "label": "交期(天)", "kind": "number"},
    {"key": "application_scenario", "label": "应用场景", "kind": "single"},
    {"key": "customization_needs", "label": "定制需求", "kind": "single"},
    {"key": "budget_range", "label": "预算范围", "kind": "single", "optional": True},
]

# 品类扩展（架构 6.6.2）
CATEGORY_EXTENSIONS: dict[str, list[dict]] = {
    "机顶盒": [
        {"key": "decode_capability", "label": "解码能力", "kind": "multi", "options": ["H.264", "H.265", "AV1", "HDR"]},
        {"key": "soc_platform", "label": "主控平台", "kind": "single", "options": ["Amlogic", "Allwinner", "HiSilicon", "Rockchip"]},
        {"key": "wireless", "label": "无线", "kind": "multi", "options": ["WiFi", "蓝牙", "无"]},
        {"key": "tv_standard", "label": "电视制式", "kind": "multi", "options": ["DVB-C", "DVB-T", "ATSC", "ISDB", "无"]},
        {"key": "output_interfaces", "label": "输出接口", "kind": "multi", "options": ["HDMI", "AV", "SPDIF"]},
        {"key": "memory_storage", "label": "存储配置", "kind": "single"},
    ],
    "智能音箱": [
        {"key": "mic_array", "label": "麦克风阵列", "kind": "single", "options": ["2麦", "4麦", "6麦"]},
        {"key": "speaker_power", "label": "喇叭功率", "kind": "single", "options": ["3W", "5W", "10W"]},
        {"key": "voice_assistant", "label": "语音助手", "kind": "single", "options": ["自研", "接入第三方"]},
        {"key": "wireless", "label": "无线", "kind": "multi", "options": ["WiFi", "蓝牙"]},
    ],
    "IoT设备": [
        {"key": "comm_protocol", "label": "通信协议", "kind": "multi", "options": ["BLE", "WiFi", "Zigbee", "LoRa", "NB-IoT", "4G"]},
        {"key": "power_supply", "label": "供电方式", "kind": "single", "options": ["电池", "市电", "USB"]},
        {"key": "ip_rating", "label": "防护等级", "kind": "single", "options": ["IP54", "IP65", "无"]},
        {"key": "sensors", "label": "传感器", "kind": "multi", "options": ["温度", "湿度", "运动", "无"]},
    ],
    "其他": [],
}

# 完成判定"关键维度"（代理 LLD 0.4）：品类锚点之外的必填关键项
KEY_DIMS = ["os", "interfaces", "certifications"]


def fields_for(product_type: str | None) -> list[dict]:
    """当前品类的完整字段（固定 + 品类扩展）。"""
    if not product_type:
        return FIXED_FIELDS
    return FIXED_FIELDS + CATEGORY_EXTENSIONS.get(product_type, [])


def label_of(key: str, product_type: str | None = None) -> str:
    for f in fields_for(product_type):
        if f["key"] == key:
            return f["label"]
    return key


def next_unfilled(state: dict, product_type: str | None) -> dict | None:
    """按字段顺序返回下一个未指定且必填的字段（用于追问）；无则 None。"""
    for f in fields_for(product_type):
        if f.get("optional"):
            continue
        sv = state.get(f["key"])
        if not sv or sv.get("state") != SlotTriState.SET.value or _empty(sv.get("value")):
            return f
    return None


def _empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, list):
        return len(v) == 0
    return str(v).strip() == ""
