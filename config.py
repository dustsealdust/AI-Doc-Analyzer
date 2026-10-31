# -*- coding: utf-8 -*-
"""全局配置：目录、主键、字段别名、OCR 开关。

想加新的主键（比如手机号）→ 只改 PRIMARY_KEY_FIELDS。
想加新字段别名 → 只改 FIELD_ALIASES。
"""
from pathlib import Path

# ---------- 目录 ----------
ROOT_DIR = Path(__file__).resolve().parent
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
EXTRACTOR_DIR = ROOT_DIR / "extractors"

# ---------- 主键 ----------
# 按顺序尝试：先看「姓名」，找不到再看「手机号」……命中谁就用谁当主键。
# 以后要扩展，往列表里加一个字符串即可（例如 "手机号"）。
PRIMARY_KEY_FIELDS = ["姓名"]

# ---------- 字段别名 ----------
# 标准字段名 -> 该字段所有可能的写法（大小写、空格差异由代码容错）
FIELD_ALIASES = {
    "姓名": ["姓名", "名字", "客户姓名", "户主", "联系人", "员工姓名", "name", "fullname"],
    "手机号": ["手机号", "手机", "手机号码", "电话", "联系电话", "联系方式", "tel", "phone", "mobile"],
    "年龄": ["年龄", "age"],
    "城市": ["城市", "所在城市", "地区", "所在地", "居住地", "city"],
    "部门": ["部门", "所在部门", "所属部门", "department", "dept"],
    "职位": ["职位", "职务", "岗位", "title", "position", "job"],
    "邮箱": ["邮箱", "电子邮箱", "邮件", "电子邮件", "email", "e-mail", "mail"],
}

# ---------- PDF 扫描件 OCR 开关 ----------
# 先不跑 OCR：文字型 PDF 正常抽取；扫描件会被跳过并在报告里记一笔。
# 以后接上 OCR（如 PaddleOCR / Tesseract）再把这里改成 True。
ENABLE_OCR = False


def find_cjk_font():
    """找一个能显示中文的字体文件，给生成演示 PDF 用。

    返回路径字符串，找不到返回 None。兼容 Windows / macOS / Linux。
    """
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None