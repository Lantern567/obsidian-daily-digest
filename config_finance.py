"""
config_finance.py - Finance Digest 配置文件
============================================
金融日报专用配置：美股、量化金融、宏观经济、金融大佬访谈。
由 main.py --profile finance 自动加载，不需要手动 import。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件中的 API 密钥（与 config.py 共享同一个 .env）
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

# ─────────────────────────────────────────────
# API 密钥（从 .env 文件读取）
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ─────────────────────────────────────────────
# Vault 路径配置
# ─────────────────────────────────────────────
VAULT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_FOLDER = "Finance Digest"  # 金融日报输出到独立文件夹

# ─────────────────────────────────────────────
# GitHub 配置 - 量化金融 / 金融科技仓库
# ─────────────────────────────────────────────
GITHUB_TOPICS = [
    "algorithmic-trading",
    "quantitative-finance",
    "fintech",
    "backtesting",
    "pandas-ta",
]

GITHUB_MIN_STARS = 200
GITHUB_MAX_REPOS = 10
GITHUB_DAYS_LOOKBACK = 7

# ─────────────────────────────────────────────
# YouTube 配置 - 金融频道 + 大佬访谈
# ─────────────────────────────────────────────
# 金融类官方频道（高质量原创内容）
YOUTUBE_CHANNEL_IDS = [
    "UCTLrD7MbZNJ5saCMJXY8s7A",  # Bloomberg Markets（待验证）
    "UCM9pcmFXFoFGJRSBFqDikFQ",  # Patrick Boyle 量化金融（待验证）
]

# 关键词搜索：金融大佬原始访谈 + 宏观经济 + 量化策略
YOUTUBE_KEYWORDS = [
    "Warren Buffett interview 2026",
    "Ray Dalio 2026",
    "Federal Reserve FOMC 2026",
    "US stock market outlook 2026",
    "quantitative finance tutorial",
    "algorithmic trading strategy",
    "hedge fund interview 2026",
    "Howard Marks memo",
]

YOUTUBE_MAX_RESULTS_PER_KEYWORD = 2

# 金融大佬访谈不一定每天都有，放宽时间窗口
YOUTUBE_DAYS_LOOKBACK = 14

# ─────────────────────────────────────────────
# RSS 配置 - 美股 / 宏观 / 量化资讯
# ─────────────────────────────────────────────
RSS_FEEDS = [
    # ── 美股 / 宏观资讯 ─────────────────────────
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",  # CNBC Markets
    "https://feeds.bloomberg.com/markets/news.rss",           # Bloomberg Markets
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",  # NYT Business
    "https://www.marketwatch.com/rss/topstories",             # MarketWatch
    "https://fortune.com/feed/fortune-feeds/?id=3230629",     # Fortune
    # ── 量化 / 金融科技 ──────────────────────────
    "https://quantocracy.com/feed/",                          # QuantOcracy（量化策略聚合）
    # ── 商业深度 ─────────────────────────────────
    "https://feeds.feedburner.com/typepad/alleyinsider/silicon_alley_insider",  # Business Insider Markets
]

RSS_MAX_ITEMS_PER_FEED = 3
RSS_DAYS_LOOKBACK = 2

# ─────────────────────────────────────────────
# Claude 和输出配置
# ─────────────────────────────────────────────
CLAUDE_MODEL = "claude-opus-4-6"

MAX_ITEMS_PER_DIGEST = 15
MIN_RELEVANCE_SCORE = 5

# 金融日报使用中文输出
DIGEST_LANGUAGE = "zh"
