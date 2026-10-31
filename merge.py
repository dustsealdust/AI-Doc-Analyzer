# -*- coding: utf-8 -*-
"""命令行入口：抽取 input/ 下的文件 → 合并 → 输出 JSON / Excel / 冲突报告。

用法（在 D:\\ai\\data-merge 下）：
    python make_sample.py     # 生成测试数据（input/ 为空时 merge.py 会自动调用）
    python merge.py           # 抽取 + 合并 + 输出
    python merge.py --rebuild-sample   # 强制重新生成测试数据再合并
"""
import json
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from core import (
    EXTRACTORS,
    build_conflict_markdown,
    build_payload,
    build_store,
    extract_file,
    normalize_records,
)

# Windows 控制台默认 GBK，直接 print emoji/ 生僻字会崩，这里兜一下
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def ensure_sample_if_empty():
    if any(config.INPUT_DIR.glob("*")):
        return
    print("input/ 是空的，先自动生成测试数据……")
    import make_sample
    make_sample.main()
    print()


def load_records() -> list:
    records = []
    files = sorted(p for p in config.INPUT_DIR.iterdir()
                   if p.is_file() and p.suffix.lower() in EXTRACTORS)
    if not files:
        print("⚠ input/ 里没有可处理的文件")
    for path in files:
        print(f"📄 抽取 {path.name} ……", end=" ")
        got = extract_file(path.name, path)
        print(f"{len(got)} 条")
        records.extend(got)
    return records


# ---------------------------------------------------------------- 输出
def write_json(payload: dict, path: Path):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_excel(payload: dict, path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "合并结果"

    columns = []
    for entity in payload["entities"].values():
        for field_name in entity:
            if field_name == "_meta" or field_name in columns:
                continue
            columns.append(field_name)

    ws.append(columns + ["来源", "冲突字段"])
    for entity in payload["entities"].values():
        row = [entity.get(c, "") for c in columns]
        row.append(" | ".join(entity["_meta"]["sources"]))
        row.append(", ".join(c["field"] for c in entity["_meta"]["conflicts"]))
        ws.append(row)

    for idx, col in enumerate(ws[1], start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = \
            40 if col in ("来源", "冲突字段") else 14
        col.font = openpyxl.styles.Font(bold=True)

    ws.freeze_panes = "A2"
    wb.save(str(path))


# ---------------------------------------------------------------- 入口
def main():
    if "--rebuild-sample" in sys.argv:
        import make_sample
        make_sample.main()

    for directory in (config.INPUT_DIR, config.OUTPUT_DIR, config.EXTRACTOR_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    ensure_sample_if_empty()

    records = load_records()
    store = build_store(records)
    payload = build_payload(records, store)
    stats = payload["summary"]

    write_json(payload, config.OUTPUT_DIR / "merged.json")
    write_excel(payload, config.OUTPUT_DIR / "merged.xlsx")
    (config.OUTPUT_DIR / "conflicts.md").write_text(
        build_conflict_markdown(payload), encoding="utf-8"
    )

    print()
    print("=" * 52)
    print(f"输入文件 {stats['files']} 个 / 记录 {stats['records']} 条")
    print(f"合并出实体 {stats['entities']} 个，字段冲突 {stats['conflict_fields']} 处")
    print(f"无主键挂置 {stats['unmatched']} 条")
    print("-" * 52)
    for key, entity in store.entities.items():
        flags = f"  ⚠冲突:{','.join(entity.conflicts)}" if entity.conflicts else ""
        fields = " ".join(f"{k}={v}" for k, v in entity.data.items())
        print(f"· {fields}{flags}")
    print("-" * 52)
    print(f"已输出到 {config.OUTPUT_DIR}")
    print("  merged.json / merged.xlsx / conflicts.md")


if __name__ == "__main__":
    main()