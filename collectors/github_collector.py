"""
github_collector.py - GitHub 热门内容抓取器
============================================
抓取与配置 Topics 相关的热门仓库，并读取 README 摘要。
"""

import sys
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from github import Github, GithubException

# 将上级目录加入 path，以便导入 config
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger(__name__)


def _safe_get_readme(repo) -> str:
    """安全地获取仓库 README 前 1500 字符（如果不存在则返回描述）。"""
    try:
        readme = repo.get_readme()
        content = readme.decoded_content.decode("utf-8", errors="replace")
        # 去除 HTML 标签（简单处理）
        import re
        content = re.sub(r"<[^>]+>", "", content)
        return content[:1500].strip()
    except Exception:
        return repo.description or ""


def collect_github(max_repos: Optional[int] = None) -> list[dict]:
    """
    按配置的 Topics 搜索热门仓库。

    Returns:
        list of dict, 每项包含:
            - title: str
            - url: str
            - description: str
            - readme_snippet: str
            - stars: int
            - language: str | None
            - topics: list[str]
            - pushed_at: str (ISO 日期)
            - source: "github"
    """
    if not config.GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN 未配置，使用未认证模式（速率限制较严）")
        gh = Github()
    else:
        gh = Github(config.GITHUB_TOKEN)

    max_repos = max_repos or config.GITHUB_MAX_REPOS
    days_back = config.GITHUB_DAYS_LOOKBACK
    min_stars = config.GITHUB_MIN_STARS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    collected: list[dict] = []
    seen_ids: set[int] = set()

    for topic in config.GITHUB_TOPICS:
        if len(collected) >= max_repos:
            break
        try:
            query = f"topic:{topic} stars:>={min_stars} pushed:>={cutoff.strftime('%Y-%m-%d')}"
            results = gh.search_repositories(query=query, sort="stars", order="desc")

            count = 0
            for repo in results:
                if len(collected) >= max_repos:
                    break
                if repo.id in seen_ids:
                    continue
                seen_ids.add(repo.id)

                readme_snippet = _safe_get_readme(repo)
                item = {
                    "title": repo.full_name,
                    "url": repo.html_url,
                    "description": repo.description or "",
                    "readme_snippet": readme_snippet,
                    "stars": repo.stargazers_count,
                    "language": repo.language,
                    "topics": repo.get_topics(),
                    "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else "",
                    "source": "github",
                }
                collected.append(item)
                count += 1

                # 避免触发速率限制
                if count % 5 == 0:
                    time.sleep(1)

        except GithubException as e:
            logger.error(f"GitHub 搜索 topic={topic} 失败: {e}")
        except Exception as e:
            logger.error(f"未知错误 topic={topic}: {e}")

    logger.info(f"GitHub: 共收集 {len(collected)} 个仓库")
    return collected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    items = collect_github()
    for item in items:
        print(f"⭐ {item['stars']:,}  {item['title']}")
        print(f"   {item['url']}")
        print(f"   {item['description'][:80]}")
        print()
