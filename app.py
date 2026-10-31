# -*- coding: utf-8 -*-
# 多源文件数据合并助手
# 开发者：chen2604329@qq.com
# © 2026 版权所有，保留一切权利。未经书面许可，不得用于商业用途或二次分发。
"""Streamlit Web 界面：上传文件 → 内存合并 → AI 分析 → 下载报告。

启动：
    streamlit run app.py
"""
import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from core import build_conflict_markdown, build_payload, build_store, extract_file

BASE_DIR = Path(__file__).resolve().parent
DOTENV = BASE_DIR / ".env"

DEVELOPER_EMAIL = "chen2604329@qq.com"
APP_NAME = "多源文件数据合并助手"
APP_VERSION = "v1.0.0"
COPYRIGHT = f"© 2026 {APP_NAME} · 保留所有权利"

DEFAULT_BASE_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "deepseek-v4.1-flash-1017"

SYSTEM_PROMPT = """
你是一个专业的企业数据分析员。
请阅读我提供的 JSON 数据，并完成以下任务：
1. 【内容总结】：用一句话总结这批数据的核心内容。
2. 【关联分析】：列出数据中关联最多（出现频率最高）的实体（如人名或项目名），并说明理由。
3. 【核心提取】：整理出最关键的业务信息（如人员名单、对应的合同与手机号等），请用 Markdown 表格形式展示。
"""


# ---------------------------------------------------------------- 工具函数
def load_dotenv(path: Path) -> None:
    """极简 .env 读取：KEY=VALUE，忽略注释，不覆盖已有环境变量。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def mask(key: str) -> str:
    return f"{key[:8]}…{key[-4:]}" if len(key) > 14 else "已配置"


def run_llm(api_key: str, base_url: str, model: str, payload: dict) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    data_str = json.dumps(payload, ensure_ascii=False, indent=2)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"以下是合并后的多源异构文件数据：\n{data_str}"},
        ],
        temperature=0.3,
        max_tokens=1500,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------- 页面设置
st.set_page_config(
    page_title=APP_NAME,
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.8rem; padding-bottom: 1rem; max-width: 1180px;}
      #MainMenu, footer {visibility: hidden;}
      [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none;}

      .app-header {
        padding: 26px 30px;
        border-radius: 14px;
        background: linear-gradient(120deg, #0f172a 0%, #1d4ed8 100%);
        color: #ffffff;
        margin-bottom: 18px;
      }
      .app-header .title {font-size: 26px; font-weight: 700; letter-spacing: .5px;}
      .app-header .subtitle {font-size: 13.5px; opacity: .82; margin-top: 8px; line-height: 1.7;}
      .app-header .tag {
        display: inline-block; margin-top: 14px; padding: 3px 10px;
        font-size: 12px; border-radius: 999px;
        background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22);
      }

      .section-title {
        font-size: 15px; font-weight: 600; color: #0f172a;
        margin: 6px 0 10px 0; padding-left: 9px; border-left: 3px solid #1d4ed8;
      }

      div[data-testid="stMetric"] {
        background: #f8fafc; border: 1px solid #e6eaf2;
        border-radius: 10px; padding: 12px 14px;
      }
      div[data-testid="stMetricValue"] {font-size: 22px;}

      .app-footer {
        margin-top: 26px; padding-top: 14px; border-top: 1px solid #e6eaf2;
        font-size: 12.5px; color: #6b7280; line-height: 1.9;
      }
      .app-footer strong {color: #374151;}
      .stButton > button {border-radius: 8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="app-header">
      <div class="title">{APP_NAME}</div>
      <div class="subtitle">
        Excel / Word / PDF 跨源数据按主键合并为统一实体，并调用大模型生成结构化分析报告。
      </div>
      <div class="tag">当前主键：{'、'.join(config.PRIMARY_KEY_FIELDS)}</div>
      <div class="tag">支持格式：.xlsx / .xlsm / .docx / .pdf</div>
    </div>
    """,
    unsafe_allow_html=True,
)

load_dotenv(DOTENV)

# ---------------- 侧边栏：模型配置 + 关于 ----------------
with st.sidebar:
    st.subheader("模型配置")
    st.caption("留空则读取项目根目录 `.env` 中的配置")

    api_key_input = st.text_input(
        "API Key", value="", type="password",
        placeholder="留空 = 使用 .env 中的 OPENAI_API_KEY",
    )
    base_url_input = st.text_input(
        "Base URL", value=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    )
    model_input = st.text_input(
        "Model", value=os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    )

    effective_key = api_key_input.strip() or os.getenv("OPENAI_API_KEY", "")

    if effective_key:
        st.success(f"密钥已就绪：{mask(effective_key)}")
    else:
        st.warning("未检测到密钥，AI 分析功能不可用")

    if st.button("测试连接", use_container_width=True):
        if not effective_key:
            st.error("请先填写 API Key")
        else:
            try:
                with st.spinner("正在测试连接……"):
                    run_llm(effective_key, base_url_input.strip(),
                            model_input.strip(), {"ping": 1})
                st.success("连接成功")
            except Exception as exc:
                st.error(f"连接失败：{exc}")

    st.divider()

    st.subheader("关于")
    st.markdown(
        f"""
        <div style="font-size:13px;line-height:2;color:#374151;">
          <div><strong>开发者</strong>：{DEVELOPER_EMAIL}</div>
          <div><strong>版本</strong>：{APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("本工具为原创软件，受著作权法保护。未经许可，禁止复制、二次分发或商业使用。")
    st.caption(COPYRIGHT)

# ---------------- 主界面：上传 ----------------
st.markdown('<div class="section-title">文件上传</div>', unsafe_allow_html=True)

with st.container(border=True):
    uploaded = st.file_uploader(
        "拖拽文件到此处，或点击选择（支持多选）",
        type=["xlsx", "xlsm", "docx", "pdf"],
        accept_multiple_files=True,
        help="文件仅在内存中解析，不会保存到本地 input/ 目录",
    )

    if uploaded:
        st.dataframe(
            [
                {"文件名": f.name, "类型": Path(f.name).suffix.lower(),
                 "大小(KB)": round(f.size / 1024, 1)}
                for f in uploaded
            ],
            use_container_width=True,
            hide_index=True,
        )

col_run, col_clear, _ = st.columns([1.2, 1, 2.4])
run_clicked = col_run.button("开始合并并分析", type="primary", use_container_width=True)
if col_clear.button("清空结果", use_container_width=True):
    for key in ("payload", "report", "errors"):
        st.session_state.pop(key, None)

# ---------------- 执行 ----------------
if run_clicked:
    if not uploaded:
        st.warning("请先上传至少一个文件")
    else:
        errors, records = [], []
        progress = st.progress(0.0, text="正在解析文件……")
        for index, file in enumerate(uploaded, start=1):
            try:
                records.extend(extract_file(file.name, file.getvalue()))
            except Exception as exc:
                errors.append(f"{file.name}：{exc}")
            progress.progress(index / len(uploaded),
                              text=f"已解析 {index}/{len(uploaded)} 个文件")
        progress.empty()

        store = build_store(records)
        payload = build_payload(records, store)

        report = ""
        if effective_key:
            try:
                with st.spinner(f"正在调用 {model_input.strip()} 进行分析……"):
                    report = run_llm(effective_key, base_url_input.strip(),
                                     model_input.strip(), payload)
            except Exception as exc:
                errors.append(f"AI 分析失败：{exc}")
        else:
            errors.append("未配置 API Key，已跳过 AI 分析")

        st.session_state["payload"] = payload
        st.session_state["report"] = report
        st.session_state["errors"] = errors

for message in st.session_state.get("errors") or []:
    st.error(message)

payload = st.session_state.get("payload")
report = st.session_state.get("report", "")

# ---------------- 结果展示 ----------------
if payload:
    stats = payload["summary"]
    left, middle, right, last = st.columns(4)
    left.metric("输入文件", stats["files"])
    middle.metric("抽取记录", stats["records"])
    right.metric("合并实体", stats["entities"])
    last.metric("冲突字段", stats["conflict_fields"])

    tab_data, tab_conflict, tab_report = st.tabs(
        ["结构化数据", "冲突报告", "AI 分析报告"]
    )

    with tab_data:
        st.caption("按主键合并后的完整实体，包含字段来源与冲突信息")
        st.json(payload, expanded=False)
        st.download_button(
            "下载合并结果 JSON",
            data=json.dumps(payload, ensure_ascii=False, indent=2),
            file_name="merged.json",
            mime="application/json",
        )

    with tab_conflict:
        conflict_md = build_conflict_markdown(payload)
        st.markdown(conflict_md)
        st.download_button(
            "下载冲突报告",
            data=conflict_md,
            file_name="conflicts.md",
            mime="text/markdown",
        )

    with tab_report:
        if report:
            st.markdown(report)
            st.download_button(
                "下载 Markdown 报告",
                data=report,
                file_name="ai_analysis_report.md",
                mime="text/markdown",
            )
        else:
            st.info("暂无 AI 报告。配置 API Key 后重新点击「开始合并并分析」。")
else:
    st.info("上传文件后点击「开始合并并分析」。首次使用可先运行 `python make_sample.py` 生成测试数据。")

# ---------------- 页脚 ----------------
st.markdown(
    f"""
    <div class="app-footer">
      <div><strong>{APP_NAME}</strong> {APP_VERSION} · 开发者 <strong>{DEVELOPER_EMAIL}</strong></div>
      <div>{COPYRIGHT}。本软件为原创作品，未经开发者书面许可，不得复制、修改、二次分发或用于商业用途。</div>
    </div>
    """,
    unsafe_allow_html=True,
)