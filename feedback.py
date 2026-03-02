"""
feedback.py - 反馈记录与品味学习系统
======================================
使用方式：
  python feedback.py                  # 交互式录入今日日报的打分
  python feedback.py --date 2026-03-01  # 对指定日期的日报打分
  python feedback.py --stats            # 查看偏好统计报告
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config
from summarizer import _init_db, DB_PATH

# ─────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    _init_db()
    return sqlite3.connect(DB_PATH)


def save_feedback(
    date_str: str,
    source: str,
    title: str,
    url: str,
    score: int,
    notes: str = "",
    ai_summary: str = "",
):
    """将一条反馈写入数据库。"""
    conn = _get_conn()
    # 更新已有记录 or 插入新记录
    existing = conn.execute(
        "SELECT id FROM feedback WHERE date=? AND url=?", (date_str, url)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE feedback SET score=?, notes=?, ai_summary=? WHERE id=?",
            (score, notes, ai_summary, existing[0]),
        )
    else:
        conn.execute(
            """INSERT INTO feedback (date, source, title, url, score, notes, ai_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (date_str, source, title, url, score, notes, ai_summary),
        )
    conn.commit()
    conn.close()


def load_digest_items(date_str: str) -> list[dict]:
    """
    从对应日期的 Obsidian 日报文件中读取条目列表。
    日报文件格式见 digest_writer.py。
    返回 [{title, url, source, ai_summary}, ...]
    """
    vault_root = config.VAULT_ROOT
    digest_path = vault_root / config.OUTPUT_FOLDER / f"{date_str}.md"

    if not digest_path.exists():
        print(f"❌ 找不到日报文件: {digest_path}")
        return []

    content = digest_path.read_text(encoding="utf-8")

    # 解析日报中嵌入的 JSON 数据块（digest_writer.py 写入的隐藏元数据）
    # 格式: <!-- DIGEST_DATA: {...} -->
    match = re.search(r"<!-- DIGEST_DATA: ([\s\S]*?) -->", content)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 回退：正则解析 Markdown 标题和链接
    items = []
    # 匹配形如 ### [title](url) 的行
    for m in re.finditer(r"###\s+\[([^\]]+)\]\((https?://[^\)]+)\)", content):
        items.append({
            "title": m.group(1),
            "url": m.group(2),
            "source": "unknown",
            "ai_summary": "",
        })
    return items


# ─────────────────────────────────────────────────
# 交互式打分
# ─────────────────────────────────────────────────

def interactive_feedback(date_str: str):
    """逐条显示日报内容，引导用户打分。"""
    items = load_digest_items(date_str)
    if not items:
        print("没有可以打分的内容。")
        return

    print(f"\n📋 正在为 {date_str} 的日报打分（共 {len(items)} 条）")
    print("评分：1=不感兴趣  2=一般  3=还不错  4=很好  5=极好")
    print("直接按 Enter 跳过该条目\n")

    saved = 0
    for i, item in enumerate(items, 1):
        print(f"─── [{i}/{len(items)}] ───────────────────────────────")
        print(f"📌 {item['title']}")
        print(f"🔗 {item['url']}")
        if item.get("ai_summary"):
            print(f"💡 {item['ai_summary']}")
        print()

        while True:
            raw = input("评分 (1-5, 或 Enter 跳过): ").strip()
            if raw == "":
                print("  → 跳过\n")
                break
            if raw.isdigit() and 1 <= int(raw) <= 5:
                score = int(raw)
                notes = input("  备注 (可选, Enter 跳过): ").strip()
                save_feedback(
                    date_str=date_str,
                    source=item.get("source", "unknown"),
                    title=item["title"],
                    url=item["url"],
                    score=score,
                    notes=notes,
                    ai_summary=item.get("ai_summary", ""),
                )
                print(f"  → 已保存 ⭐ {score}/5\n")
                saved += 1
                break
            else:
                print("  请输入 1-5 的数字")

    print(f"\n✅ 完成！共保存 {saved} 条反馈。Claude 下次运行时将参考这些数据。")


# ─────────────────────────────────────────────────
# 统计报告
# ─────────────────────────────────────────────────

def show_stats():
    """打印偏好统计报告。"""
    conn = _get_conn()

    total = conn.execute("SELECT COUNT(*) FROM feedback WHERE score IS NOT NULL").fetchone()[0]
    if total == 0:
        print("还没有任何反馈数据。先运行一次日报再来打分吧！")
        conn.close()
        return

    avg_score = conn.execute(
        "SELECT AVG(score) FROM feedback WHERE score IS NOT NULL"
    ).fetchone()[0]

    print(f"\n📊 品味偏好统计报告")
    print(f"{'─'*40}")
    print(f"总反馈条数: {total}")
    print(f"平均评分:   {avg_score:.2f} / 5.0\n")

    # 各来源平均分
    print("各信源平均分:")
    for row in conn.execute(
        "SELECT source, COUNT(*), AVG(score) FROM feedback WHERE score IS NOT NULL GROUP BY source"
    ):
        print(f"  {row[0]:10s}  {row[1]:3d} 条  均分: {row[2]:.2f}")

    # 最高分内容
    print("\n⭐ 你最喜欢的内容（Top 5）:")
    for row in conn.execute(
        "SELECT title, source, score, notes FROM feedback WHERE score >= 4 ORDER BY score DESC, created_at DESC LIMIT 5"
    ):
        print(f"  [{row[2]}/5] [{row[1]}] {row[0][:60]}")
        if row[3]:
            print(f"           备注: {row[3]}")

    conn.close()


# ─────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Digest 反馈系统")
    parser.add_argument("--date", default=str(date.today()), help="日报日期 (YYYY-MM-DD)")
    parser.add_argument("--stats", action="store_true", help="显示偏好统计报告")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        interactive_feedback(args.date)
