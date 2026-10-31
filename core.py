# -*- coding: utf-8 -*-
"""合并核心：文件 → 记录 → 传入内存实体 → 可序列化结果。

CLI（merge.py）和 Web 界面（app.py）共用这一份逻辑，避免两边行为不一致。
"""
from pathlib import Path

import config
from extractors import excel_extractor, pdf_extractor, word_extractor
from extractors.base import Record, canonical, clean_value

EXTRACTORS = {
    ".xlsx": excel_extractor.extract,
    ".xlsm": excel_extractor.extract,
    ".docx": word_extractor.extract,
    ".pdf": pdf_extractor.extract,
}


# ---------------------------------------------------------------- 内存实体
class Entity:
    """一个实体 = 你要的那块「结构体内存」。字段随挂载持续增长。"""

    def __init__(self, key_field: str, key_value: str):
        self.key_field = key_field
        self.key_value = key_value
        self.data = {key_field: key_value}
        self.sources = []                 # 这条实体来自哪些文件
        self.conflicts = {}               # 字段 -> [{value, source}, ...]

    def attach(self, record: Record):
        """挂载一条外部记录：新字段直接补上，老字段冲突则登记不覆盖。"""
        source_label = f"{record.source} · {record.location}"
        self.sources.append(source_label)
        for field_name, value in record.data.items():
            if field_name == self.key_field:
                continue
            value = clean_value(value)
            if not value:
                continue

            if field_name not in self.data:
                self.data[field_name] = value
                continue

            if self.data[field_name] == value:
                continue

            # 冲突：保留第一个值，其余登记到报告里等你裁决
            bucket = self.conflicts.setdefault(
                field_name,
                [{"value": self.data[field_name], "source": self.sources[0]}],
            )
            if not any(item["value"] == value for item in bucket):
                bucket.append({"value": value, "source": source_label})

    def to_dict(self):
        return {
            **self.data,
            "_meta": {
                "key_field": self.key_field,
                "sources": self.sources,
                "conflicts": [
                    {"field": k, "candidates": v} for k, v in self.conflicts.items()
                ],
            },
        }


class EntityStore:
    """主键值 -> Entity 的字典。扩展多主键时只需要动 resolve_key。"""

    def __init__(self):
        self.entities: dict[str, Entity] = {}
        self.unmatched: list[Record] = []

    def resolve_key(self, record: Record):
        """按 config.PRIMARY_KEY_FIELDS 的顺序找第一个能用的主键。"""
        for field_name in config.PRIMARY_KEY_FIELDS:
            value = clean_value(record.data.get(field_name, ""))
            if value:
                return field_name, value
        return None, None

    def mount(self, record: Record):
        key_field, key_value = self.resolve_key(record)
        if key_value is None:
            self.unmatched.append(record)   # 没有主键，先搁置，不丢数据
            return

        entity = self.entities.get(key_value)
        if entity is None:
            # 第一次见到这个主键 → 分配「结构体内存」
            entity = Entity(key_field, key_value)
            self.entities[key_value] = entity
        entity.attach(record)


# ---------------------------------------------------------------- 抽取
def normalize_records(records: list[Record]) -> list[Record]:
    """把键名统一成标准字段名，值统一成字符串。"""
    for record in records:
        data = {}
        for key, value in record.data.items():
            canon = canonical(key)
            value = clean_value(value)
            if value:
                data[canon] = value
        record.data = data
    return records


def extract_file(name: str, source) -> list[Record]:
    """按扩展名选抽取器；source 可以是路径，也可以是 bytes / BytesIO。"""
    suffix = Path(name).suffix.lower()
    extractor = EXTRACTORS.get(suffix)
    if extractor is None:
        raise ValueError(f"不支持的文件类型：{name}（支持 xlsx / xlsm / docx / pdf）")
    return normalize_records(extractor(source, name))


def build_store(records: list[Record]) -> EntityStore:
    store = EntityStore()
    for record in records:
        store.mount(record)
    return store


def compute_stats(records: list[Record], store: EntityStore) -> dict:
    return {
        "files": len({r.source for r in records}),
        "records": len(records),
        "entities": len(store.entities),
        "unmatched": len(store.unmatched),
        "conflict_fields": sum(len(e.conflicts) for e in store.entities.values()),
    }


def build_payload(records: list[Record], store: EntityStore) -> dict:
    return {
        "summary": compute_stats(records, store),
        "entities": {k: e.to_dict() for k, e in store.entities.items()},
        "unmatched_records": [
            {"source": r.source, "location": r.location, "data": r.data}
            for r in store.unmatched
        ],
    }


def build_conflict_markdown(payload: dict) -> str:
    stats = payload["summary"]
    lines = ["# 合并冲突报告", ""]
    lines.append(f"- 输入文件：{stats['files']} 个")
    lines.append(f"- 抽取记录：{stats['records']} 条")
    lines.append(f"- 合并实体：{stats['entities']} 个")
    lines.append(f"- 无主键挂置：{stats['unmatched']} 条")
    lines.append("")

    conflict_entities = {
        k: e for k, e in payload["entities"].items() if e["_meta"]["conflicts"]
    }
    if not conflict_entities:
        lines.append("✅ 没有字段冲突。")
    else:
        lines.append(f"⚠ {len(conflict_entities)} 个实体存在冲突（保留第一个值，其余列出待裁决）：")
        lines.append("")
        for key, entity in conflict_entities.items():
            lines.append(f"## {key}")
            for item in entity["_meta"]["conflicts"]:
                lines.append(f"- **{item['field']}**")
                for candidate in item["candidates"]:
                    lines.append(f"  - `{candidate['value']}`  ← {candidate['source']}")
            lines.append("")

    if payload["unmatched_records"]:
        lines.append("## 没有匹配到主键的记录")
        for record in payload["unmatched_records"]:
            lines.append(f"- {record['source']} {record['location']}：{record['data']}")
    return "\n".join(lines)