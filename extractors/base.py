# -*- coding: utf-8 -*-
"""抽取器公共结构：Record + 字段归一化。"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


@dataclass
class Record:
    """一条记录 = 文件里的一行/一行文字。"""
    data: dict = field(default_factory=dict)   # 已归一化的字段
    source: str = ""                           # 文件名
    location: str = ""                         # 第几行 / 第几页


def clean_key(name) -> str:
    """去掉表头里的空格、换行、全角冒号等噪音。"""
    if name is None:
        return ""
    s = str(name).replace("\n", "").replace("\r", "").replace(" ", "")
    s = s.replace("　", "").strip(":：*")
    return s


def clean_value(value) -> str:
    """统一把值转成字符串。"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).replace("\n", "").replace("\r", "").strip()


_ALIAS_LOOKUP = {}
for _canon, _aliases in config.FIELD_ALIASES.items():
    for _a in _aliases:
        _ALIAS_LOOKUP[clean_key(_a).lower()] = _canon


def canonical(name) -> str:
    """把任意写法映射成标准字段名；认不出来就保留原样（不丢数据）。"""
    key = clean_key(name)
    return _ALIAS_LOOKUP.get(key.lower(), key)


# 汇总行关键词：合计/总计 这类行不是实体，直接丢掉
SUMMARY_WORDS = ("合计", "总计", "小计", "共计", "汇总", "总人数", "总数", "平均")


def find_header_index(rows, scan_limit: int = 10) -> int:
    """在前几行里找真正的表头行（真实表格上面常压着一行合并的大标题）。"""
    for index, row in enumerate(rows[:scan_limit]):
        hits = 0
        for cell in row:
            key = clean_key(cell)
            if key and canonical(key) in config.FIELD_ALIASES:
                hits += 1
        if hits >= 1:
            return index
    return 0


def is_summary_row(data: dict) -> bool:
    """这一行是不是「合计/总计」这种汇总行。"""
    for field_name in config.PRIMARY_KEY_FIELDS:
        value = clean_value(data.get(field_name, "")).strip(":： ")
        if value and any(word in value for word in SUMMARY_WORDS):
            return True
    return False