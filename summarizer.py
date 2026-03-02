"""
summarizer.py - Claude 摘要与品味过滤引擎
==========================================
使用 Claude API 对采集到的内容进行：
  1. 相关性打分（结合历史高分内容作为 few-shot 示例）
  2. 内容摘要生成
  3. 最终筛选和排序
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import anthropic

sys.path.insert(0, str(Path(__file__).parent))
import config

logger = logging.getLogger(__name__)

# 数据库路径（存储历史反馈，用于品味学习）
DB_PATH = Path(__file__).parent / "feedback.db"


# ─────────────────────────────────────────────────
# 数据库工具
# ─────────────────────────────────────────────────

def _init_db():
    """初始化 SQLite 数据库（首次运行时创建表）。"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            source      TEXT NOT NULL,
            title       TEXT NOT NULL,
            url         TEXT NOT NULL,
            score       INTEGER,        -- 你给的分数 1-5
            notes       TEXT,           -- 你的备注
            ai_summary  TEXT,           -- Claude 生成的摘要（存档）
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def _load_taste_examples(limit: int = 8) -> list[dict]:
    """
    从数据库读取高分历史（4-5 分），作为 Claude 的品味参考示例。
    返回格式：[{title, source, summary, score, notes}, ...]
    """
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """
        SELECT title, source, ai_summary, score, notes
        FROM feedback
        WHERE score >= 4
        ORDER BY score DESC, created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    return [
        {
            "title": r[0],
            "source": r[1],
            "summary": r[2] or "",
            "score": r[3],
            "notes": r[4] or "",
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────
# Claude 调用
# ─────────────────────────────────────────────────

def _build_system_prompt(taste_examples: list[dict]) -> str:
    """构建包含品味示例的 system prompt。"""
    base = f"""你是一个专业的技术内容策展助手，负责为用户筛选和摘要每日技术信息流。

用户的偏好语言是：{"中文" if config.DIGEST_LANGUAGE == "zh" else "English"}

你的任务是对每一条内容进行：
1. **相关性评分**（1-10 分）：结合用户历史喜好判断这条内容对用户的价值
2. **生成摘要**：用 2-4 句话提炼核心价值，说明"为什么值得关注"

评分标准：
- 9-10：极度相关，用户几乎肯定感兴趣
- 7-8：较相关，有一定参考价值
- 5-6：一般，勉强值得一看
- 1-4：不相关或质量低，不推荐
"""

    if taste_examples:
        base += "\n\n---\n## 用户历史高分内容（品味参考）\n\n"
        base += "以下是用户过去打高分（4-5/5）的内容，请参考这些来判断用户的偏好：\n\n"
        for i, ex in enumerate(taste_examples, 1):
            base += f"**示例 {i}**（用户评分 {ex['score']}/5）\n"
            base += f"- 标题: {ex['title']}\n"
            base += f"- 来源: {ex['source']}\n"
            if ex["summary"]:
                base += f"- 摘要: {ex['summary']}\n"
            if ex["notes"]:
                base += f"- 用户备注: {ex['notes']}\n"
            base += "\n"
        base += "---\n"

    return base


def _make_item_text(item: dict) -> str:
    """将一条原始采集数据格式化为给 Claude 看的文本。"""
    source = item.get("source", "unknown")
    lines = [f"**来源**: {source.upper()}", f"**标题**: {item.get('title', '')}"]

    if item.get("url"):
        lines.append(f"**链接**: {item['url']}")

    if source == "github":
        if item.get("stars"):
            lines.append(f"**Stars**: {item['stars']:,}")
        if item.get("language"):
            lines.append(f"**语言**: {item['language']}")
        if item.get("description"):
            lines.append(f"**简介**: {item['description']}")
        if item.get("readme_snippet"):
            lines.append(f"**README 片段**:\n{item['readme_snippet'][:800]}")

    elif source == "youtube":
        if item.get("channel"):
            lines.append(f"**频道**: {item['channel']}")
        if item.get("description"):
            lines.append(f"**视频描述**: {item['description']}")
        if item.get("transcript_snippet"):
            lines.append(f"**字幕片段**:\n{item['transcript_snippet'][:800]}")

    elif source == "rss":
        if item.get("feed_title"):
            lines.append(f"**订阅源**: {item['feed_title']}")
        if item.get("content_snippet"):
            lines.append(f"**正文片段**:\n{item['content_snippet'][:800]}")

    return "\n".join(lines)


def summarize_items(
    raw_items: list[dict],
    min_score: Optional[int] = None,
    max_output: Optional[int] = None,
) -> list[dict]:
    """
    对原始采集内容批量打分+摘要。

    Args:
        raw_items: 来自各 collector 的原始数据列表
        min_score: 低于此相关性分数的条目被过滤（默认读 config）
        max_output: 最多返回条目数（默认读 config）

    Returns:
        过滤并排序后的列表，每项新增：
            - ai_score: int (1-10)
            - ai_summary: str
            - ai_reason: str (推荐理由)
    """
    if not raw_items:
        return []

    min_score = min_score or config.MIN_RELEVANCE_SCORE
    max_output = max_output or config.MAX_ITEMS_PER_DIGEST

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    taste_examples = _load_taste_examples()
    system_prompt = _build_system_prompt(taste_examples)

    results: list[dict] = []

    # 逐条处理（保证每条独立打分，避免 token 过长）
    for i, item in enumerate(raw_items):
        logger.info(f"  摘要进度: {i+1}/{len(raw_items)} - {item.get('title', '')[:50]}")
        item_text = _make_item_text(item)

        user_message = f"""请对以下内容进行评估，并以 JSON 格式返回结果：

{item_text}

请严格按照以下 JSON 格式返回（不要包含其他文字）：
{{
  "score": <1到10的整数>,
  "summary": "<2-4句话的中文摘要，说明核心内容>",
  "reason": "<1-2句话说明为什么推荐或不推荐>"
}}
"""
        try:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text = response.content[0].text.strip()

            # 提取 JSON（Claude 有时会加```json ... ```包装）
            import re
            json_match = re.search(r"\{[\s\S]*\}", raw_text)
            if not json_match:
                logger.warning(f"Claude 返回格式异常: {raw_text[:100]}")
                continue

            parsed = json.loads(json_match.group())
            score = int(parsed.get("score", 0))
            summary = parsed.get("summary", "")
            reason = parsed.get("reason", "")

            if score < min_score:
                logger.debug(f"  跳过低分内容 score={score}: {item.get('title', '')[:40]}")
                continue

            enriched = dict(item)
            enriched["ai_score"] = score
            enriched["ai_summary"] = summary
            enriched["ai_reason"] = reason
            results.append(enriched)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
        except anthropic.APIError as e:
            logger.error(f"Claude API 错误: {e}")
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")

    # 按分数排序
    results.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
    return results[:max_output]
