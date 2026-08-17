"""切分 + 批量嵌入单测（纯逻辑，无 LLM/DB；token 计数走启发式/或 tiktoken）。"""
import asyncio

from app.llm import embedding
from app.vector.indexer import MAX_TOKENS, _count_tokens, chunk_document


def _pages(chars_per_page: int, page_count: int) -> list[str]:
    """构造多页长文本（无空行段落，模拟长正文/表格）。"""
    out = []
    for _ in range(page_count):
        out.append("".join(f"第{i}段能力描述" for i in range(chars_per_page // 6)))
    return out


def test_count_tokens_chinese():
    """中文≈1 字 1 token（启发式/或 tiktoken），且为正值。"""
    n = _count_tokens("智能音箱制造能力" * 10)
    assert n >= 60 and n <= 200


def test_chunk_document_cross_page_merge():
    """页边界两块合并进同一 chunk → page 范围 1~2，且两页内容都在同一块。"""
    p1_tail = "第一页尾部这一段，语义延续到下一页，不应被页边界切断。"
    p2_head = "第二页开头这一段，是上一段落的延续，保持完整语义。"
    big = "本段落内容较长，用于把第一页空间占满，使其尾部块无法并入第一页首块。" * 9  # ~270 字
    page1 = big + "\n\n" + p1_tail
    page2 = p2_head + "\n\n第二页第二段，独立内容。"
    chunks = chunk_document([page1, page2])

    assert chunks, "应有切分结果"
    # 所有块不超过 token 上限
    assert all(_count_tokens(c["text"]) <= MAX_TOKENS for c in chunks)
    # 存在跨页合并块（1~2），且同时包含两页内容
    cross = [c for c in chunks if c["page_start"] == 1 and c["page_end"] == 2]
    assert cross, "应存在跨页合并块"
    assert any(p1_tail in c["text"] and p2_head in c["text"] for c in cross)


def test_chunk_document_single_page_label():
    """单页短文档 → 全部单页块（page_start == page_end == 1）。"""
    chunks = chunk_document(["第一段。\n\n第二段。\n\n第三段。"])
    assert chunks
    assert all(c["page_start"] == 1 and c["page_end"] == 1 for c in chunks)


def test_chunk_document_oversized_block_split():
    """单个超长块（无空行，模拟巨型表格）→ 拆成多个 ≤上限 的块，且同页。"""
    long_block = "参数项|参数值|备注。" * 200  # ~1800 字，无空行 → 单块超限
    chunks = chunk_document([long_block])
    assert len(chunks) > 1
    assert all(_count_tokens(c["text"]) <= MAX_TOKENS for c in chunks)
    assert all(c["page_start"] == 1 and c["page_end"] == 1 for c in chunks)


def test_chunk_document_empty():
    """空页/空文档 → 无块。"""
    assert chunk_document([]) == []
    assert chunk_document(["   ", "\n"]) == []


def test_embed_batches_over_8k():
    """embed 按 token 分批（单批 ≤6000）、保序、不丢不重。"""

    class _D:
        def __init__(self, index, embedding):
            self.index = index
            self.embedding = embedding

    class _Resp:
        def __init__(self, data):
            self.data = data

    # 4 条可区分的长文本（每条 ~2500 token，总 ~10000 → 必分批）
    texts = ["智能音箱制造能力描述。" * 200 + f"标记{i}" * 60 for i in range(4)]

    def _global_idx(t: str) -> int:
        return next(i for i, s in enumerate(texts) if s == t)

    class _FakeEmb:
        def __init__(self):
            self.calls: list[list[str]] = []

        async def create(self, model, input):
            self.calls.append(list(input))
            # 故意乱序返回（index 正确），验证 _embed_batch 按 index 排序恢复输入顺序
            data = [_D(i, [float(_global_idx(t))]) for i, t in enumerate(input)]
            data.reverse()
            return _Resp(data)

    class _FakeClient:
        def __init__(self):
            self.embeddings = _FakeEmb()

    fake = _FakeClient()
    orig = embedding._get_client
    embedding._get_client = lambda: fake
    try:
        vecs = asyncio.run(embedding.embed(texts))
    finally:
        embedding._get_client = orig

    total = sum(len(b) for b in fake.embeddings.calls)
    assert total == 4, "不应丢/重文本"
    assert len(fake.embeddings.calls) >= 2, "总 token 超 8K 应分批"
    assert len(vecs) == 4
    # 保序：第 i 条向量由第 i 条文本产生（跨批 + 乱序返回都需恢复正确顺序）
    assert vecs == [[float(i)] for i in range(4)]
