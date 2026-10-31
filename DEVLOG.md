# 开发日志 · DEVLOG

> 目的：后续更新时**不用从头读代码**，看这一页就能接上。
> 最后更新：2026-10-31 ｜ 版本：v1.0.1 ｜ 开发者：chen2604329@qq.com

---

## 1. 这个项目是什么

把散落在 **Excel / Word / PDF** 里的同一批数据，按**主键（默认"姓名"）**合并成一个个完整实体，
再交给大模型生成分析报告。核心比喻：C 语言的 `malloc` 一块结构体，再拿指针往里填字段。

- 交付形态：Streamlit Web 应用（用户上传 → 内存合并 → 展示 + 下载）
- 同时保留一套命令行流程（`merge.py` + `ai_agent.py`）
- 已部署到云服务器（无头模式运行，见第 8 节）

---

## 2. 数据流（看这一条就懂整体）

```
上传文件(bytes) 或 本地路径
        │  core.extract_file(name, source)      ← 按扩展名选抽取器
        ▼
extractors/*.py →  list[Record]                ← Record(data, source, location)
        │  base.canonical() 归一化字段名（手机/电话/联系方式 → 手机号）
        ▼
core.build_store(records)                      ← EntityStore.mount()
        │  按 PRIMARY_KEY_FIELDS 顺序找主键
        │  命中 → 已有实体 attach()，没有 → 新建 Entity（分配"内存"）
        ▼
core.build_payload(store)                      ← dict：summary / entities / unmatched_records
        ├─ app.py      → st.json / 冲突页 / AI 报告 / 下载按钮
        └─ merge.py    → output/merged.json + merged.xlsx + conflicts.md
```

**合并规则**：新字段直接挂；同值忽略；**不同值不覆盖**，保留第一个并把候选值+来源记进 `_meta.conflicts`；
没有主键的记录进 `unmatched_records`，绝不丢数据。

---

## 3. 文件职责（改哪儿先看这里）

| 文件 | 职责 | 什么时候要动 |
| --- | --- | --- |
| `app.py` | Streamlit 界面、侧边栏配置、AI 调用、结果展示 | 改 UI / 下载项 / 提示文案 |
| `core.py` | `Entity`、`EntityStore`、抽取调度、payload、冲突报告 | 改合并规则、加统计字段 |
| `extractors/base.py` | `Record`、字段归一化、表头定位、合计行过滤 | 加别名、改表头识别逻辑 |
| `extractors/*_extractor.py` | 各格式摊平成 `Record` | 支持新格式（如 .csv/.txt） |
| `config.py` | 主键、别名表、OCR 开关、找中文字体 | **90% 的定制都在这一个文件** |
| `merge.py` | 命令行入口 + 写 JSON/Excel/冲突报告 | 改 CLI 输出 |
| `ai_agent.py` | 命令行版 AI 分析（读 output/merged.json） | 改 Prompt |
| `idle_guard.py` | 浏览器全关后自动关服务（端口监视） | 改宽限时长/退出策略 |
| `启动.vbs` / `停止.vbs` | 无黑框启动/关闭（Windows） | 改端口、改解释器路径 |
| `make_sample.py` / `generate_demo.py` | 生成 CLI 样例 / 演示数据 | 换演示内容 |
| `demo/` | 演示数据 01-04 + 演示脚本 | 录视频、答辩 |

---

## 4. 关键设计决策（含"为什么"，别轻易推翻）

1. **主键用列表而不是单个字段** —— `config.PRIMARY_KEY_FIELDS = ["姓名"]`，按顺序回退。
   想加手机号只改这一行；重名场景将来可扩成 `["手机号", "姓名"]` 或复合键。
2. **别名表集中管理** —— `FIELD_ALIASES` 把「手机/电话/联系方式/tel」映射成「手机号」。
   不做这一步，跨文件字段永远对不上。
3. **冲突不自动选值** —— 自动选等于替业务做决定。现在保留首个值 + 全部候选进报告，人工裁决。
4. **表头自动定位** —— 真实表格上方常压着合并的大标题，`find_header_index()` 在前 10 行里找
   命中已知字段最多的一行当表头。
5. **合计行过滤** —— `is_summary_row()` 丢掉「合计/总计/小计…」，否则会多出一个叫"合计"的人。
6. **Excel 遍历所有 Sheet** —— 早期只读 `wb.active`，数据在第二个 Sheet 就静默丢光（真实踩过）。
7. **不叫 `watchdog.py`** —— 会和 Streamlit 依赖的 `watchdog` 包撞名，导致别人部署时文件监视挂掉，
   所以叫 `idle_guard.py`。
8. **密钥走 `.env` 不写死在源码** —— `.gitignore` 已排除；云上用环境变量或 `st.secrets`。
9. **`core.py` 被 CLI 和 Web 共用** —— 避免两套逻辑行为不一致（早期就是两份代码）。

---

## 5. 踩过的坑（重复犯的概率很高）

| 坑 | 现象 | 解法 |
| --- | --- | --- |
| Windows 控制台 GBK | `print("✅")` 直接 `UnicodeEncodeError` 崩掉 | 入口脚本里 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` |
| VBS 编码 | 中文 `MsgBox` 报「无效字符」 | `.vbs` 必须存成 **UTF-16（带 BOM）**，UTF-8 会被按 ANSI 读 |
| VBS 起 pythonw | 用 `WshShell.Exec` 启动 pythonw，端口一直不监听 | 改用 `Run(..., 0, False)` 隐藏启动，再用 netstat 反查 PID |
| PyMuPDF 中文字体 | 内置字体没有中文字形，PDF 里全是方块 | `insert_font(fontfile=...)` + `doc.subset_fonts()`（不 subset 会 19MB） |
| openpyxl 只读 active | 多 Sheet 文件只解析第一个 | 遍历 `wb.worksheets` |
| 表头被大标题顶掉 | 整列错位，所有人进 unmatched | `find_header_index()` |
| 上传文件是内存流 | 抽取器只接受路径就报错 | 三个 extractor 都支持 `bytes/BytesIO` 与路径 |
| Streamlit 状态丢失 | 点下载按钮会重跑脚本，结果消失 | 结果存 `st.session_state` |
| 假密钥"已就绪" | 云端没配真 Key，侧边栏却绿色通过，点分析才 401 | `is_valid_key()` 严格校验（非空 + 长度≥20 + `sk-` 开头），按钮里 `st.error` + `st.stop()` 拦截 |

---

## 6. 已知限制（不是 bug，是没做）

- **扫描件 PDF**：只检测（无文字层告警）+ 跳过，OCR 开关 `config.ENABLE_OCR` 预留，未实现。
- **超大文件**：几十 MB 的 PDF / 十万行 Excel 未做流式处理和压测。
- **合并单元格**：跨行跨列的复杂表格没专门处理（标准表格没问题）。
- **重名**：只有姓名主键时会错误合并，需要复合主键。
- **并发/鉴权**：无用户体系、无权限控制，单机单用户假设。
- **AI 报告长度**：`max_tokens=1500`，数据量大时可能截断。

## 7. 下一步 TODO（按优先级）

1. OCR 接入（PaddleOCR / Tesseract），配合 `ENABLE_OCR`
2. 复合主键（姓名 + 手机号），解决重名
3. 大文件流式解析 + 进度反馈
4. 结果页加列筛选/搜索，实体多时更好找
5. `st.secrets` 适配 + Docker 化，方便云上多实例

---

## 8. 云服务器部署（你已上传的那套）

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple   # 国内镜像快很多
streamlit run app.py --server.headless true --server.port 8501 --server.address 0.0.0.0
```

- **必须 `--server.headless true`**，否则服务器上会尝试开浏览器。
- 要有公网访问：`--server.address 0.0.0.0` + 安全组/防火墙放行端口。
- 挂 Nginx 反代时，通常还要 `--server.enableCORS false --server.enableXsrfProtection false`
  （或正确配置 `server.enableXsrfProtection` + 域名）。
- **密钥别进代码**：云上用环境变量，或 `.streamlit/secrets.toml`（读取处改成 `st.secrets`）。
- 常驻运行：`systemd` / `tmux` / `docker`；纯粹的 `nohup &` 重启后会没。
- 两个 `.vbs` 是 Windows 桌面用的，服务器上不需要。

---

## 9. 怎么快速自测（改完先跑这个）

```bash
python generate_demo.py        # 重建演示数据（4 个文件 / 17 条 / 9 实体 / 1 冲突）
python merge.py                # CLI 全链路：input/ → output/
streamlit run app.py           # Web 全链路：上传 → 合并 → AI → 下载
```

判据（改坏了对照这里）：

- `demo/` 4 个文件 → **17 条记录 / 9 个实体 / 1 处冲突（李四·手机号）**
- 张三应来自 **4 个来源**（4 个文件都有他）
- `input/` 3 个样例 → 12 条 / 7 个实体 / 1 处冲突

改抽取逻辑后，重点回归这 7 种脏数据（曾写脚本验证过，脚本已清理，改动时可临时重写）：
多 Sheet、表头上方有大标题、空行+合计行、纯段落 Word、跨页重复表头 PDF、无主键文件、无文字层扫描件。

---

## 10. 变更记录

| 日期 | 版本 | 内容 |
| --- | --- | --- |
| 2026-10-31 | v1.0.0 | MVP：三格式抽取、实体合并、冲突报告、Streamlit 界面、AI 分析、CLI 流程、演示数据、启动器与自动退出、依赖与跨平台校验 |
| 2026-10-31 | v1.0.1 | 密钥校验修复：`is_valid_key()` 严格判定（空/短/非 sk- 一律无效），侧边栏黄条提示，点开始分析时 `st.stop()` 拦截；密钥支持 `st.secrets`（云端）→ 环境变量（本地）→ 界面输入 的优先级 |