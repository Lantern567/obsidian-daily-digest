"""
mailer.py — 日报邮件发送脚本

用法：
  uv run python mailer.py --profile tech     # 发送今日科技日报
  uv run python mailer.py --profile finance  # 发送今日金融日报
  uv run python mailer.py --profile tech --date 2026-03-01  # 指定日期
"""

import argparse
import os
import re
import smtplib
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Windows 终端默认 GBK，强制 stdout/stderr 使用 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import markdown as md
from dotenv import load_dotenv

# ── 加载 .env ──────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
RECIPIENT_EMAILS = [
    e.strip()
    for e in os.getenv("RECIPIENT_EMAILS", "").split(",")
    if e.strip()
]

# ── Vault 根目录（mailer.py 在 _tools/daily-digest/ 下）──
VAULT_ROOT = Path(__file__).parent.parent.parent

# ── Profile 配置 ───────────────────────────────────────────
PROFILES = {
    "tech": {
        "folder": "Daily Digest",
        "subject_prefix": "🗞️ 科技精选",
    },
    "finance": {
        "folder": "Finance Digest",
        "subject_prefix": "💰 金融精选",
    },
    "consumer": {
        "folder": "Consumer Digest",
        "subject_prefix": "🛒 消费精选",
    },
}

# ── HTML 模板 ──────────────────────────────────────────────
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 720px;
    margin: auto;
    padding: 24px 16px;
    color: #1a1a1a;
    line-height: 1.7;
    background: #ffffff;
  }}
  h1 {{
    font-size: 22px;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 8px;
    margin-bottom: 20px;
  }}
  h2 {{
    font-size: 17px;
    color: #1d4ed8;
    margin-top: 28px;
    margin-bottom: 8px;
  }}
  h3 {{
    font-size: 15px;
    color: #374151;
    margin-top: 16px;
    margin-bottom: 4px;
  }}
  a {{
    color: #2563eb;
    text-decoration: none;
  }}
  a:hover {{
    text-decoration: underline;
  }}
  p {{
    margin: 6px 0;
  }}
  code {{
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 13px;
    font-family: "SFMono-Regular", Consolas, monospace;
  }}
  pre {{
    background: #f3f4f6;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 13px;
  }}
  blockquote {{
    border-left: 3px solid #d1d5db;
    margin: 8px 0;
    padding: 4px 12px;
    color: #6b7280;
  }}
  hr {{
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 20px 0;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
  }}
  th, td {{
    border: 1px solid #e5e7eb;
    padding: 8px 12px;
    text-align: left;
  }}
  th {{
    background: #f9fafb;
    font-weight: 600;
  }}
  ul, ol {{
    padding-left: 20px;
  }}
  li {{
    margin: 4px 0;
  }}
  .footer {{
    color: #9ca3af;
    font-size: 12px;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #e5e7eb;
    text-align: center;
  }}
</style>
</head>
<body>
{content}
<div class="footer">
  由 Claudian 自动生成 · {send_date} · 如需退订请回复此邮件
</div>
</body>
</html>
"""


def strip_frontmatter(text: str) -> str:
    """剥离 YAML frontmatter（--- 之间的部分）。"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def clean_obsidian_syntax(text: str) -> str:
    """
    清理 Obsidian 专用语法，使其在邮件中可读：
    - [[note]]           → note
    - [[note|alias]]     → alias
    - ![[image.png]]     → [image] (图片无法内嵌邮件)
    """
    # 图片嵌入 ![[...]]
    text = re.sub(r"!\[\[([^\]]+)\]\]", r"[图片: \1]", text)
    # 带别名的 wikilink [[note|alias]]
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    # 普通 wikilink [[note]]
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text


def markdown_to_html(text: str) -> str:
    """将 Markdown 转换为 HTML，启用常用扩展。"""
    return md.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )


def send_email(subject: str, html_body: str, recipients: list[str]) -> None:
    """通过 SMTP 发送 HTML 邮件。"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipients, msg.as_string())


def main() -> None:
    parser = argparse.ArgumentParser(description="发送日报邮件")
    parser.add_argument(
        "--profile",
        choices=["tech", "finance", "consumer"],
        required=True,
        help="日报类型：tech（科技）、finance（金融）或 consumer（消费品）",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="日报日期，格式 YYYY-MM-DD（默认今天）",
    )
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    report_date = args.date

    # ── 检查 SMTP 配置 ──────────────────────────────────────
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️ SMTP 未配置：请在 _tools/daily-digest/.env 中填写 SMTP_USER 和 SMTP_PASS")
        sys.exit(0)

    if not RECIPIENT_EMAILS:
        print("⚠️ SMTP 未配置：请在 _tools/daily-digest/.env 中填写 RECIPIENT_EMAILS")
        sys.exit(0)

    # ── 定位日报文件 ────────────────────────────────────────
    digest_path = VAULT_ROOT / profile["folder"] / f"{report_date}.md"
    if not digest_path.exists():
        print(f"❌ 未找到日报文件：{digest_path}")
        print(f"   请先生成 {report_date} 的日报，或检查 --profile / --date 参数。")
        sys.exit(1)

    # ── 读取并处理 Markdown ─────────────────────────────────
    raw = digest_path.read_text(encoding="utf-8")
    body_md = strip_frontmatter(raw)
    body_md = clean_obsidian_syntax(body_md)
    body_html = markdown_to_html(body_md)

    # ── 组装 HTML 邮件正文 ──────────────────────────────────
    full_html = HTML_TEMPLATE.format(
        content=body_html,
        send_date=report_date,
    )

    # ── 构造邮件主题 ────────────────────────────────────────
    subject = f"{profile['subject_prefix']} · {report_date}"

    # ── 发送 ────────────────────────────────────────────────
    try:
        send_email(subject, full_html, RECIPIENT_EMAILS)
        print(f"✅ 邮件已发送")
        print(f"   主题：{subject}")
        print(f"   收件人：{', '.join(RECIPIENT_EMAILS)}")
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP 认证失败：请检查 SMTP_USER / SMTP_PASS 是否正确")
        print("   Gmail 用户需使用「应用专用密码」，而非账户密码")
        sys.exit(2)
    except smtplib.SMTPException as e:
        print(f"❌ SMTP 发送失败：{e}")
        sys.exit(2)
    except Exception as e:
        print(f"❌ 发生未知错误：{e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
