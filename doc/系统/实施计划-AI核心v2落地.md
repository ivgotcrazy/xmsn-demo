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

### Step 1 本体配置化（D1，前置基座）—— ✅ 已完成（2026-08-16）
- **新增** `backend/app/domains/ontology.json`：本体配置（general 11 维 + `shared_groups.consumer_electronics`（os/interfaces/wireless）+ 3 品类 fields，**extends 结构**、闭集无"其他"）；`backend/app/domains/ontology.py`：解析 + 查询 API（`fields_for`/`label_of`/`value_type_of`/`category_names`；含 **level/optional 兼容层推导**，本体不含 level，D11）。
- **改造** `conversation/schema.py`：`FIXED_FIELDS`/`CATEGORY_EXTENSIONS` → 从本体派生；`fields_for`/`label_of` 走本体；**删除 `KEY_DIMS`/`_load_categories`/`_normalize`**（D12）。
- **兼容层**：三态 `SlotTriState`/`LEVEL_*`/`pending_slots` 保留（agent/service 仍引用，Step 3 需求侧删除）；旧 `schema_categories.json` 已不被引用（Step 3 删除）。
- **单测**：`tests/test_ontology.py` 11 例全过（品类闭集 / 维度展开 17/19/18 / extends 共享 / label / depends_on / 状态机兼容）。
- **遗留（后续步骤）**：能力侧 `os_support` → `os`（Step 2 extractor/validator/indexer/seed_data）；judger/retriever 的 os_support 映射（Step 4 重写消除）。

### Step 2 能力侧升级（D1/D3/D9）—— ✅ 已完成（2026-08-16）
- `vendor_service/extractor.py` `PROMPT_PARSE`：`os_support` → **`os`**（D1 同 key）；`summary_text` 改**自然语言串联全部萃取字段（含 soft_tags），≤400 字**（D9）；新增 **`soft_tags`**（D3 软层自由标签）。
- `vendor_service/validator.py`：`HARD_FIELDS` 的 `os_support` → `os`；`validate` 返回 5 元组（+ soft_tags 透传）。
- `db/models.py`：`VendorCapability` 新增 `soft_tags` JSONB；**alembic 迁移 `d3f0c1a2b9e7`** 已应用。
- `vector/indexer.py`：删 `rep_text` 拼接 → `index_representative(vendor_id, summary)` 直接 `embed(summary)`（D9）；`chunk_text`/原文块保留。
- `worker/_parse_capability`：`soft_tags` 落库；`index_representative` 新签名。
- `scripts/seed_data.py` + `seed_curated.py` + `data/curated_vendors.json`：`os_support` → `os`、补 `soft_tags`、summary 模板全字段自然语言；`index_representative` 新签名。
- `match_service/judger.py`/`retriever.py`：`os_support` → `os`（PARAM_MAP/CRITICAL/_tags_hit 映射同 key 对齐；判定逻辑不动，Step 4 重写读本体）。
- **单测**：`tests/test_capability.py` 4 例全过（PROMPT 同 key/400字/soft_tags、validate 归一/completeness 分母含 os）；连同本体共 15 例全过。

### Step 3 需求侧升级（D5-D8/D11/D12）—— ✅ 已完成核心（2026-08-16）
- `schemas/conversation.py`：`DemandPoint` 加 `strictness`（strict/best-effort，D7）。
- `conversation/schema.py`：新增 `schema_ref_of(pt)`、`count_demand_points(state,pt)`；`validate_completion` 改 **D12 门槛**（品类锚定 + 品类外 ≥1 需求点）；`next_unfilled` 跳过 `_confirmed_unlimited`（D6 私有标记）。
- `conversation/agent.py`：`EXTRACT_PROMPT`/`build_tool_schema` 去三态（`__states__`→`__strictness__`）；`write_option`/`merge_slot` 改**正向点** `{value, state:set, strictness}`；**extended 结构化**（D8）；自创字段归 extended；`reconcile`/`weak_close_recap` 对齐。
- `conversation/service.py`：`_slots_snapshot` → **正向点快照** `{schema_ref, dimensions:{key:{value,strictness}}, extended:[...], version}`（无 state/excluded）；`to_demand_points` schema 感知 + strictness；`_delta_summary` 去三态；**提交门槛 D12**（`_do_confirm`/`_do_submit_from_message` 校验 0 需求点）；**两步化**（confirm 接收 demand_points 微调 strictness）；start 品类闭集去"其他"；"跳过/不限"→ `_confirmed_unlimited` 私有标记不入档。
- `api/conversation.py`：confirm 传 `payload.demand_points`。
- **D11 追问兜底修复**：`agent.decide_question` 移除 `next_slot` 逐维度模板追问分支（"请问您需要哪些接口/认证"）——门槛未达成（仅品类/0 需求点）→ 开放引导 `NEED_POINTS_TEXT`（提示补充需求点，追问交 LLM 自然引导）；`next_slot` 仅保留作 `build_recommendation`/`agent_reasoning` 的参考锚点。
- **单测**：`tests/test_conversation.py` 11 例（正向点/strictness/extended/快照无 state/门槛 D12/私有标记）；连同本体+能力侧共 26 例全过。
- **遗留**：`eval.py` 仍用旧 `extra_constraints` 键与三态断言（Step 6 更新评估集）；匹配侧读取（Step 4 重写）；前端（Step 5）。

### Step 4 匹配漏斗 Stage0-4（D1/D2/D6/D7/D9/D10 + AI核心 §5.3）—— ✅ 已完成核心（2026-08-16）
- **契约** `schemas/match.py`：`MatchItem` 去 `param_hit_rate`/`critical_fail` → 四计数（matched/partial/missing/unmatched_count）；`MatchParam.verdict` 四值（missing 独立，D10）+ strictness；`MatchDetailResponse` **四组** + `match_reason`/`risk_warning`（D4）。
- **模型/迁移**：`MatchResult` 加 `missing_params`/`match_reason`/`risk_warning`（alembic `a4b5c6d7e8f9` 已应用；`param_hit_rate`/`critical_fail` 列保留兼容旧数据）。
- **Stage0** `stage0.py`（新建）：SQL JSONB 硬筛（strict 受控 enum/scalar/number，无容差；best-effort 不进；品类恒硬条件；仅 passed 厂商）→ `passed` 集。
- **Stage1** `retriever.py`：`demand_embedding_text` 自然语言模板（D9，label+值+extended）；**两路 ANN**（REP ∪ 原文块，passed 内）；`semantic_score=max(rep,chunk)` 只做召回（D10）。
- **Stage2** `judger.py`：删 `PARAM_MAP`/`CRITICAL` → 本体 `value_type` 派生四档（enum 集合 / scalar 等值无 partial / number 容差1.5 / text+extended LLM 语义）；**strict_ok**（D7：strict 未满足不硬杀，供 Stage4 risk_warning）。
- **Stage3** `scorer.py`：`match_score = round(Σ档位/N)`（100/50/30/0）；**阈值 60**（D10）；无权重。
- **编排** `service.py`：Stage0→Stage1→Stage2/3 并发→**TopK（K=10）**→四组落库→触发 Stage4 解释（全部 TopK）。
- **Stage4** `explain.py`/`worker`：四组 + `match_reason`/`risk_warning`/`ai_comment`（D4）；TopK 解释范围。
- **单测**：`tests/test_match.py` 8 例（四档判定/scorer 等权/demand_embedding_text/Stage0 SQL）；全量 **34 例**全过。
- **遗留**：`eval_match_runner.py` 依赖旧契约（Step 6 更新）；前端（Step 5）。

### Step 5 前端适配（D5/D7/D10）—— ✅ 已完成核心（2026-08-16）
- `packages/types`：`ParamKey` 本体 key（去 os_support/权重）、`REQUEST_SCHEMA_FIELDS` 去 weight/critical（D10）、`Verdict` 四值 + `VERDICT_META`（missing 独立）、`CapabilityKey` os。
- `packages/api/src/types.ts`：`DemandPoint`+strictness、`MatchItem` 四计数去 param_hit_rate/critical_fail、`MatchParam` 四值、`MatchDetailResponse` 四组+match_reason/risk_warning。
- `DemandProfileCard.vue`：需求点实例 + **strictness 徽标**（必须/尽力，D7）。
- `MatchDetailPanel.vue`：**四组**（missing 独立）+ `match_reason`/`risk_warning`（D4）；去 `critical_fail` 红色警示。
- `MatchResultItem.vue`：四计数 meta + 未声明提示；去 critical_fail 标签。
- `ChatView.vue`：**两步化确认框**（D7）——`openConfirm` 打开 NModal（需求点 + strictness 可切换）+ D12 门槛前置校验（品类 + ≥1 需求点）+ `confirm()` 提交（editablePoints 微调 strictness）。
- `admin RequestsView`（missing 计数）、`VendorsView`/`VendorCapabilityView`（os）。
- **验证**：VSCode TS 检查关键文件无错误；本地 node_modules 缺失（容器内已装，构建留待容器验证）。

### Step 6 迁移 + 回归 + 评估 —— 代码层已完成（2026-08-16）
- `agent.extract_slots` 输出 `extended`（D8）；`eval.py`/`eval_match_runner.py` 适配新快照（正向点 + dimensions 锚点判断）。
- alembic 迁移已应用：`d3f0c1a2b9e7`（vendor_capabilities.soft_tags）+ `a4b5c6d7e8f9`（match_results missing_params/match_reason/risk_warning）。
- 全量单测 **34 例**全过（本体/能力/需求/匹配）。
- **遗留（用户审查后验证）**：① 容器内 pnpm build + e2e 回归（02A 对话→两步化确认→02B 四组详情）；② 重新导出 openapi 契约（前端 types 已手动对齐）；③ msw mockData 更新（os/四计数/四值）；④ 评估集扩充（strictness/四档/召回边界）；⑤ **§5.3.6② 参数（min_semantic/top_k/聚合）用评估数据定**；⑥ 旧数据一次性迁移（三态快照→正向点；旧能力 os_support→os）。

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
