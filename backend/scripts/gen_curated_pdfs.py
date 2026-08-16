"""生成精选演示 PDF 能力文档（curated v2，2026-08-16）。

- 输入：scripts/data/curated_vendors.json（每家 capability.doc_file + golden 参数）
- 输出：scripts/data/curated_capabilities/{doc_file}（真实 PDF，可被 pypdf 解析、可溯源预览）
- 依赖：reportlab（本地生成工具，仅 dev 环境需要；容器运行 seed 只需 pypdf 读取产物）
- 字体：优先 Windows 黑体 simhei.ttf，回退 Deng.ttf；找不到则报错。
- 运行：python scripts/gen_curated_pdfs.py（cwd=backend）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "scripts" / "data"
OUT_DIR = DATA / "curated_capabilities"

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf",   # Windows 黑体
    r"C:\Windows\Fonts\Deng.ttf",     # Windows 等线
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑（reportlab 对 ttc 支持有限，作回退）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]


def _find_font() -> str:
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            return p
    raise SystemExit("未找到可用的中文字体（需要 simhei.ttf 等），请安装后重试")


def _val_str(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, list):
        return "、".join(str(x) for x in v) if v else "—"
    return str(v)


def _build_doc_text(meta: dict, v: dict) -> list:
    """按 golden 生成结构化能力介绍文本（platypus 元素列表）。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    cap = v["capability"]
    g = cap["golden"]
    comp = v["vendor"]["company_name"]
    title = cap.get("doc_title") or f"{comp} · 制造能力介绍"

    s_title = ParagraphStyle("t", fontName="CJK", fontSize=16, leading=22, alignment=1, spaceAfter=6)
    s_h = ParagraphStyle("h", fontName="CJK", fontSize=12, leading=18, spaceBefore=10, spaceAfter=4)
    s_p = ParagraphStyle("p", fontName="CJK", fontSize=10.5, leading=16)
    s_note = ParagraphStyle("n", fontName="CJK", fontSize=8.5, leading=12, textColor=colors.grey)

    def P(text: str, style=s_p) -> Paragraph:
        return Paragraph(text, style)

    els: list = [Paragraph(title, s_title), Spacer(1, 4)]
    els.append(P(f"文档编号：{v['id']}-CAP-{g.get('version', 1)}　|　编制日期：2026-08-16　|　保密级别：内部", s_note))
    els.append(Spacer(1, 4))

    # 一、公司简介
    els.append(Paragraph("一、公司简介", s_h))
    els.append(P(f"{comp} 位于{meta['category']}制造领域，{_val_str(g.get('customization'))} 模式，"
                 f"主营{meta['category']}的研发、生产与交付，具备{_val_str(g.get('process_types'))}等制程能力。"))

    # 二、核心能力概述
    els.append(Paragraph("二、核心能力概述", s_h))
    els.append(P(cap.get("summary_text") or ""))

    # 三、主要产品与技术参数
    els.append(Paragraph("三、主要产品与技术参数", s_h))
    rows = [
        ("产品类型", _val_str(g.get("product_types"))),
        ("操作系统", _val_str(g.get("os"))),
        ("无线连接", _val_str(g.get("wireless"))),
        ("接口", _val_str(g.get("interfaces"))),
        ("麦克风阵列", _val_str(g.get("mic_array"))),
        ("喇叭功率", _val_str(g.get("speaker_power"))),
        ("防护等级", _val_str(g.get("ip_rating"))),
        ("起订量（MOQ）", f"{g.get('moq', '—')} 台"),
        ("交期", f"{g.get('lead_time_days', '—')} 天"),
        ("月产能", f"{g.get('monthly_capacity', '—')} 台"),
    ]
    t = Table([["参数项", "参数值"]] + [[Paragraph(f"<b>{k}</b>", s_p), P(str(val))] for k, val in rows],
              colWidths=[36 * mm, 130 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "CJK"),
        ("FONTNAME", (0, 0), (0, 0), "CJK"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8d0da")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    els.append(t)

    # 四、制程与质量保障
    els.append(Paragraph("四、制程与质量保障", s_h))
    els.append(P(f"制程能力：{_val_str(g.get('process_types'))}；建立来料检验（IQC）、过程检验（IPQC）、"
                 f"成品检验（OQC）与出厂老化测试流程，关键声学/射频参数逐台记录可追溯。"))

    # 五、认证资质
    els.append(Paragraph("五、认证资质", s_h))
    els.append(P(f"已具备/可协助办理认证：{_val_str(g.get('certifications'))}。"))

    # 六、应用场景
    els.append(Paragraph("六、应用场景", s_h))
    els.append(P(f"适用于：{_val_str(g.get('application_scenarios'))}。"))

    # 七、定制与商务
    els.append(Paragraph("七、定制与商务", s_h))
    els.append(P(f"合作模式：{_val_str(g.get('customization'))}；起订量 {g.get('moq', '—')} 台起，"
                 f"常规交期 {g.get('lead_time_days', '—')} 天，月产能 {g.get('monthly_capacity', '—')} 台，"
                 f"支持按客户需求开模与深度定制。"))
    if g.get("soft_tags"):
        els.append(P(f"特色能力：{'、'.join(str(x) for x in g['soft_tags'])}。"))

    els.append(Spacer(1, 8))
    els.append(Paragraph("—— 以上内容为厂商能力介绍节选，最终以双方商务确认为准 ——", s_note))
    return els


def _render_pdf(doc_file: str, els: list) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / doc_file
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    doc.build(els)
    print(f"  generated: {doc_file} ({out.stat().st_size} bytes)")


def main() -> None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = _find_font()
    pdfmetrics.registerFont(TTFont("CJK", font_path))
    print(f"font: {font_path}")

    data = json.loads((DATA / "curated_vendors.json").read_text(encoding="utf-8"))
    for v in data["vendors"]:
        doc_file = v["capability"]["doc_file"]
        els = _build_doc_text(data["_meta"], v)
        _render_pdf(doc_file, els)
    print(f"done: {len(data['vendors'])} PDFs → {OUT_DIR}")


if __name__ == "__main__":
    sys.path.insert(0, str(BACKEND))
    main()
