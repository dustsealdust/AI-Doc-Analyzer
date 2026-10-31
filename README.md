# 多源文件数据合并助手 · data-merge

> **开发者**：chen2604329@qq.com ｜ **版本**：v1.0.1
> © 2026 版权所有，保留一切权利。未经书面许可，禁止复制、二次分发或商业使用。详见 [COPYRIGHT.md](COPYRIGHT.md)。
>
> **要改代码先看 [DEVLOG.md](DEVLOG.md)**：架构、各文件职责、设计决策、踩过的坑、已知限制和 TODO 都在里面，不用从头读代码。

把 **PDF / Word / Excel** 里的数据，按 **主键（默认"姓名"）** 合并成一个个完整实体，
再交给大模型做总结分析。

底层思路就是 C 里那句 `struct Entity *e = malloc(...)`：先分配实体，再遍历文件把字段挂上去。

## 目录

```
data-merge/
├── app.py             # Streamlit Web 界面（上传 → 合并 → AI 分析 → 下载报告）
├── core.py            # 合并核心（CLI 和 Web 共用）：Entity / EntityStore / 抽取调度
├── merge.py           # 命令行入口：读 input/ → 合并 → 输出 output/
├── ai_agent.py        # 命令行版 AI 分析（读 output/merged.json）
├── config.py          # 主键、字段别名、OCR 开关
├── idle_guard.py      # 浏览器全关后自动关掉服务（不叫 watchdog，避免撞 Streamlit 的依赖包名）
├── extractors/        # 各格式抽取器（支持本地路径或内存 bytes）
├── demo/              # 演示数据：01-04 四个文件 + 演示脚本.md
├── input/             # CLI 输入目录（空时自动生成样例）
├── output/            # CLI 输出目录
├── 启动.vbs           # 双击：无黑框启动 Web 界面
├── 停止.vbs           # 双击：立即关闭
├── run_app.bat        # 控制台版启动（能看日志，调试用）
├── make_sample.py     # 生成 CLI 样例数据
├── generate_demo.py   # 重新生成 demo/ 演示数据
├── .env               # API Key / Base URL / Model（已 gitignore）
├── COPYRIGHT.md       # 版权声明与免责声明
└── requirements.txt
```

## 部署要求

| 项目 | 要求 |
| --- | --- |
| Python | **3.10+**（代码用了 `str \| None` 注解） |
| 系统 | Windows 用两个 `.vbs` 双击启动；核心代码本身跨平台，Mac/Linux 可直接 `streamlit run app.py` |
| 依赖 | `pip install -r requirements.txt`（约 100-200MB，国内建议加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`） |
| 密钥 | 填 `.env` 的三个变量，或在界面侧边栏临时填 |

首次运行：`pip install -r requirements.txt` → 双击 `启动.vbs` → 浏览器打开 `localhost:8501`。
`.env` 已在 `.gitignore` 里，打包分发时记得先清空里面的密钥。

## 用 Web 界面（推荐）

**双击 [`启动.vbs`](启动.vbs) 即可**：无黑框启动，自动打开浏览器；用完双击 [`停止.vbs`](停止.vbs) 关闭。

**关掉浏览器后会自动退出**：启动器会顺带拉起 `idle_guard.py`，它盯着 8501 端口的连接，
所有标签页关掉约 60 秒后自动结束 Streamlit（留 60 秒是为了避免刷新页面被误杀）。
想改宽限时长，启动前设环境变量 `WATCHDOG_GRACE=15` 即可。

命令行方式（会显示控制台窗口，便于看日志）：

```bash
pip install -r requirements.txt
streamlit run app.py      # 或双击 run_app.bat
```

- 侧边栏填 API Key / Base URL / Model，留空自动读 `.env`
- 主界面拖拽上传 xlsx / xlsm / docx / pdf，**多选**，文件只在内存里解析，不落盘
- 结果三个标签页：结构化数据（`st.json`）、冲突报告、AI 报告（`st.markdown`）
- 三个下载按钮：合并 JSON / 冲突报告 / Markdown 报告

## 用命令行

```bash
python make_sample.py              # 生成测试数据
python merge.py                    # 合并 input/ → output/
python merge.py --rebuild-sample   # 重生成测试数据再合并
python ai_agent.py                 # 调模型分析 output/merged.json
```

## 合并规则

| 情况 | 处理 |
| --- | --- |
| 新字段 | 直接挂到实体上 |
| 字段已存在且值相同 | 忽略 |
| 字段已存在但值不同 | **不覆盖**，保留第一个值，其余进冲突报告 |
| 记录里找不到主键 | 不丢数据，进 `unmatched_records` |

## 怎么扩展

- **加主键**（比如手机号）：`config.PRIMARY_KEY_FIELDS = ["姓名", "手机号"]`，按顺序找第一个命中的。
- **加字段别名**（"客户姓名"/"名字" 都算"姓名"）：改 `config.FIELD_ALIASES`。
- **扫描件 PDF**：`config.ENABLE_OCR = True` 后还需在 `pdf_extractor.py` 接 OCR，目前只告警跳过。
- **换模型**：只改 `.env` 三行，或在 Web 侧边栏直接覆盖。