# -*- coding: utf-8 -*-
"""Word 抽取器：优先抽表格；没有表格就退化成「键：值」段落解析。

source 支持本地路径或上传的内存文件（bytes / BytesIO）。
"""
import io
import re

import docx

from .base import (
    Record,
    canonical,
    clean_key,
    clean_value,
    find_header_index,
    is_summary_row,
)


def _open(source):
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    return docx.Document(source if hasattr(source, "read") else str(source))


def _extract_tables(document, name) -> list[Record]:
    records = []
    for t_idx, table in enumerate(document.tables, start=1):
        rows = [[clean_value(c.text) for c in row.cells] for row in table.rows]
        if len(rows) < 2:
            continue
        header_row = find_header_index(rows)
        header = [clean_key(h) if h else f"列{i + 1}" for i, h in enumerate(rows[header_row])]
        for r_idx, row in enumerate(rows[header_row + 1:], start=header_row + 2):
            data = {}
            for idx, value in enumerate(row):
                if idx >= len(header) or value == "":
                    continue
                data[canonical(header[idx])] = value
            if not data or is_summary_row(data):
                continue
            records.append(Record(data=data, source=name, location=f"表{t_idx} 第{r_idx}行"))
    return records


def _extract_paragraphs(document, name) -> list[Record]:
    """退化模式：连续几行「姓名：张三」这样的键值对，凑成一条记录。"""
    pattern = re.compile(r"^\s*([^:：]{1,12})\s*[:：]\s*(.+?)\s*$")
    records, current = [], {}
    for para in document.paragraphs:
        m = pattern.match(para.text)
        if m:
            current[canonical(m.group(1))] = clean_value(m.group(2))
        elif current and not para.text.strip():
            records.append(Record(data=current, source=name, location="段落"))
            current = {}
    if current:
        records.append(Record(data=current, source=name, location="段落"))
    return records


def extract(source, name: str | None = None) -> list[Record]:
    name = name or getattr(source, "name", None) or str(source)
    document = _open(source)
    records = _extract_tables(document, name)
    return records if records else _extract_paragraphs(document, name)