# -*- coding: utf-8 -*-
"""生成录视频用的演示数据（demo/ 目录），4 个文件按 01-04 编号。

数据设计（故意留一个冲突，方便演示冲突报告）：
  01 员工花名册.xlsx : 张三 李四 王五 赵六 孙七 陈十一
  02 项目成员.docx   : 张三 李四 王五 周八          ← 李四电话与 01 冲突
  03 客户名单.pdf    : 张三 赵六 吴九
  04 合同台账.xlsx   : 张三 李四 赵六 郑十
张三在 4 个文件里都出现 → 关联最多，AI 报告会点名。
预期：17 条记录 / 9 个实体 / 1 处冲突。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

import docx
import openpyxl
import pymupdf
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DEMO_DIR = Path(__file__).resolve().parent / "demo"

HEADER_FILL = PatternFill("solid", fgColor="1D4ED8")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
THIN = Side(style="thin", color="C9D2E3")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _style_sheet(ws, widths):
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=len(widths)):
        for cell in row:
            cell.border = BORDER
            if cell.row > 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22


# ---------------------------------------------------------------- 01 员工花名册
def make_emp_roster():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "员工花名册"
    ws.append(["姓名", "手机", "所在城市", "邮箱", "入职日期"])
    rows = [
        ["张三", "13800000001", "北京", "zhangsan@example.com", "2021-03-15"],
        ["李四", "13800000002", "上海", "lisi@example.com", "2020-07-01"],
        ["王五", "13800000003", "广州", "wangwu@example.com", "2022-11-09"],
        ["赵六", "13800000004", "深圳", "zhaoliu@example.com", "2019-05-20"],
        ["孙七", "13800000005", "杭州", "sunqi@example.com", "2023-02-14"],
        ["陈十一", "13800000006", "南京", "chenshiyi@example.com", "2021-09-30"],
    ]
    for row in rows:
        ws.append(row)
    _style_sheet(ws, [12, 16, 12, 30, 14])
    wb.save(DEMO_DIR / "01_员工花名册.xlsx")


# ---------------------------------------------------------------- 02 项目成员
def make_project_members():
    document = docx.Document()
    document.add_heading("项目成员表", level=1)
    document.add_paragraph("项目：智慧园区数据中台   填报日期：2026-10-30")

    data = [
        ["姓名", "电话", "部门", "职位"],
        ["张三", "13800000001", "研发部", "工程师"],
        ["李四", "13900000002", "市场部", "经理"],   # ← 与 01 冲突
        ["王五", "13800000003", "运营部", "主管"],
        ["周八", "13800000008", "财务部", "会计"],
    ]
    table = document.add_table(rows=len(data), cols=len(data[0]))
    table.style = "Table Grid"
    for r, row in enumerate(data):
        for c, value in enumerate(row):
            table.cell(r, c).text = value

    for cell in table.rows[0].cells:                 # 表头加粗
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True

    document.add_paragraph("")
    document.add_paragraph("注：本表仅用于内部统计。")
    document.save(DEMO_DIR / "02_项目成员.docx")


# ---------------------------------------------------------------- 03 客户名单
def make_client_pdf():
    font = None
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\simsun.ttc"):
        if Path(path).exists():
            font = path
            break

    rows = [
        ["姓名", "联系方式", "地区", "年龄"],
        ["张三", "13800000001", "北京", "28"],
        ["赵六", "13800000004", "深圳", "35"],
        ["吴九", "13800000009", "成都", "41"],
    ]

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=360)
    page.insert_font(fontname="cjk", fontfile=font)
    page.insert_text((40, 46), "客户名单", fontname="cjk", fontsize=18)
    page.insert_text((40, 70), "统计口径：2026 年第三季度", fontname="cjk", fontsize=10)

    left, top, cell_h = 40, 90, 30
    widths = [110, 150, 130, 90]

    def x_of(col):
        return left + sum(widths[:col])

    # 横线
    for r in range(len(rows) + 1):
        y = top + r * cell_h
        page.draw_line(pymupdf.Point(left, y),
                       pymupdf.Point(left + sum(widths), y))
    # 竖线
    for c in range(len(widths) + 1):
        x = x_of(c)
        page.draw_line(pymupdf.Point(x, top), pymupdf.Point(x, top + len(rows) * cell_h))
    # 内容
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            page.insert_text((x_of(c) + 10, top + r * cell_h + 20),
                             value, fontname="cjk", fontsize=11)

    doc.subset_fonts()
    doc.save(DEMO_DIR / "03_客户名单.pdf")
    doc.close()


# ---------------------------------------------------------------- 04 合同台账
def make_contracts():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "合同台账"
    ws.append(["姓名", "合同编号", "合同金额(万元)", "签约日期", "负责人"])
    rows = [
        ["张三", "HT-2026-001", 120, "2026-01-18", "周八"],
        ["李四", "HT-2026-002", 86, "2026-03-02", "周八"],
        ["赵六", "HT-2026-003", 240, "2026-05-21", "周八"],
        ["郑十", "HT-2026-004", 55, "2026-08-09", "周八"],
    ]
    for row in rows:
        ws.append(row)
    _style_sheet(ws, [12, 18, 18, 14, 12])
    wb.save(DEMO_DIR / "04_合同台账.xlsx")


def main():
    DEMO_DIR.mkdir(exist_ok=True)
    make_emp_roster()
    make_project_members()
    make_client_pdf()
    make_contracts()
    for path in sorted(DEMO_DIR.iterdir()):
        print(f"{path.name}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()