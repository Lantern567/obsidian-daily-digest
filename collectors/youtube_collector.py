"""
youtube_collector.py - YouTube 内容抓取器
==========================================
从订阅频道 + 关键词搜索中获取近期视频，并抓取字幕作为内容摘要的基础。
使用 requests 直接调用 YouTube Data API v3，无需 google-api-python-client。
"""

import sys
import logging
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger(__name__)

# YouTube API 基础 URL
YT_API_BASE = "https://www.googleapis.com/youtube/v3"
VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"


class YouTubeClient:
    """轻量级 YouTube Data API v3 客户端，基于 requests。"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()

    def get(self, endpoint: str, **params) -> dict:
        """发送 GET 请求并返回 JSON，失败则抛出异常。"""
        params["key"] = self.api_key
        resp = self.session.get(f"{YT_API_BASE}/{endpoint}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search(self, **params) -> dict:
        return self.get("search", **params)

    def channels(self, **params) -> dict:
        return self.get("channels", **params)

    def playlist_items(self, **params) -> dict:
        return self.get("playlistItems", **params)


def _build_youtube_client() -> YouTubeClient:
    if not config.YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY 未在 .env 中配置")
    return YouTubeClient(config.YOUTUBE_API_KEY)


def _iso_cutoff(days_back: int) -> str:
    """返回 YouTube API 所需的 RFC 3339 格式时间字符串。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_transcript(video_id: str, max_chars: int = 2000) -> str:
    """
    尝试获取视频字幕（优先中文，其次英文，最后自动生成）。
    返回前 max_chars 个字符，失败则返回空字符串。
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        for lang in ["zh", "zh-Hans", "zh-CN", "en"]:
            try:
                transcript = transcript_list.find_transcript([lang])
                entries = transcript.fetch()
                text = " ".join(e["text"] for e in entries)
                return text[:max_chars]
            except Exception:
                continue

        try:
            transcript = transcript_list.find_generated_transcript(["en", "zh"])
            entries = transcript.fetch()
            text = " ".join(e["text"] for e in entries)
            return text[:max_chars]
        except Exception:
            pass

    except (NoTranscriptFound, TranscriptsDisabled):
        pass
    except Exception as e:
        logger.debug(f"获取字幕失败 video_id={video_id}: {e}")

    return ""


def _search_by_keyword(yt: YouTubeClient, keyword: str, days_back: int, max_results: int) -> list[dict]:
    """关键词搜索最新视频。"""
    items = []
    try:
        response = yt.search(
            q=keyword,
            part="snippet",
            type="video",
            order="date",
            publishedAfter=_iso_cutoff(days_back),
            maxResults=max_results,
        )
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id:
                continue
            transcript = _get_transcript(video_id)
            parsed = {
                "title": snippet.get("title", ""),
                "url": VIDEO_URL.format(video_id=video_id),
                "description": snippet.get("description", "")[:300],
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "transcript_snippet": transcript,
                "source": "youtube",
            }
            if parsed["title"]:
                items.append(parsed)

    except requests.HTTPError as e:
        logger.error(f"YouTube 关键词搜索失败 keyword={keyword}: {e}")
    except Exception as e:
        logger.error(f"YouTube 关键词搜索异常 keyword={keyword}: {e}")

    return items


def _fetch_channel_videos(yt: YouTubeClient, channel_id: str, days_back: int, max_results: int) -> list[dict]:
    """从指定频道获取最新视频（通过 uploads 播放列表）。"""
    items = []
    try:
        # 1. 获取频道的 uploads 播放列表 ID
        ch_response = yt.channels(id=channel_id, part="contentDetails")
        channels = ch_response.get("items", [])
        if not channels:
            logger.warning(f"频道 {channel_id} 不存在或无权限")
            return []

        uploads_playlist_id = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 2. 从播放列表获取最新视频
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        pl_response = yt.playlist_items(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=max_results,
        )

        for item in pl_response.get("items", []):
            snippet = item.get("snippet", {})
            published = snippet.get("publishedAt", "")
            if published:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue

            video_id = snippet.get("resourceId", {}).get("videoId", "")
            transcript = _get_transcript(video_id) if video_id else ""

            parsed = {
                "title": snippet.get("title", ""),
                "url": VIDEO_URL.format(video_id=video_id),
                "description": snippet.get("description", "")[:300],
                "channel": snippet.get("channelTitle", ""),
                "published_at": published,
                "transcript_snippet": transcript,
                "source": "youtube",
            }
            if parsed["title"]:
                items.append(parsed)

    except requests.HTTPError as e:
        logger.error(f"频道视频获取失败 channel_id={channel_id}: {e}")
    except Exception as e:
        logger.error(f"频道视频获取异常 channel_id={channel_id}: {e}")

    return items


def collect_youtube(max_total: Optional[int] = None) -> list[dict]:
    """
    综合抓取：订阅频道 + 关键词搜索。

    Returns:
        list of dict，每项包含:
            - title, url, description, channel,
            - published_at, transcript_snippet, source
    """
    if not config.YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY 未配置，跳过 YouTube 抓取")
        return []

    yt = _build_youtube_client()
    max_per_kw = config.YOUTUBE_MAX_RESULTS_PER_KEYWORD
    days_back = config.YOUTUBE_DAYS_LOOKBACK

    collected: list[dict] = []
    seen_urls: set[str] = set()

    # 1. 订阅频道
    for channel_id in config.YOUTUBE_CHANNEL_IDS:
        videos = _fetch_channel_videos(yt, channel_id, days_back, max_results=5)
        for v in videos:
            if v["url"] not in seen_urls:
                seen_urls.add(v["url"])
                collected.append(v)

    # 2. 关键词搜索
    for keyword in config.YOUTUBE_KEYWORDS:
        videos = _search_by_keyword(yt, keyword, days_back, max_per_kw)
        for v in videos:
            if v["url"] not in seen_urls:
                seen_urls.add(v["url"])
                collected.append(v)

    if max_total:
        collected = collected[:max_total]

    logger.info(f"YouTube: 共收集 {len(collected)} 个视频")
    return collected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    items = collect_youtube()
    for item in items:
        print(f"[{item['channel']}] {item['title']}")
        print(f"  {item['url']}")
        print(f"  {'有字幕' if item['transcript_snippet'] else '无字幕'}")
        print()
