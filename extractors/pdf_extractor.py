# -*- coding: utf-8 -*-
"""PDF 抽取器（电子文字型）。

依赖 PyMuPDF：既能判断页面有没有文字层（区分扫描件），也能抽表格。
扫描件目前只做告警，不做 OCR（config.ENABLE_OCR 先关着）。

source 支持本地路径或上传的内存文件（bytes / BytesIO）。
"""
import io
import re

import pymupdf

import config
from .base import (
    Record,
    canonical,
    clean_key,
    clean_value,
    find_header_index,
    is_summary_row,
)

_KV = re.compile(r"^\s*([^:：\s]{1,12})\s*[:：]\s*(.+?)\s*$")


def _open(source):
    if isinstance(source, (bytes, bytearray)):
        return pymupdf.open(stream=bytes(source), filetype="pdf")
    if hasattr(source, "read"):
        return pymupdf.open(stream=source.read(), filetype="pdf")
    return pymupdf.open(str(source))


def _records_from_page(page, name, page_no) -> list[Record]:
    records = []

    # 1) 先试表格
    try:
        tables = page.find_tables().tables
    except Exception:
        tables = []

    for t_idx, table in enumerate(tables, start=1):
        rows = table.extract()
        rows = [[clean_value(c) for c in row] for row in rows if row]
        if len(rows) < 2:
            continue
        header_row = find_header_index(rows)
        header = [clean_key(h) if h else f"列{i + 1}" for i, h in enumerate(rows[header_row])]
        for r_idx, row in enumerate(rows[header_row + 1:], start=header_row + 2):
            data = {}
            for idx, value in enumerate(row):
                if idx >= len(header) or value == "":
                    continue
                if header[idx] == header[0] and value == rows[header_row][0]:
                    continue  # 跨页重复的表头
                data[canonical(header[idx])] = value
            if not data or is_summary_row(data):
                continue
            records.append(
                Record(data=data, source=name,
                       location=f"第{page_no}页 表{t_idx} 第{r_idx}行")
            )

    if records:
        return records

    # 2) 没有表格 → 按「键：值」文本行解析
    current = {}
    for line in page.get_text().splitlines():
        m = _KV.match(line)
        if m:
            current[canonical(m.group(1))] = clean_value(m.group(2))
        elif current and line.strip() == "":
            records.append(Record(data=current, source=name, location=f"第{page_no}页 文本"))
            current = {}
    if current:
        records.append(Record(data=current, source=name, location=f"第{page_no}页 文本"))
    return records


def extract(source, name: str | None = None) -> list[Record]:
    name = name or getattr(source, "name", None) or str(source)
    records = []
    with _open(source) as doc:
        for page_no, page in enumerate(doc, start=1):
            if not page.get_text().strip():
                print(f"  ⚠ {name} 第{page_no}页 没有文字层（疑似扫描件），"
                      f"OCR 开关为 {config.ENABLE_OCR}，已跳过")
                continue
            records.extend(_records_from_page(page, name, page_no))
    return records