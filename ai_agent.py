import json
import os
from pathlib import Path

from openai import OpenAI


def load_dotenv(path: Path) -> None:
    """极简 .env 读取：KEY=VALUE，忽略注释和空行，不覆盖已有环境变量。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")

    # 1. 读取配置（.env / 系统环境变量都行）
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://maas.qianwenaiapi.com/compatible-mode/v1")
    model_name = os.getenv("OPENAI_MODEL", "deepseek-v4.1-flash-1017")

    if not api_key:
        print("❌ 错误: 未找到 OPENAI_API_KEY，请在 .env 或系统环境变量里配置！")
        return

    # 初始化 OpenAI 客户端（兼容 DeepSeek / 通义 MaaS 等）
    client = OpenAI(api_key=api_key, base_url=base_url)

    # 2. 读取合并好的数据
    json_path = Path(__file__).resolve().parent / "output" / "merged.json"
    if not json_path.exists():
        print(f"❌ 错误: 找不到文件 {json_path}，请先运行 merge.py 生成数据！")
        return

    merged_data = json.loads(json_path.read_text(encoding="utf-8"))
    data_str = json.dumps(merged_data, ensure_ascii=False, indent=2)

    # 3. 构造 Prompt
    system_prompt = """
    你是一个专业的企业数据分析员。
    请阅读我提供的 JSON 数据，并完成以下任务：
    1. 【内容总结】：用一句话总结这批数据的核心内容。
    2. 【关联分析】：列出数据中关联最多（出现频率最高）的实体（如人名或项目名），并说明理由。
    3. 【核心提取】：整理出最关键的业务信息（如人员名单、对应的合同与手机号等），请用 Markdown 表格形式展示。
    """

    user_prompt = f"以下是合并后的多源异构文件数据：\n{data_str}"

    print(f"🚀 正在调用 {model_name} 进行分析，请稍候……")
    print(f"   base_url = {base_url}")
    print(f"   key = {api_key[:8]}…（已从 .env 读取）")

    # 4. 调用 API
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        ai_reply = response.choices[0].message.content

        # 5. 输出并保存
        print("\n" + "=" * 40)
        print("🤖 AI 分析报告：\n")
        print(ai_reply)
        print("=" * 40 + "\n")

        output_path = json_path.parent / "ai_analysis_report.md"
        output_path.write_text(ai_reply, encoding="utf-8")
        print(f"✅ 分析完成！报告已保存至 {output_path}")

    except Exception as e:
        print(f"❌ API 调用失败，错误信息: {e}")


if __name__ == "__main__":
    main()