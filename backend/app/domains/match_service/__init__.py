"""匹配引擎域（M4）：双通道打分 + 兜底 + 落库。

实现以《匹配详细设计》LLD v1.0 为准（第 2-8 章）：
- retriever.py：通道A 语义检索（需求向量 → vendor_representative ANN）
- judger.py：通道B 参数判定（PARAM_MAP + RULE 规则 + SEMANTIC 批量 LLM + 判定缓存）
- scorer.py：综合打分（⌊100×(0.4A+0.6B)⌋ + 封顶 + 阈值）+ param_hit_rate
- service.py：compute 主流程（confirm 生成 match_runs(running) 后消费）→ done/empty + 落库 match_results
"""
