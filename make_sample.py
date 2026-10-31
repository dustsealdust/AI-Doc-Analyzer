# -*- coding: utf-8 -*-
"""生成 3 份测试数据（Excel / Word / PDF），故意制造重叠与冲突，方便直接跑通。

数据设计：
  Excel  员工花名册：张三 李四 王五 赵六 孙七
  Word   项目成员表：张三 李四(电话冲突) 王五 周八(只在Word)
  PDF    客户名单  ：张三 赵六 吴九(只在PDF)
预期合并出 7 个实体：张三 李四 王五 赵六 孙七 周八 吴九
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Windows 控制台默认 GBK，直接 print emoji/ 生僻字会崩，这里兜一下
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import docx
import openpyxl
import pymupdf


# ---------------- Excel ----------------
EXCEL_ROWS = [
    ["姓名", "手机", "所在城市", "邮箱"],
    ["张三", "13800000001", "北京", "zhangsan@example.com"],
    ["李四", "13800000002", "上海", "lisi@example.com"],
    ["王五", "13800000003", "广州", "wangwu@example.com"],
    ["赵六", "13800000004", "深圳", "zhaoliu@example.com"],
    ["孙七", "13800000005", "杭州", "sunqi@example.com"],
]

# ---------------- Word ----------------
WORD_ROWS = [
    ["姓名", "电话", "部门", "职位"],
    ["张三", "13800000001", "研发部", "工程师"],
    ["李四", "13900000002", "市场部", "经理"],   # ← 电话与 Excel 冲突
    ["王五", "13800000003", "运营部", "主管"],
    ["周八", "13800000008", "财务部", "会计"],
]

# ---------------- PDF ----------------
PDF_ROWS = [
    ["名字", "联系方式", "地区", "年龄"],
    ["张三", "13800000001", "北京", "28"],
    ["赵六", "13800000004", "深圳", "35"],
    ["吴九", "13800000009", "成都", "41"],
]


def make_excel(target: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "员工花名册"
    for row in EXCEL_ROWS:
        ws.append(row)
    for col, width in zip("ABCD", (12, 18, 12, 28)):
        ws.column_dimensions[col].width = width
    wb.save(str(target))
    return target


def make_word(target: Path):
    document = docx.Document()
    document.add_heading("项目成员表", level=1)
    table = document.add_table(rows=len(WORD_ROWS), cols=len(WORD_ROWS[0]))
    table.style = "Table Grid"
    for r, row in enumerate(WORD_ROWS):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    document.save(str(target))
    return target


def _cjk_font() -> str | None:
    """挑一个本机可用的中文字体（PyMuPDF 内置字体没有中文字形）。"""
    return config.find_cjk_font()


def make_pdf(target: Path):
    font_file = _cjk_font()
    if not font_file:
        raise RuntimeError("找不到中文字体，无法生成测试 PDF")

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=420)   # A4 横放
    page.insert_font(fontname="cjk", fontfile=font_file)

    cell_w, cell_h = 128, 30
    left, top = 40, 50
    cols, rows = len(PDF_ROWS[0]), len(PDF_ROWS)

    # 画表格线（有线条，find_tables 才能稳定识别单元格）
    for r in range(rows + 1):
        y = top + r * cell_h
        page.draw_line(pymupdf.Point(left, y), pymupdf.Point(left + cols * cell_w, y))
    for c in range(cols + 1):
        x = left + c * cell_w
        page.draw_line(pymupdf.Point(x, top), pymupdf.Point(x, top + rows * cell_h))

    # 往单元格写文字
    for r, row in enumerate(PDF_ROWS):
        for c, value in enumerate(row):
            page.insert_text(
                (left + c * cell_w + 8, top + r * cell_h + 20),
                value, fontname="cjk", fontsize=11,
            )

    doc.subset_fonts()   # 只嵌入用到的字形，否则 19MB 的微软雅黑整包塞进去
    doc.save(str(target))
    doc.close()
    return target


def main():
    config.INPUT_DIR.mkdir(parents=True, exist_ok=True)
    made = [
        make_excel(config.INPUT_DIR / "员工花名册.xlsx"),
        make_word(config.INPUT_DIR / "项目成员.docx"),
        make_pdf(config.INPUT_DIR / "客户名单.pdf"),
    ]
    for p in made:
        print(f"✅ 已生成 {p.relative_to(config.ROOT_DIR)}  ({p.stat().st_size} 字节)")


if __name__ == "__main__":
    main()