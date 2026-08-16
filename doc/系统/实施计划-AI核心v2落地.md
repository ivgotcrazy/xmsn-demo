# 需脉枢纽 · 实施方案与计划（AI核心 v2 落地）

> 版本：v1.0 ｜ 状态：指导实施 ｜ 更新：2026-08-16
>
> 本文档给出在**当前已实现代码**基础上，将《AI核心总体架构设计v2》（D1-D11 + Stage0-4）落地的分步改造方案：依赖顺序、改动文件、验收标准与风险。**不重写、只改造**；每步保持可运行。

**权威文档**：《AI核心总体架构设计v2.md》（决策与漏斗）、供需Schema设计.md（本体）、代理详细设计v2.md（需求侧）、匹配详细设计.md（匹配侧）、厂商解析详细设计.md（能力侧）、前端设计规范.md（前端）。

---

## 0. 现状基线（当前实现，全部待改造）

| 模块 | 文件 | 现状（旧） | 目标（新） |
| --- | --- | --- | --- |
| 本体 | `domains/conversation/schema.py` `FIXED_FIELDS` / `schema_categories.json` | 硬编码维度 + 三态 + `LEVEL_HARD/SOFT/OPTIONAL` | 本体配置化（供需Schema §3.4/3.5/§7），同 key |
| 需求侧 | `conversation/{agent,service,schema}.py` | 三态（set/wildcard/excluded）、extra_constraints、level、pending_slots | 正向点 + strictness 两档 + extended 结构化 + 两步化 + 品类锚定 |
| 能力侧 | `vendor_service/extractor.py` / `vector/indexer.py` | `os_support` 旧key、summary ≤50字、rep=拼装tags | 同 key（os）、summary ≤400字全字段、REP=embed(summary)、soft.tags |
| 匹配侧 | `match_service/{service,retriever,judger}.py` | 通道A（单路代表ANN top50）→ 通道B（PARAM_MAP 映射判定）→ 权重打分 → critical_fail | Stage0 SQL 硬筛 → Stage1 两路召回 → Stage2 逐维度判定（四档）→ Stage3 等权打分 → Stage4 LLM 解释 |
| 前端 | `user-web` ChatView / DemandProfileCard / MatchDetailPanel | 三态需求档案、详情三组+critical_fail | schema 感知、确认框 strictness 可调、详情四组+match_score+risk_warning |

---

## 1. 分步改造（依赖顺序，每步可运行）

### Step 1 本体配置化（D1，前置基座）
- **新增** `backend/app/domains/match_service/ontology.py`：承载需求点 schema 元数据（通用 + 4 品类 + 扩展规则），字段含 `{key, label, value_type(enum/scalar/number/text), unit, options, direction, strict_supported}`；消费 e 供需Schema §3.4/3.5/§7 的 JSON。
- **改造** `conversation/schema.py`：`FIXED_FIELDS` → 读本体；删除三态 `SlotTriState`、`LEVEL_*` 分级常量、**`KEY_DIMS` 与 `pending_slots` 完成判定机制**（D12）。
- **统一 key**：`os_support` → `os`（消除映射层，D1）。
- **验收**：单测（本体加载、key 全局唯一、options 闭集无"其他"）；`python -c "from app.domains.match_service.ontology import *"` 可导入。

### Step 2 能力侧升级（D1/D3/D9）
- `vendor_service/extractor.py` `PROMPT_PARSE`：结构化输出改**本体同 key**；`summary_text` 改**自然语言串联全部萃取字段（含 soft.tags），≤400 字**（D9）。
- `vendor_service/extractor.py`：新增 **`soft.tags`** 提取（本体外自由能力标签，D3）。
- `vector/indexer.py`：删 `rep_text` 拼接 → `index_representative(vendor_id, summary)` 直接 `embed(summary)`；`chunk_text` 与原文块向量保留。
- 能力画像落库：`structured{key:{value,confidence,source}}` + `soft{tags,summary,doc_chunks}`。
- **验收**：解析一条样本 → REP 为 `embed(summary)`、key 同本体、含 soft.tags、summary 覆盖全字段 ≤400字。

### Step 3 需求侧升级（D5/D6/D7/D8/D11）
- `conversation/schema.py`：三态 → **正向点**（删除 EXCLUDED；wildcard 降为 Agent 私有标记不落库）；**strictness 两档**（strict/best-effort）；`extra_constraints` → **extended 结构化 `{label, value, strictness}`**（D8）。
- `conversation/agent.py`：`merge_slot` 去 excluded 分支；`extract_slots` 输出含 strictness + extended 结构化；sys_prompt 注入**品类 allowed_set + 已填需求点**，**追问交 LLM**（D11，去 pending_slots 分级）。
- `conversation/service.py`：`_slots_snapshot` → **正向点快照**（`{schema_ref, dimensions:{key:{value,strictness}}, extended:[...]}`）；**两步化提交（D7）**：Agent 判定 → 确认框（strictness 只读可微调）→ 确认落库；**提交门槛（D12）= 品类锚定 + ≥1 需求点 + 用户确认**，后台校验 `len(dimensions)+len(extended)>=1` 拦截 0 需求点提交。
- **验收**：e2e 一条对话 → 快照为正向点 + strictness + extended；无 excluded/level 字段；**0 需求点提交被后台拦截**（仅品类 → 提示补至少 1 个需求点）。

### Step 4 匹配漏斗改造（D2/D9/D10 + Stage0-4）
- **Stage0 硬筛**：`match_service/stage0.py` 新增 SQL（JSONB `@>` 闭集等值、数值方向**无容差**、枚举已归一）→ 输出 `passed` 集（D2/D6，删除 `_excluded_hard_filter`）。
- **Stage1 召回**：`retriever.py` 改 **passed 内两路 ANN**（REP ∪ 原文块）；`semantic_score = max(rep, chunk)` **只做召回**；`demand_embedding_text` 改**自然语言模板**（D9，去三态 key:value 拼接）。
- **Stage2 判定**：`judger.py` 删 `PARAM_MAP` → 读本体 `value_type` 派生（enum 集合 / scalar 等值 / number 容差1.5 / text LLM）；**verdict 四档**（matched/partial/missing/unmatched，missing 独立，D10）；strictness 接受规则（strict→仅 matched；best-effort→全接受）。
- **Stage3 打分**：`service.py` `compute` → `match_score = round(Σ需求点档位/需求点数)`（0-100，四档 100/50/30/0，阈值 60，TopK）；删权重 / 0.4-0.6 blend / `critical_fail` / `param_hit_rate`。
- **Stage4 解释**：`worker/_explain_match` 输入改 **Stage3 TopK** → 四组 verdict + `match_reason` + `risk_warning` + `ai_comment`（带 source 溯源，D4）；失败回退 Stage2/3 结果。
- **验收**：用贯穿示例（V1 华声 / V2 锐联 / V3 微芯 / V4 极光）→ Stage0 passed=[V1,V4]、V4=94、V1=73（物流 missing=30）；`eval_match_runner.py` 回归。

### Step 5 前端适配（D5/D7/D10）
- `ChatView.vue` / `DemandProfileCard.vue`：**当前需求 = 需求档案**（schema_ref + 需求点实例），label/options 由品类 Schema 提供（不再"不感知 schema"）。
- 确认框（两步化）：只读展示 Agent 判定的 strictness，可微调后提交。
- `MatchDetailPanel.vue`：**四组**（missing 独立）+ `match_score` + `risk_warning`；去 `critical_fail` 红色警示。
- `packages/api` / `packages/types`：契约同步（快照格式、match 字段、四计数）。
- **验收**：浏览器验证 02A 对话 → 确认框 → 02B 详情四组。

### Step 6 回归与评估
- e2e 回归（buyer 13912345678 / vendor 18812345678 演示账号）；DB 迁移（alembic：`buyer_requests.structured_demand`、`vendor_capabilities.structured_tags`、`match_results` 字段变化）。
- 评估集扩充（strictness / 四档 / 召回边界用例）；**§5.3.6 ② 参数（min_semantic / top_k / 聚合）用评估数据定**。

---

## 2. 风险与注意事项

- **兼容旧数据**：历史三态快照 / 旧能力档案 → Step 6 一次性迁移或标注"仅最新"。
- **embedding 窗口**：summary ≤400 字需验证 token 数（智谱 embedding-2）。
- **品类闭集**：不接受"其他"声明；买方非已知品类 → best-effort 走语义（Stage1）。
- **0 需求点**：Step 3 后台校验拦截（D12），Stage3 分母恒 ≥1，无需额外兜底。
- **评估驱动**：Stage3 阈值 60、Stage1 min_semantic/top_k 均为待评估参数，勿在数据前拍死。
- **每步可运行**：Step 1-3 独立交付（能力/需求侧），Step 4 匹配侧改造较大，可先 mock Stage0 再替换。
- **WSL 容器**：`docker compose up -d --build web` 偶发 pnpm 失败需重跑；验证浏览器需 CDP 禁缓存 + reload。

## 3. 里程碑建议

| 阶段 | 内容 | 预估 |
| --- | --- | --- |
| M1 | Step 1 本体配置化 + 单测 | 0.5 天 |
| M2 | Step 2 能力侧（同 key/summary/soft） | 1 天 |
| M3 | Step 3 需求侧（正向点/两步化/追问LLM） | 1.5 天 |
| M4 | Step 4 匹配漏斗 Stage0-4 | 2 天 |
| M5 | Step 5 前端适配 | 1 天 |
| M6 | Step 6 迁移 + 回归 + 评估调参 | 1 天 |
