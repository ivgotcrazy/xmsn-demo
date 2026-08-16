# 需脉枢纽 · 供需 Schema 设计（需求 Schema + 能力 Schema）

> 版本：v1.3 ｜ 状态：设计（需求 Schema 已同步 D5-D11 + 术语统一；能力 Schema 待评审） ｜ 更新：2026-08-16
>
> 依据：《AI核心总体架构设计v2》第 4 章（能力维度本体，D1 统一同 key）+《代工厂能力模型》（领域输入）。
> 两个 Schema 是系统实现的最关键契约：**需求侧能问什么、厂商侧能萃什么、匹配能比什么** 全部由此派生。

---

## 0. 定位

- 本文档定义**统一的能力维度本体**，以及由它投影出的**需求 Schema** 与**能力 Schema**。
- 三个子系统的共同语言：Agent（需求萃取）、提取器（厂商萃取）、匹配引擎（判定）都以本体为准。
- **同 key**（D1）：消除现有 os vs os_support 这类映射层。

---

## 1. 设计原则

1) **单一本体、双侧投影**：本体是唯一维度字典；需求 Schema、能力 Schema 是它的"需求侧视图"与"能力侧视图"。
2) **值形态决定判定、来源决定萃取**：`value_type`（enum/scalar/number/text）→ 匹配判定方式；`provenance`（general/category）→ 萃取/采集方式；两者正交。
3) **需求侧重"要求"（D6/D7）**：维度收敛为**正向指定点** `{value, strictness}`；`strictness` 两档（strict 必须 / best-effort 尽力）；wildcard=未指定不入档（Agent 私有标记）；excluded 已移除。
4) **能力侧重"供给"**：维度带 `confidence` + `source`（溯源），本体外能力走 **soft 软层**（D3）。
5) **数据驱动**：本体存 JSON 配置，新增品类/维度不改代码。

---

## 2. 需求点 schema：统一维度元数据（本体条目）

> 每个维度条目 = **需求点 schema**：定义"这个维度长什么样"；**需求点**是它的**实例**（维度元数据 + `value`/`strictness`，§3.1）。同一条目供能力侧使用（`applicable` 区分）。

```json
{
  "key": "os",                 // 两侧同 key
  "label": "操作系统",          // 通用展示名
  "provenance": "category",    // general 通用 / category 品类
  "value_type": "enum",        // enum多选 / scalar单值 / number数值 / text自由文本
  "kind": "multi",             // enum: single/multi；其余 single
  "options": ["Linux","Android","RTOS","其他"],  // enum/scalar 候选
  "direction": null,           // number: "upper"(s≤d达标，需求上限如交期) / "lower"(s≥d达标，需求下限如产能)
  "unit": null,                // number 单位：台/天/万元
  "compare_tolerance": 1.5,    // number partial 容差倍数
  "depends_on": null,          // 依赖联动：[{"key":"product_type","values":["智能音箱"]}]
  "applicable": "both"         // demand / capability / both（该维度在哪侧可用）
}
```

> 严格度（strict/best-effort）为**全局两档常量**（D7）：所有维度均支持，不再作为本体条目字段（`strictness_support` 已移除）；`partial` 不是用户严格度选项，仅作为**判定结果 verdict**（matched/partial/missing/unmatched）保留（§6.1）。

---

## 3. 需求 Schema

需求侧两个层次：
- **需求点 schema**（§2）：单个维度的元数据（本体条目）。
- **品类 Schema**：某品类的**全量需求维度字典** = **通用 schema + 品类 schema + 扩展**（如"智能音箱" = 通用字段 + 音箱品类字段 + 扩展约束）。

对应实例：
- **需求点** = 需求点 schema 的**实例**（§3.1/§3.7）。
- **需求档案/快照** = 品类 Schema 的**实例**（§3.7，一组需求点，版本化持久化）。

### 3.1 需求点 = 需求点 schema 的实例
- **需求点 schema**（§2 维度元数据）定义"这个维度长什么样"；**需求点** = 它的**实例**（维度元数据 + `value`/`strictness`）。
- 需求点**不是"整个品类 Schema 的实例"**——品类 Schema 的实例是**需求档案**（§3.7）。
- Agent 私有工作态（`_pending`/`_recommend` 等）不属于需求点。

### 3.2 需求点状态语义（D6 收敛：移除 excluded）
| 状态 | 含义 | 处理 |
| --- | --- | --- |
| 正向指定 | 用户明确给出值（"要 Android + RTOS"） | 入档（需求点实例，§3.7），参与判定 |
| 未指定（wildcard） | 用户未提或表示不限（"系统无所谓"） | **不入档**，降为 Agent 私有标记（"已确认不限，勿再追问"）；不参与判定、不计分母 |
| 排除（excluded） | 用户明确"不要X"（"不要华为系"） | **已移除（D6）**：能力可加、多余能力不 disqualify；"不要X"由 Agent 语义处理（不加入需求集；厂商身份/合规类排除另设独立厂商属性维度） |

### 3.3 strictness 两档 → verdict 接受规则（D7）
| strictness | 含义 | 接受范围 | 说明 |
| --- | --- | --- | --- |
| strict（必须） | 硬性要求 | 仅 `matched` | 前置 **Stage0 SQL 硬筛**（枚举/数值含容差，零 LLM）；Stage2 未满足标红 |
| best-effort（尽力） | 倾向性要求 | 全部 | 等权计分（默认，D10） |

> **关键区分（D7）**：去掉的是"用户严格度选项"中的 partial 档；**verdict 的 partial（厂商部分满足的判定结果：matched/partial/missing/unmatched）保留**（见 §6.1）。
> strict 的 text/扩展需求：不走 Stage0 SQL，走 Stage2 语义 strict（LLM 判定）。
> `strictness` 由 Agent 从语言自动推断（"必须/一定要/只要"→strict；"最好/优先/希望"→best-effort；默认=best-effort），确认框只读展示可微调（D7）。

### 3.4 通用 Schema（所有品类共用的需求维度，provenance=general）

> 通用 Schema 是**每个品类 Schema 的公共部分**（需求侧）；下面是它的需求点 schema 定义。完整本体配置（含能力侧）见 §7。

```json
{
  "product_type":         {"label": "产品类型", "value_type": "scalar", "kind": "single",
                            "options": ["机顶盒", "智能音箱", "IoT设备"], "applicable": "both"},
  "certifications":       {"label": "认证", "value_type": "enum", "kind": "multi",
                            "options": ["CE", "FCC", "CCC", "SRRC", "ISO9001", "其他"], "applicable": "both"},
  "moq":                  {"label": "起订量", "value_type": "number", "direction": "upper", "unit": "台", "applicable": "both"},
  "lead_time_days":       {"label": "交期(天)", "value_type": "number", "direction": "upper", "unit": "天", "applicable": "both"},
  "monthly_capacity":     {"label": "月产能", "value_type": "number", "direction": "lower", "unit": "台", "applicable": "both"},
  "process_types":        {"label": "制程能力", "value_type": "enum", "kind": "multi", "applicable": "both"},
  "application_scenario": {"label": "应用场景", "value_type": "text", "applicable": "demand"},
  "customization_needs":  {"label": "定制需求", "value_type": "text", "applicable": "demand"},
  "budget_range":         {"label": "预算范围", "value_type": "text", "applicable": "demand"},
  "service_years":        {"label": "服务年限", "value_type": "number", "direction": "lower", "unit": "年", "applicable": "both"},
  "industry_cases":       {"label": "行业经验/案例", "value_type": "text", "applicable": "both"}
}
```

### 3.5 品类 Schema（某品类的全量需求维度 = 通用 Schema + 品类维度 + 扩展）

> 每个品类的**品类 Schema** 由三部分组成：**§3.4 通用 Schema + 下述品类维度 + §3.6 扩展**。
> 下面是首批品类的需求点 schema 定义（provenance=category）。

**消费电子通用（智能音箱 / 机顶盒 / IoT 共用）**

```json
{
  "os":         {"label": "操作系统", "value_type": "enum", "kind": "multi", "options": ["Linux", "Android", "RTOS", "其他"]},
  "interfaces": {"label": "接口", "value_type": "enum", "kind": "multi", "options": ["网口", "USB", "HDMI", "GPIO", "其他"]},
  "wireless":   {"label": "无线", "value_type": "enum", "kind": "multi"}
}
```

**智能音箱（品类 Schema = §3.4 通用 + 以下 + 扩展）**

```json
{
  "mic_array":       {"label": "麦克风阵列", "value_type": "enum", "kind": "single", "options": ["2麦", "4麦", "6麦"]},
  "speaker_power":   {"label": "喇叭功率", "value_type": "enum", "kind": "single"},
  "voice_assistant": {"label": "语音助手", "value_type": "enum", "kind": "single"}
}
```

**机顶盒（品类 Schema = §3.4 通用 + 以下 + 扩展）**

```json
{
  "decode_capability": {"label": "解码能力", "value_type": "enum", "kind": "multi"},
  "soc_platform":      {"label": "主控平台", "value_type": "enum", "kind": "single"},
  "tv_standard":       {"label": "电视制式", "value_type": "enum", "kind": "multi"},
  "output_interfaces": {"label": "输出接口", "value_type": "enum", "kind": "multi"},
  "memory_storage":    {"label": "存储配置", "value_type": "scalar", "kind": "single"}
}
```

**IoT 设备（品类 Schema = §3.4 通用 + 以下 + 扩展）**

```json
{
  "comm_protocol": {"label": "通信协议", "value_type": "enum", "kind": "multi"},
  "power_supply":  {"label": "供电方式", "value_type": "enum", "kind": "single"},
  "ip_rating":     {"label": "防护等级", "value_type": "enum", "kind": "single"},
  "sensors":       {"label": "传感器", "value_type": "enum", "kind": "multi"}
}
```

### 3.6 扩展（extra_constraints → extended，D8 方案 D 定案）
- 需求侧永远可填的**自由需求点**，每条结构化：`{label, value, strictness}`。
  - `value`：约束语义短语（如"外壳黑色" / "送货上门"）。
  - `label`：**必填**自由展示标签（LLM 生成简洁类别短语，如"外观"/"物流"），供前端分组/确认框展示；**非受控 key**、不参与匹配、不进本体。
  - `strictness`：两档（strict/best-effort），与 dimensions 一致，确认框可微调（D7）。
  - 示例（扩展需求点实例）：
    ```json
    [
      {"label": "外观", "value": "外壳黑色", "strictness": "strict"},
      {"label": "物流", "value": "送货上门", "strictness": "best-effort"}
    ]
    ```
- 匹配走 **soft 语义通道**（向量，strict 阈值 0.8）；不参与本体精确判定。
- **promote 机制（D8）**：同类扩展约束高频出现（按 label 聚类，如"外观"被多买方提及）→ 固化进本体维度配置，此后直接进 `dimensions`（D1 数据驱动，新增维度不改代码）。

### 3.7 需求档案（= 当前需求 = 品类 Schema 的实例，buyer_requests.structured_demand）
- **需求档案 = 品类 Schema 的实例**：一组需求点（各为需求点 schema 的实例）；**前端"当前需求"就是需求档案本身**（同一概念，D5）——**提交 = 对它的版本化快照**（vN），不再单独定义。
- **提交门槛（D12）**：品类锚定 + **至少 1 个需求点**（dimensions 或 extended 非空）+ 用户确认；**不允许 0 需求点提交**（后台校验拦截），规避 match_score 分母=0。
- 档案**只存明确设置的需求点**（正向指定点；wildcard 不入档、无 excluded、strictness 两档），并通过 **`schema_ref`** 指向其品类 Schema（定义），**不内嵌 schema**（D1 单一本体）。
- **前端展示（D5）**：按 key 从 schema_ref 指向的品类 Schema 取 `label`/`options`，与实例的 `value`/`strictness` 对齐即得"当前需求"面板（**无映射**，字典 + 实例按 key 对齐）；扩展需求点（extended）也属当前需求，前端按数组序展示（label 不保证唯一，用索引作渲染 key）。
- 持久化格式与《AI核心总体架构设计v2》§9 契约一致：`{schema_ref, dimensions: {key: {value, strictness}}, extended: [{label, value, strictness}], version}`（值实例 + schema_ref 引用，label/options 由品类 Schema 重建）。

```json
{
  "schema_ref": "category:智能音箱@v1",
  "dimensions": {
    "product_type": {"value": "智能音箱", "strictness": "strict"},
    "os": {"value": ["RTOS", "Android"], "strictness": "best-effort"},
    "certifications": {"value": ["CCC", "SRRC"], "strictness": "strict"},
    "interfaces": {"value": ["USB", "HDMI"], "strictness": "best-effort"},
    "moq": {"value": 500, "strictness": "best-effort"},
    "application_scenario": {"value": "家庭客厅", "strictness": "best-effort"}
  },
  "extended": [
    {"label": "外观", "value": "外壳黑色", "strictness": "strict"},
    {"label": "物流", "value": "送货上门", "strictness": "best-effort"}
  ],
  "version": 1
}
```

---

## 4. 能力 Schema

### 4.1 能力项结构（一个维度在能力侧的表示）
```json
{ "key": "os", "value": ["Android"], "confidence": 0.9, "source": {"doc_id":"...","doc_name":"...","page":1,"chunk_text":"..."} }
```

### 4.2 硬层（structured）：通用 + 品类维度
- 与需求侧**同 key**（3.4 / 3.5 中 `capability=✓` 的维度）。
- 能力侧用 `completeness`（硬维度缺失计入完备度）；无需求侧采集级别（demand_level 已移除，D11：匹配端无必填、采集只靠品类锚定 + LLM 追问）。

### 4.3 soft 软层（本体外能力的承接层，D3）
```json
"soft": {
  "tags": ["三防", "声学调校", "欧美市场经验"],
  "summary": "专注智能音箱方案，SMT贴片、声学测试、组装，支持Android，月产能100万台，交期30天。",
  "doc_chunks": [{"doc_id":"...","page":1,"chunk_text":"..."}]
}
```
- **tags**：LLM 提取的自由能力标签（品类·软、本体外能力）。
- **summary**：自然语言串联全部萃取字段的能力描述（含 soft.tags），≤400 字；**一物两用**：档案展示 + REP 向量（REP=`embed(summary)`，D9），不再单独拼接。
- **doc_chunks**：原文块多向量（召回 + 溯源双用）。
> 对称性（待确认）：需求侧 extended 已结构化 `{label, value, strictness}`（D8）；能力侧 `soft.tags` 本期保持字符串（与 extended 语义匹配不受影响），是否同步结构化（如 `{value, confidence?}`）待定。

### 4.4 完备度
- `completeness` = 硬层已填维度数 / 硬层应填维度数（缺失=未声明，可审计）。

### 4.5 能力快照（VendorCapability.structured_tags + soft）
```json
{
  "structured": {
    "product_type": {"value": "智能音箱", "confidence": 0.95, "source": {"page": 1}},
    "os": {"value": ["Android"], "confidence": 0.9, "source": {"page": 1}},
    "certifications": {"value": ["SRRC","CE"], "confidence": 0.9, "source": {"page": 1}},
    "moq": {"value": 500, "confidence": 0.95, "source": {"page": 1}},
    "lead_time_days": {"value": 30, "confidence": 0.9, "source": {"page": 1}},
    "monthly_capacity": {"value": 1000000, "confidence": 0.8, "source": {"page": 1}}
  },
  "soft": {
    "tags": ["三防", "声学调校"],
    "summary": "专注智能音箱方案...",
    "doc_chunks": []
  },
  "completeness": 0.86
}
```

---

## 5. 双侧映射（同 key 表）

| key | 需求侧（声明） | 能力侧（提供） | value_type | 判定方式 |
| --- | --- | --- | --- | --- |
| product_type | 要做什么品类 | 能做什么品类 | scalar | rule 等值 / semantic 近义 |
| certifications | 必须/希望哪些认证 | 已具备哪些认证 | enum | rule 集合包含 |
| os / interfaces / wireless | 要哪些系统/接口/无线 | 支持哪些 | enum | rule 集合包含 |
| moq | 计划起订量（上限） | 最小起订量 | number | rule 数值（upper） |
| lead_time_days | 目标交期（上限） | 交期 | number | rule 数值（upper） |
| monthly_capacity | 需要产能（下限） | 月产能 | number | rule 数值（lower） |
| process_types | 需要哪些工艺 | 具备哪些制程 | enum | rule 集合包含 |
| service_years | 希望成立年限（下限） | 成立年限 | number | rule 数值（lower） |
| application_scenario / customization / industry_cases | 场景/定制/经验要求 | 场景/定制/案例 | text | semantic（LLM） |
| budget_range | 预算 | —（需求侧） | text | 仅需求侧 |

---

## 6. 判定方式派生规则（Stage2）

### 6.1 值形态 → 判定方式
| value_type | 判定方式 | matched / partial / unmatched |
| --- | --- | --- |
| enum(multi) | rule 集合 | 需求⊆厂商 = matched；有交集非全 = partial；无交集 = unmatched |
| scalar | rule 等值 / semantic 近义 | 等值 = matched（品类近义走 semantic） |
| number | rule 数值 + direction | upper：s≤d=matched，s≤d×容差=partial；lower：s≥d=matched，s≥d÷容差=partial |
| text | semantic（LLM verdict） | LLM 判 matched/partial/unmatched/missing |

> missing（厂商未声明）为**独立判定**（计分 30，需协商），不并入 partial；verdict 四档 matched/partial/missing/unmatched（对齐《AI核心总体架构设计v2》§9）。

### 6.2 strictness → 接受规则（Stage0 + Stage2，D7 两档）
- **strict（必须）**：前置 Stage0 硬过滤（集合/数值/方向规则，零 LLM）先行淘汰（枚举/数值含容差）；text/扩展的 strict 走 Stage2 语义 strict；Stage2 若仍 unmatched → 标红。
- **best-effort（尽力）**：全部接受，等权计分（默认，D10）。

### 6.3 打分（D10 等权）
- 需求点匹配度四档：matched=100 / partial=50 / missing=30 / unmatched=0（missing=未声明，介于 partial 与 unmatched 之间）。
- `match_score` = round(Σ需求点匹配度档位 / 需求点数)（0-100，即需求点命中率；等权；语义维度取 LLM verdict 四档同量纲）；阈值 60。

---

## 7. 配置样例（本体 JSON）

```json
{
  "general": [
    {"key":"product_type","label":"产品类型","provenance":"general","value_type":"scalar","kind":"single",
     "options":["机顶盒","智能音箱","IoT设备"]},
    {"key":"certifications","label":"认证","provenance":"general","value_type":"enum","kind":"multi",
     "options":["CE","FCC","CCC","SRRC","ISO9001","其他"]},
    {"key":"moq","label":"起订量","provenance":"general","value_type":"number","direction":"upper","unit":"台"},
    {"key":"lead_time_days","label":"交期(天)","provenance":"general","value_type":"number","direction":"upper","unit":"天"},
    {"key":"monthly_capacity","label":"月产能","provenance":"general","value_type":"number","direction":"lower","unit":"台"}
  ],
  "categories": {
    "智能音箱": [
      {"key":"os","label":"操作系统","provenance":"category","value_type":"enum","kind":"multi",
       "options":["Linux","Android","RTOS","其他"]},
      {"key":"interfaces","label":"接口","provenance":"category","value_type":"enum","kind":"multi",
       "options":["网口","USB","HDMI","GPIO","其他"]},
      {"key":"mic_array","label":"麦克风阵列","provenance":"category","value_type":"enum","kind":"single",
       "options":["2麦","4麦","6麦"]}
    ]
  }
}
```

---

## 8. 与现有实现的迁移映射

| 现有 | 新设计 | 影响 |
| --- | --- | --- |
| `FIXED_FIELDS`（os/interfaces/certifications 等为 general 硬） | 部分维度改归 **category（消费电子）**：os/interfaces/wireless；`KEY_DIMS` 完成判定机制**移除**（D12） | schema.py 配置化重构（本体驱动） |
| `CATEGORY_EXTENSIONS` | 本体 categories 部分 | schema_categories.json → 本体配置 |
| 需求三态（set/wildcard/excluded） | 收敛为正向点 `{value, strictness}`（D6 去 excluded/state；D7 两档） | 快照结构改为 `{dimensions, extended, version}` |
| `ALL_FIELDS`（厂商 7 硬 + 3 软） | 本体子集 + **soft 软层**（tags） | validator.py / extractor.py |
| `PARAM_MAP`（带 os→os_support 映射） | 本体同 key 派生（映射消除） | judger.py 重写为读本体 |
| 判定（rule/semantic 手配） | value_type 自动派生 | judge 逻辑数据驱动 |

---

## 9. 待确认决策

1) **os/interfaces/wireless 归"品类（消费电子）"而非"通用"**：按《代工厂能力模型》它们属电子行业特有。原代价 `KEY_DIMS` 按品类配置已随 **D12（移除 KEY_DIMS）** 消失，**零代价**。**是否同意**？
2) **MOQ 语义 = "计划起订量，厂商最小起订量≤它"（direction=upper）**：与现有 judge 一致。**确认**？
3) **提交门槛 = 品类锚定 + ≥1 需求点 + 用户确认；`KEY_DIMS`/pending_slots 完成判定机制移除（D12）**。**已定案**？
3) ~~strictness 快照格式~~ → **已定案（D6/D7）**：需求点收敛 `{value, strictness}` 两档；能力侧 `{value, confidence, source}`。
4) ~~scalar 不提供 partial 档~~ → **已定案（D7）**：用户严格度去掉 partial 档（scalar 支持 strict/best-effort）；verdict partial（判定结果）保留。
