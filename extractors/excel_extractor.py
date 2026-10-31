# -*- coding: utf-8 -*-
"""Excel 抽取器：遍历所有 Sheet，自动定位表头行，每行一条记录。

source 既可以是本地路径，也可以是 Streamlit 上传的内存文件（bytes / BytesIO）。
"""
import io

import openpyxl

from .base import (
    Record,
    canonical,
    clean_key,
    clean_value,
    find_header_index,
    is_summary_row,
)


def extract(source, name: str | None = None) -> list[Record]:
    name = name or getattr(source, "name", None) or str(source)
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    book = source if hasattr(source, "read") else str(source)

    wb = openpyxl.load_workbook(book, data_only=True, read_only=False)
    records = []
    multi_sheet = len(wb.worksheets) > 1

    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            continue

        header_row = find_header_index(rows)
        header = [
            clean_key(c) if c is not None else f"列{i + 1}"
            for i, c in enumerate(rows[header_row])
        ]

        for offset, row in enumerate(rows[header_row + 1:], start=header_row + 2):
            data = {}
            for idx, cell in enumerate(row):
                if idx >= len(header):
                    break
                value = clean_value(cell)
                if value == "":
                    continue
                data[canonical(header[idx])] = value
            if not data:
                continue          # 整行空
            if is_summary_row(data):
                continue          # 合计/总计 行
            location = f"{ws.title} 第{offset}行" if multi_sheet else f"第{offset}行"
            records.append(Record(data=data, source=name, location=location))

    return records