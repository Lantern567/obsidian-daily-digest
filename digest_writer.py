"""
digest_writer.py - Obsidian Markdown 日报生成器
=================================================
将经过 Claude 打分摘要后的内容写入 Obsidian vault，
生成美观的每日日报 Markdown 文件。
"""

import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config

logger = logging.getLogger(__name__)

# 来源 Emoji 映射
SOURCE_EMOJI = {
    "github": "🐙",
    "youtube": "📺",
    "rss": "📰",
    "unknown": "🔗",
}

SCORE_LABEL = {
    9: "🔥 极度推荐",
    8: "⭐ 强烈推荐",
    7: "👍 值得关注",
    6: "💡 可以一看",
    5: "📌 备选参考",
}


def _score_label(score: int) -> str:
    for threshold, label in SCORE_LABEL.items():
        if score >= threshold:
            return label
    return "📌 备选参考"


def _format_github_item(item: dict) -> str:
    """格式化 GitHub 仓库条目。"""
    stars = item.get("stars", 0)
    lang = item.get("language") or "未知"
    topics = item.get("topics", [])
    topic_tags = " ".join(f"`{t}`" for t in topics[:5])

    lines = [
        f"### [{item['title']}]({item['url']})",
        f"> {_score_label(item['ai_score'])}  ·  ⭐ {stars:,} Stars  ·  {lang}",
        f">",
        f"> {item['ai_summary']}",
        f">",
        f"> **为什么推荐**: {item['ai_reason']}",
    ]
    if topic_tags:
        lines.append(f"> **Topics**: {topic_tags}")
    return "\n".join(lines)


def _format_youtube_item(item: dict) -> str:
    """格式化 YouTube 视频条目。"""
    channel = item.get("channel", "未知频道")
    pub = item.get("published_at", "")[:10]

    lines = [
        f"### [{item['title']}]({item['url']})",
        f"> {_score_label(item['ai_score'])}  ·  📺 {channel}  ·  {pub}",
        f">",
        f"> {item['ai_summary']}",
        f">",
        f"> **为什么推荐**: {item['ai_reason']}",
    ]
    has_transcript = "✅ 有字幕" if item.get("transcript_snippet") else "❌ 无字幕（基于描述摘要）"
    lines.append(f"> {has_transcript}")
    return "\n".join(lines)


def _format_rss_item(item: dict) -> str:
    """格式化 RSS 文章条目。"""
    feed = item.get("feed_title", "未知来源")
    pub = item.get("published_at", "")[:10]

    lines = [
        f"### [{item['title']}]({item['url']})",
        f"> {_score_label(item['ai_score'])}  ·  📰 {feed}  ·  {pub}",
        f">",
        f"> {item['ai_summary']}",
        f">",
        f"> **为什么推荐**: {item['ai_reason']}",
    ]
    return "\n".join(lines)


def _format_item(item: dict) -> str:
    """根据来源选择对应的格式化函数。"""
    source = item.get("source", "unknown")
    if source == "github":
        return _format_github_item(item)
    elif source == "youtube":
        return _format_youtube_item(item)
    elif source == "rss":
        return _format_rss_item(item)
    else:
        return (
            f"### [{item['title']}]({item['url']})\n"
            f"> {item.get('ai_summary', '')}\n"
        )


def write_digest(items: list[dict], digest_date: date = None) -> Path:
    """
    将摘要后的内容写入 Obsidian vault 的日报文件。

    Args:
        items: 经过 summarizer 处理后的条目列表（含 ai_score, ai_summary 等）
        digest_date: 日报日期，默认为今天

    Returns:
        写入的文件路径
    """
    if digest_date is None:
        digest_date = date.today()

    date_str = digest_date.strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 确保输出文件夹存在
    output_dir = config.VAULT_ROOT / config.OUTPUT_FOLDER
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{date_str}.md"

    # 按来源分组
    groups: dict[str, list[dict]] = {}
    for item in items:
        src = item.get("source", "unknown")
        groups.setdefault(src, []).append(item)

    source_count = {src: len(lst) for src, lst in groups.items()}
    sources_used = list(groups.keys())

    # ─── 生成 Frontmatter ───
    frontmatter = f"""---
date: {date_str}
type: daily-digest
tags:
  - daily-digest
sources: [{', '.join(sources_used)}]
total_items: {len(items)}
generated_at: "{now_str}"
---"""

    # ─── 生成标题区 ───
    header = f"""# 🗞️ 每日精选 · {date_str}

> 生成时间：{now_str}  |  共 {len(items)} 条内容
> 📊 来源：{' · '.join(f"{SOURCE_EMOJI.get(s,'🔗')} {s.upper()} ({source_count[s]})" for s in sources_used)}

---"""

    # ─── 生成各分区内容 ───
    sections = []

    if "github" in groups:
        section = f"## {SOURCE_EMOJI['github']} GitHub 项目\n\n"
        section += "\n\n---\n\n".join(_format_item(item) for item in groups["github"])
        sections.append(section)

    if "youtube" in groups:
        section = f"## {SOURCE_EMOJI['youtube']} YouTube 视频\n\n"
        section += "\n\n---\n\n".join(_format_item(item) for item in groups["youtube"])
        sections.append(section)

    if "rss" in groups:
        section = f"## {SOURCE_EMOJI['rss']} 文章 & 资讯\n\n"
        section += "\n\n---\n\n".join(_format_item(item) for item in groups["rss"])
        sections.append(section)

    # ─── 打分区（供反馈用） ───
    feedback_table = _build_feedback_table(items)

    # ─── 隐藏元数据（供 feedback.py 读取） ───
    metadata_json = json.dumps(
        [
            {
                "title": item["title"],
                "url": item["url"],
                "source": item.get("source", "unknown"),
                "ai_summary": item.get("ai_summary", ""),
                "ai_score": item.get("ai_score", 0),
            }
            for item in items
        ],
        ensure_ascii=False,
        indent=2,
    )
    hidden_metadata = f"<!-- DIGEST_DATA: {metadata_json} -->"

    # ─── 组合全文 ───
    full_content = "\n\n".join(
        [
            frontmatter,
            header,
            "\n\n".join(sections),
            feedback_table,
            hidden_metadata,
        ]
    )

    output_path.write_text(full_content, encoding="utf-8")
    logger.info(f"日报已写入: {output_path}")
    return output_path


def _build_feedback_table(items: list[dict]) -> str:
    """生成打分区块，引导用户反馈。"""
    lines = [
        "## 💬 今日评分",
        "",
        "> 运行 `python feedback.py` 进行交互式打分，或直接在下表填写后保存。",
        "> 评分: 1=不感兴趣 · 2=一般 · 3=还不错 · 4=很好 · 5=极好",
        "",
        "| # | 标题 | 来源 | AI评分 | 你的评分 | 备注 |",
        "|---|------|------|--------|---------|------|",
    ]
    for i, item in enumerate(items, 1):
        emoji = SOURCE_EMOJI.get(item.get("source", "unknown"), "🔗")
        title_short = item["title"][:45] + ("…" if len(item["title"]) > 45 else "")
        lines.append(
            f"| {i} | [{title_short}]({item['url']}) "
            f"| {emoji} {item.get('source','').upper()} "
            f"| {item.get('ai_score','-')}/10 "
            f"|  "
            f"|  |"
        )
    return "\n".join(lines)
