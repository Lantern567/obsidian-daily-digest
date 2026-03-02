"""
config.py - Daily Digest 用户配置文件
============================================
在这里配置你的信息源偏好、API密钥路径、以及输出设置。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件中的 API 密钥
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

# ─────────────────────────────────────────────
# API 密钥（从 .env 文件读取，不要直接填写在这里）
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ─────────────────────────────────────────────
# Vault 路径配置
# ─────────────────────────────────────────────
# 脚本目录的两级上方就是 Vault 根目录
VAULT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_FOLDER = "Daily Digest"  # Obsidian vault 中的输出文件夹名

# ─────────────────────────────────────────────
# GitHub 配置
# ─────────────────────────────────────────────
# 要监控的 GitHub Topics（关键词）
GITHUB_TOPICS = [
    "llm",
    "ai-agent",
    "machine-learning",
    "python",
    "claude",
    "openai",
]

# 只显示 star 数大于此值的仓库
GITHUB_MIN_STARS = 50

# 每次最多抓取的仓库数量
GITHUB_MAX_REPOS = 12

# 监控最近几天内有更新的仓库（用于过滤）
GITHUB_DAYS_LOOKBACK = 7

# ─────────────────────────────────────────────
# YouTube 配置
# ─────────────────────────────────────────────
# 深度访谈类频道（更新频率低但质量高）
YOUTUBE_CHANNEL_IDS = [
    "UCnUYZLuoy1rq1aVMwx4aTzw",  # Lex Fridman Podcast - 顶级科技/AI 访谈
    "UCcefcZRL2oaA_uBNeo5UOWg",  # Y Combinator - 创业/科技思想（已验证）
    "UC9cn0TuPq4dnbTY-CBsm8XA",  # a16z - 顶级 VC 观点（已验证）
]

# 关键词搜索：AI 顶尖科学家 + 科技创始人的最新访谈/演讲
# 注意：金融大佬（Buffett、Dalio、Howard Marks 等）已移至 config_finance.py
YOUTUBE_KEYWORDS = [
    # AI 顶尖科学家 / 研究者（最高优先级）
    "Sam Altman interview",        # OpenAI CEO
    "Andrej Karpathy lecture",     # AI 研究者（前 Tesla / OpenAI）
    "Karpathy lecture",            # 同上，覆盖不同标题格式
    "Dario Amodei interview",      # Anthropic CEO
    "Demis Hassabis interview",    # Google DeepMind CEO
    # 科技领袖
    "Jensen Huang interview",      # NVIDIA CEO
    "Elon Musk interview",         # Tesla / SpaceX / xAI
    "Satya Nadella interview",     # Microsoft CEO
    "Sundar Pichai interview",     # Google CEO
    "Marc Andreessen interview",   # a16z
]

# 每个关键词最多抓取的视频数（关键词多了，每个少抓点）
YOUTUBE_MAX_RESULTS_PER_KEYWORD = 2

# 科学家访谈/讲座更稀少，放宽到14天确保能抓到
YOUTUBE_DAYS_LOOKBACK = 14

# ─────────────────────────────────────────────
# RSS 订阅配置
# ─────────────────────────────────────────────
# 添加你想订阅的 RSS 源
RSS_FEEDS = [
    # ── 科技资讯 ──────────────────────────────────
    "https://hnrss.org/frontpage",                        # Hacker News 头版（技术人员最爱）
    "https://hnrss.org/best",                             # Hacker News 精选
    "https://techcrunch.com/feed/",                       # TechCrunch（科技商业）
    "https://www.theverge.com/rss/index.xml",             # The Verge（科技产品/政策）
    "https://www.wired.com/feed/rss",                     # Wired（科技文化深度）
    "https://feeds.arstechnica.com/arstechnica/index",    # Ars Technica（技术深度）
    "https://www.technologyreview.com/feed/",             # MIT Technology Review
    # ── 金融 / 商业 ────────────────────────────────
    "https://fortune.com/feed/fortune-feeds/?id=3230629", # Fortune 科技频道
    "https://feeds.feedburner.com/typepad/alleyinsider/silicon_alley_insider",  # Business Insider Tech
    # ── AI 专项 ────────────────────────────────────
    "https://blog.langchain.dev/rss/",                    # LangChain 博客
    "https://simonwillison.net/atom/everything/",         # Simon Willison（AI 动态最佳追踪者）
    # "https://openai.com/blog/rss/",                     # OpenAI（403，已停用）
]

# 每个 RSS 源最多抓取的文章数
RSS_MAX_ITEMS_PER_FEED = 3

# 只抓取最近几天内的文章
RSS_DAYS_LOOKBACK = 2

# ─────────────────────────────────────────────
# Claude 和输出配置
# ─────────────────────────────────────────────
CLAUDE_MODEL = "claude-opus-4-6"

# 每日日报最多展示的条目数
MAX_ITEMS_PER_DIGEST = 15

# 相关性评分阈值（低于此分数不展示，1-10 分）
MIN_RELEVANCE_SCORE = 5

# 日报语言（Claude 会用此语言输出摘要）
# "zh" = 中文, "en" = 英文
DIGEST_LANGUAGE = "zh"
