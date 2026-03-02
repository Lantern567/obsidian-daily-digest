"""
rss_collector.py - RSS 订阅抓取器
====================================
从配置的 RSS/Atom 源拉取近期文章，提取标题、摘要和正文片段。
"""

import sys
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger(__name__)

# 请求头，模拟正常浏览器避免被拒绝
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DailyDigestBot/1.0; "
        "+https://github.com/daily-digest)"
    )
}


def _parse_entry_date(entry) -> Optional[datetime]:
    """从 feedparser entry 中解析发布日期，返回带时区的 datetime。"""
    # feedparser 提供 published_parsed 或 updated_parsed（struct_time，UTC）
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                import calendar
                ts = calendar.timegm(t)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass

    # 回退：raw 字符串解析
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(timezone.utc)
            except Exception:
                pass

    return None


def _extract_content(entry) -> str:
    """尽力提取文章正文，优先 content，其次 summary。"""
    # content 字段（Atom）
    content_list = getattr(entry, "content", [])
    if content_list:
        raw = content_list[0].get("value", "")
        if raw:
            # 简单去除 HTML 标签
            import re
            text = re.sub(r"<[^>]+>", "", raw)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:2000]

    # summary 字段（RSS / Atom 摘要）
    summary = getattr(entry, "summary", "")
    if summary:
        import re
        text = re.sub(r"<[^>]+>", "", summary)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:2000]

    return ""


def _fetch_feed(feed_url: str, days_back: int, max_items: int) -> list[dict]:
    """抓取单个 RSS/Atom 源。"""
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    try:
        # 先用 requests 下载，设置超时，再用 feedparser 解析
        resp = requests.get(feed_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        logger.warning(f"RSS 源拉取失败 {feed_url}: {e}")
        return []

    feed_title = getattr(feed.feed, "title", feed_url)
    count = 0

    for entry in feed.entries:
        if count >= max_items:
            break

        pub_date = _parse_entry_date(entry)
        if pub_date and pub_date < cutoff:
            continue  # 跳过太旧的文章

        title = getattr(entry, "title", "").strip()
        url = getattr(entry, "link", "").strip()
        if not title or not url:
            continue

        content_snippet = _extract_content(entry)

        items.append({
            "title": title,
            "url": url,
            "description": content_snippet[:500],   # 短摘要给 Claude 快速预览
            "content_snippet": content_snippet,      # 更长的内容供深度摘要
            "published_at": pub_date.isoformat() if pub_date else "",
            "feed_title": feed_title,
            "source": "rss",
        })
        count += 1

    logger.info(f"RSS: {feed_title} → {len(items)} 篇文章")
    return items


def collect_rss(max_total: Optional[int] = None) -> list[dict]:
    """
    抓取所有配置的 RSS 源。

    Returns:
        list of dict，每项包含:
            - title, url, description, content_snippet,
            - published_at, feed_title, source
    """
    collected: list[dict] = []
    seen_urls: set[str] = set()

    days_back = config.RSS_DAYS_LOOKBACK
    max_per_feed = config.RSS_MAX_ITEMS_PER_FEED

    for feed_url in config.RSS_FEEDS:
        items = _fetch_feed(feed_url, days_back, max_per_feed)
        for item in items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                collected.append(item)

    if max_total:
        collected = collected[:max_total]

    logger.info(f"RSS: 共收集 {len(collected)} 篇文章")
    return collected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    items = collect_rss()
    for item in items:
        print(f"📰 [{item['feed_title']}] {item['title']}")
        print(f"   {item['url']}")
        print(f"   {item['description'][:100]}")
        print()
