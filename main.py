"""
main.py - Daily Digest 主入口
==============================
手动运行:        python main.py
仅采集(供AI摘要): python main.py --collect-only
测试模式:        python main.py --dry-run --source rss
金融日报:        python main.py --profile finance --collect-only
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# ─── 优先解析 --profile，在任何 import config 之前完成猴子补丁 ───
# 这样所有 collectors 里的 `import config` 都会自动读取到正确的配置模块
_pre_parser = argparse.ArgumentParser(add_help=False)
_pre_parser.add_argument("--profile", choices=["tech", "finance"], default="tech")
_pre_args, _ = _pre_parser.parse_known_args()

sys.path.insert(0, str(Path(__file__).parent))

if _pre_args.profile == "finance":
    import config_finance as config
    sys.modules["config"] = config
else:
    import config
    sys.modules["config"] = config

# ─── 日志配置 ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("daily-digest")


def _check_config() -> bool:
    """检查必要配置是否就绪，返回是否可以继续。"""
    ok = True
    if not config.ANTHROPIC_API_KEY:
        logger.error("❌ ANTHROPIC_API_KEY 未配置，请在 .env 文件中填写")
        ok = False
    if not config.GITHUB_TOKEN:
        logger.warning("⚠️  GITHUB_TOKEN 未配置，GitHub 抓取将受速率限制（每小时 60 次请求）")
    if not config.YOUTUBE_API_KEY:
        logger.warning("⚠️  YOUTUBE_API_KEY 未配置，YouTube 抓取将被跳过")
    return ok


def run(
    sources: list[str] | None = None,
    dry_run: bool = False,
    collect_only: bool = False,
    digest_date: date = None,
):
    """
    执行一次完整的日报生成流程。

    Args:
        sources:      指定信源列表，None 表示使用所有配置的信源
                      可选值: ["github", "youtube", "rss"]
        dry_run:      True 时只打印结果，不写入文件
        collect_only: True 时只采集并保存原始 JSON，不调用 AI 摘要
                      （供 Claudian skill 读取后自行摘要）
        digest_date:  日报日期，默认今天
    """
    if digest_date is None:
        digest_date = date.today()

    # collect-only 模式不需要 ANTHROPIC_API_KEY
    if not collect_only and not _check_config():
        sys.exit(1)

    sources = sources or ["github", "youtube", "rss"]
    mode_label = "仅采集" if collect_only else "完整生成"
    logger.info(f"🚀 开始日报任务 [{mode_label}] | 日期: {digest_date} | 信源: {sources}")

    # ─── Step 1: 数据采集 ───
    raw_items: list[dict] = []

    if "github" in sources:
        logger.info("📦 正在抓取 GitHub...")
        try:
            from collectors.github_collector import collect_github
            github_items = collect_github()
            raw_items.extend(github_items)
            logger.info(f"   GitHub: {len(github_items)} 个仓库")
        except Exception as e:
            logger.error(f"   GitHub 抓取失败: {e}")

    if "youtube" in sources and config.YOUTUBE_API_KEY:
        logger.info("📺 正在抓取 YouTube...")
        try:
            from collectors.youtube_collector import collect_youtube
            yt_items = collect_youtube()
            raw_items.extend(yt_items)
            logger.info(f"   YouTube: {len(yt_items)} 个视频")
        except Exception as e:
            logger.error(f"   YouTube 抓取失败: {e}")
    elif "youtube" in sources:
        logger.info("   YouTube: 跳过（未配置 API Key）")

    if "rss" in sources:
        logger.info("📰 正在抓取 RSS...")
        try:
            from collectors.rss_collector import collect_rss
            rss_items = collect_rss()
            raw_items.extend(rss_items)
            logger.info(f"   RSS: {len(rss_items)} 篇文章")
        except Exception as e:
            logger.error(f"   RSS 抓取失败: {e}")

    if not raw_items:
        logger.warning("⚠️  没有采集到任何内容，日报生成终止")
        return

    logger.info(f"✅ 采集完成，共 {len(raw_items)} 条原始内容")

    # ─── collect-only 模式：保存原始 JSON 供 Claudian 读取 ───
    if collect_only:
        import json
        inbox_dir = Path(__file__).parent / "inbox"
        inbox_dir.mkdir(exist_ok=True)
        # 金融日报用 YYYY-MM-DD-finance.json，科技日报用 YYYY-MM-DD.json
        profile_suffix = "-finance" if _pre_args.profile == "finance" else ""
        inbox_file = inbox_dir / f"{digest_date}{profile_suffix}.json"
        inbox_file.write_text(
            json.dumps(raw_items, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"原始数据已保存: {inbox_file}")
        print(f"\n[OK] 采集完成！共 {len(raw_items)} 条原始内容")
        print(f"     文件: _tools/daily-digest/inbox/{digest_date}{profile_suffix}.json")
        return

    # ─── Step 2: Claude 摘要 + 品味过滤 ───
    logger.info(f"🤖 Claude 正在分析 {len(raw_items)} 条内容...")
    from summarizer import summarize_items
    filtered_items = summarize_items(raw_items)
    logger.info(f"✅ 筛选完成，{len(filtered_items)} 条内容进入日报")

    if not filtered_items:
        logger.warning("⚠️  所有内容均低于相关性阈值，日报为空")
        return

    # ─── Step 3: 写入日报 ───
    if dry_run:
        logger.info("📄 [DRY RUN] 日报预览：")
        for item in filtered_items:
            print(f"\n  [{item['ai_score']}/10] [{item['source']}] {item['title']}")
            print(f"  {item['url']}")
            print(f"  摘要: {item['ai_summary']}")
    else:
        from digest_writer import write_digest
        output_path = write_digest(filtered_items, digest_date=digest_date)
        logger.info(f"📝 日报已写入 Obsidian: {output_path.relative_to(config.VAULT_ROOT)}")
        print(f"\n✅ 今日日报已生成！")
        print(f"   文件: {config.OUTPUT_FOLDER}/{digest_date}.md")
        print(f"   共 {len(filtered_items)} 条内容")
        print(f"\n💬 运行 'python feedback.py' 可以为今日内容打分，帮助 Claude 学习你的偏好。")


# ─────────────────────────────────────────────────
# 命令行入口
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Daily Digest - 每日内容精选（科技 / 金融）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                                    # 科技日报，正常运行
  python main.py --profile finance --collect-only   # 金融日报，仅采集
  python main.py --source github rss                # 只抓取 GitHub 和 RSS
  python main.py --dry-run                          # 只预览，不写入文件
  python main.py --dry-run --source rss             # 测试 RSS 抓取
        """,
    )
    parser.add_argument(
        "--profile",
        choices=["tech", "finance"],
        default="tech",
        help="日报类型：tech（科技，默认）或 finance（金融）",
    )
    parser.add_argument(
        "--source",
        nargs="+",
        choices=["github", "youtube", "rss"],
        default=None,
        metavar="SOURCE",
        help="指定抓取的信源（默认全部）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印结果，不写入 Obsidian 文件",
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="只采集原始数据并保存 JSON，不调用 AI（供 Claudian skill 读取）",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="指定日报日期 (YYYY-MM-DD)，默认今天",
    )
    args = parser.parse_args()

    digest_date = None
    if args.date:
        from datetime import datetime
        digest_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    run(
        sources=args.source,
        dry_run=args.dry_run,
        collect_only=args.collect_only,
        digest_date=digest_date,
    )
