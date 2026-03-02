"""
scheduler.py - 定时任务调度器
================================
让 Daily Digest 在每天指定时间自动运行。

使用方式:
  python scheduler.py              # 按配置时间每天运行，保持进程运行
  python scheduler.py --now        # 立即运行一次（用于测试）
  python scheduler.py --time 08:30 # 覆盖配置，指定运行时间

Windows 用户也可以用「任务计划程序」代替此脚本，
详见 _tools/daily-digest/README 中的说明。
"""

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

import schedule

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduler")

# 默认运行时间（每天早上 8:00）
DEFAULT_RUN_TIME = "08:00"


def job():
    """调度任务入口：运行一次日报生成。"""
    logger.info("⏰ 定时任务触发，开始生成今日日报...")
    try:
        from main import run
        run()
        logger.info("✅ 今日日报生成成功")
    except Exception as e:
        logger.error(f"❌ 日报生成失败: {e}", exc_info=True)


def start_scheduler(run_time: str = DEFAULT_RUN_TIME):
    """启动定时调度器，阻塞运行。"""
    schedule.every().day.at(run_time).do(job)
    logger.info(f"📅 Daily Digest 调度器已启动")
    logger.info(f"   每天 {run_time} 自动生成日报")
    logger.info(f"   按 Ctrl+C 停止")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Digest 定时调度器")
    parser.add_argument(
        "--time",
        default=DEFAULT_RUN_TIME,
        help=f"每天运行时间，格式 HH:MM（默认 {DEFAULT_RUN_TIME}）",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="立即运行一次（不启动调度循环）",
    )
    args = parser.parse_args()

    if args.now:
        logger.info("▶️  立即运行模式")
        job()
    else:
        try:
            start_scheduler(args.time)
        except KeyboardInterrupt:
            logger.info("👋 调度器已停止")
