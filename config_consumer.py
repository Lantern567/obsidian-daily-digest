"""
config_consumer.py - Consumer Digest 配置文件
==============================================
消费品日报专用配置：汽车、数码、家电、家具、智能家居。
由 main.py --profile consumer 自动加载，不需要手动 import。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件中的 API 密钥（与其他 profile 共享同一个 .env）
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
OUTPUT_FOLDER = "Consumer Digest"  # 消费品日报输出到独立文件夹

# ─────────────────────────────────────────────
# GitHub 配置 - 消费品类无需 GitHub
# ─────────────────────────────────────────────
GITHUB_TOPICS = []          # 不采集 GitHub 仓库
GITHUB_MIN_STARS = 9999999  # 极高门槛等效禁用
GITHUB_MAX_REPOS = 0
GITHUB_DAYS_LOOKBACK = 7

# ─────────────────────────────────────────────
# YouTube 配置 - 官方品牌发布 + 专业评测频道
# ─────────────────────────────────────────────
YOUTUBE_CHANNEL_IDS = []    # 不订阅固定频道（消费品更新不规律）

# 关键词搜索：新品发布 + 专业评测 + 汽车试驾
YOUTUBE_KEYWORDS = [
    "new car release 2026",
    "flagship smartphone review 2026",
    "home appliance review 2026",
    "best laptop 2026",
    "electric vehicle review 2026",
    "smart home device 2026",
]

YOUTUBE_MAX_RESULTS_PER_KEYWORD = 1
YOUTUBE_DAYS_LOOKBACK = 3   # 消费品评测内容更新慢，放宽到 3 天

# ─────────────────────────────────────────────
# RSS 配置 - 汽车 / 数码 / 家电 / 家具 / 智能家居
# ─────────────────────────────────────────────
RSS_FEEDS = [
    # ── 数码 / 消费电子（国际）──────────────────
    "https://www.theverge.com/rss/gadgets/index.xml",       # The Verge 数码
    "https://www.engadget.com/rss.xml",                     # Engadget 全品类
    "https://www.tomsguide.com/feeds/all",                  # Tom's Guide 测评
    "https://www.gsmarena.com/rss-news-reviews.php3",       # GSMArena 手机
    # ── 汽车（国际）────────────────────────────
    "https://www.caranddriver.com/rss/articles.xml",        # Car and Driver
    "https://www.autoblog.com/rss.xml",                     # Autoblog
    "https://www.motortrend.com/feeds/",                    # Motor Trend
    # ── 消费品 / 家电 / 家居（国际）────────────
    "https://www.consumerreports.org/cro/news/index.htm",   # Consumer Reports
    "https://www.apartmenttherapy.com/main.rss",           # Apartment Therapy 家居
    "https://www.cnet.com/rss/news/",                       # CNET 综合科技消费
    # ── 国内消费品（中文）───────────────────────
    "https://feed.smzdm.com/",                              # 什么值得买（值得关注的消费品）
    "https://rss.autohome.com.cn/info/news/index.xml",      # 汽车之家新闻
]

RSS_MAX_ITEMS_PER_FEED = 3
RSS_DAYS_LOOKBACK = 2

# ─────────────────────────────────────────────
# Claude 和输出配置
# ─────────────────────────────────────────────
CLAUDE_MODEL = "claude-opus-4-6"

MAX_ITEMS_PER_DIGEST = 15
MIN_RELEVANCE_SCORE = 5

# 消费品日报使用中文输出
DIGEST_LANGUAGE = "zh"
