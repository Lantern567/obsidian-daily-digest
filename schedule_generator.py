#!/usr/bin/env python3
"""Daily Schedule Generator for Obsidian Vault
研一日程管理系统

Usage:
    # Generate today + tomorrow's notes (main usage)
    uv run --directory _tools/daily-digest python schedule_generator.py

    # Generate for a specific date
    uv run --directory _tools/daily-digest python schedule_generator.py --date 2026-03-05

    # Initialize courses.json from Excel (one-time, needs openpyxl)
    uv run --directory _tools/daily-digest --with openpyxl python schedule_generator.py --init

    # Habit analysis (for Claude Skill to read)
    uv run --directory _tools/daily-digest python schedule_generator.py --habit-report --days 14
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows console outputs GBK by default; force UTF-8 so emoji/CJK prints work
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent           # _tools/daily-digest/
VAULT_ROOT   = SCRIPT_DIR.parent.parent        # vault root
COURSES_JSON = VAULT_ROOT / "每日日程表" / "courses.json"
SCHEDULE_DIR = VAULT_ROOT / "每日日程表"
EXCEL_PATH   = VAULT_ROOT / "每日日程表" / "研一no2学期课程.xlsx"
HABIT_LOG    = VAULT_ROOT / "每日日程表" / "habit_log.json"   # 长期作息记忆

# ── Constants ──────────────────────────────────────────────────────────────
WEEKDAY_ZH = {
    0: "周一", 1: "周二", 2: "周三", 3: "周四",
    4: "周五", 5: "周六", 6: "周日",
}


# ── Time helpers ───────────────────────────────────────────────────────────
def time_to_minutes(t: str):
    """'09:00' → 540, returns None on failure."""
    try:
        h, m = t.strip().split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def minutes_to_time(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def duration_hours(time_start: str, time_end: str) -> float:
    s = time_to_minutes(time_start)
    e = time_to_minutes(time_end)
    if s is None or e is None:
        return 0.0
    return max(0.0, (e - s) / 60)


def is_evening(time_start: str) -> bool:
    mins = time_to_minutes(time_start)
    return mins is not None and mins >= 18 * 60


def is_morning(time_start: str) -> bool:
    mins = time_to_minutes(time_start)
    return mins is not None and mins <= 10 * 60


def calculate_load(courses: list) -> tuple:
    """Return (load_key, load_label) based on total class hours."""
    total = sum(duration_hours(c["time_start"], c["time_end"]) for c in courses)
    if total == 0:
        return "light", "轻松"
    elif total <= 4:
        return "light", "轻松"
    elif total <= 7:
        return "medium", "适中"
    else:
        return "heavy", "繁忙"


# ── Excel Init ─────────────────────────────────────────────────────────────
def init_from_excel():
    """Parse Excel course schedule and write courses.json."""
    try:
        import openpyxl
    except ImportError:
        print("ERROR: openpyxl not found.")
        print("Hint: uv run --directory _tools/daily-digest --with openpyxl python schedule_generator.py --init")
        sys.exit(1)

    from datetime import datetime as dt_cls

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    courses = []
    current_course = None

    for row in ws.iter_rows(values_only=True):
        if all(c is None for c in row):
            continue
        cols = list(row) + [None] * 6
        col0, col1, col2, col3, col4, col5 = cols[:6]

        # ── Format 1: col0 is a "2026-xx-xx" date string ──────────────────
        if isinstance(col0, str) and re.match(r"2026-\d{2}-\d{2}$", col0):
            date_str    = col0
            time_str    = col1
            course_name = col3
            room        = str(col4 or "").strip()
            teacher     = str(col5 or "").strip()

        # ── Format 2: col1 is a datetime object (secondary sub-tables) ────
        elif isinstance(col1, dt_cls):
            # col0 may be int (row#) or string (course name)
            if isinstance(col0, str) and len(col0) > 4:
                raw = col0.split("\uff08")[0].split("(")[0].strip()
                if raw not in ("课次", "日期", "时间", "周次"):
                    current_course = raw
            if current_course is None:
                continue
            date_str    = col1.strftime("%Y-%m-%d")
            time_str    = col2
            course_name = current_course
            room        = str(col4 or "").strip()
            teacher     = str(col5 or "").strip()

        # ── Section-title row: long string in col0, rest None ──────────────
        elif (
            isinstance(col0, str) and col1 is None
            and len(col0) > 8
            and col0 not in ("课次", "日期", "时间", "周次", "教室", "教师", "课程名称")
        ):
            current_course = col0.split("\uff08")[0].split("(")[0].strip()
            continue

        else:
            continue

        # Validate
        if not isinstance(time_str, str) or "-" not in time_str:
            continue
        if not course_name or course_name in ("课程名称", "课次", "日期", "时间", "周次"):
            continue

        parts = time_str.strip().split("-")
        if len(parts) != 2:
            continue

        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        courses.append({
            "date":       date_str,
            "weekday":    WEEKDAY_ZH[parsed.weekday()],
            "time_start": parts[0].strip(),
            "time_end":   parts[1].strip(),
            "course":     str(course_name).strip(),
            "room":       room or "待定",
            "teacher":    str(teacher).strip(),
        })

    # De-duplicate and sort
    seen, unique = set(), []
    for c in courses:
        key = (c["date"], c["time_start"], c["course"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    unique.sort(key=lambda x: (x["date"], x["time_start"]))

    COURSES_JSON.write_text(
        json.dumps(unique, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ Generated {len(unique)} course entries → 每日日程表/courses.json")


# ── Course loading ─────────────────────────────────────────────────────────
def load_courses() -> list:
    if not COURSES_JSON.exists():
        print(f"ERROR: courses.json not found. Run --init first.")
        sys.exit(1)
    return json.loads(COURSES_JSON.read_text(encoding="utf-8"))


def get_courses_for_date(courses: list, date_str: str) -> list:
    return sorted(
        [c for c in courses if c["date"] == date_str],
        key=lambda c: c["time_start"],
    )


# ── Note building ──────────────────────────────────────────────────────────
def build_course_block(course: dict) -> str:
    dur  = duration_hours(course["time_start"], course["time_end"])
    room = course.get("room") or "待定"
    teacher = course.get("teacher") or "待定"

    if is_evening(course["time_start"]):
        tip = "晚课，注意提前吃饭"
    elif is_morning(course["time_start"]):
        tip = "早课，记得准时出发"
    else:
        tip = "注意提前到教室占位"

    return (
        f"> [!class]+ 🏫 {course['course']} · {course['time_start']} – {course['time_end']}\n"
        f"> 📍 {room} &nbsp;·&nbsp; 👤 {teacher}\n"
        f"> ⏱ 共 {dur:.0f} 小时 &nbsp;·&nbsp; 💡 {tip}"
    )


def build_tomorrow_preview(courses_tomorrow: list, date_tomorrow: str, weekday_tomorrow: str) -> str:
    header = f"> [!abstract] 🌅 明日预告\n> **{date_tomorrow} · {weekday_tomorrow}**"
    if not courses_tomorrow:
        return header + "\n> - 🎉 明日无课，可安排自习或休息"
    lines = [header]
    for c in courses_tomorrow:
        room = c.get("room") or "待定"
        lines.append(
            f"> - 🏫 {c['course']} · {c['time_start']}–{c['time_end']} · {room} · {c['teacher']}"
        )
    return "\n".join(lines)


def build_timetable(
    courses_today: list,
    start_hour: int = 7,
    end_hour: int = 23,
    interval_min: int = 60,
) -> str:
    """
    Build a 30-min time-slot table for the day.
    Course slots are pre-filled; everything else is blank for the user to fill.
    Continuation slots show '→' so the user can see course boundaries at a glance.
    """
    # Build slot → course mapping (first course wins on overlap)
    slot_course: dict = {}
    for course in courses_today:
        s = time_to_minutes(course["time_start"])
        e = time_to_minutes(course["time_end"])
        if s is None or e is None:
            continue
        t = (s // interval_min) * interval_min        # snap to interval
        while t < e:
            key = minutes_to_time(t)
            if key not in slot_course:
                slot_course[key] = course
            t += interval_min

    slot_label = f"{interval_min} 分钟" if interval_min != 60 else "1 小时"
    lines = [
        f"> {slot_label}一格，课程已预填。填入事项，用 ✅ / ❌ / ~ 标记完成情况。",
        "",
        "| 时段 | 事项 | ✓ | 备注 |",
        "|:----:|------|:--:|------|",
    ]

    t = start_hour * 60
    prev_course = None

    while t < end_hour * 60:
        key    = minutes_to_time(t)
        course = slot_course.get(key)

        if course is not None:
            if course is not prev_course:
                # First slot of this course block
                room = course.get("room") or ""
                name = f"🏫 {course['course']} · {room}" if room else f"🏫 {course['course']}"
            else:
                name = "→"
            lines.append(f"| {key} | {name} | | |")
        else:
            lines.append(f"| {key} | | | |")

        prev_course = course
        t += interval_min

    return "\n".join(lines)


def build_note(date_str: str, courses_today: list, courses_tomorrow: list) -> str:
    dt         = datetime.strptime(date_str, "%Y-%m-%d")
    weekday    = WEEKDAY_ZH[dt.weekday()]
    dt_tmr     = dt + timedelta(days=1)
    date_tmr   = dt_tmr.strftime("%Y-%m-%d")
    weekday_tmr= WEEKDAY_ZH[dt_tmr.weekday()]

    load_key, load_label = calculate_load(courses_today)
    n       = len(courses_today)
    total_h = sum(duration_hours(c["time_start"], c["time_end"]) for c in courses_today)

    if n == 0:
        summary = "🎉 今日无课 · ⚡ 负荷：轻松"
    elif all(is_evening(c["time_start"]) for c in courses_today):
        summary = f"📚 课程：{n} 节晚课 · 🕙 占用 {total_h:.0f}h · ⚡ 负荷：{load_label}"
    else:
        summary = f"📚 课程：{n} 节课 · 🕙 占用 {total_h:.0f}h · ⚡ 负荷：{load_label}"

    # Time-line section
    if courses_today:
        course_blocks = "\n\n".join(build_course_block(c) for c in courses_today)
        timeline = f"## ⏰ 今日时间线\n\n{course_blocks}"
    else:
        timeline = "## ⏰ 今日时间线\n\n> [!note] 今日无课\n> 自由安排，建议推进论文 / 项目进度"

    tomorrow_preview = build_tomorrow_preview(courses_tomorrow, date_tmr, weekday_tmr)
    timetable        = build_timetable(courses_today)

    return f"""\
---
date: {date_str}
type: daily-schedule
tags:
  - daily-schedule
week_load: {load_key}
---

# 📅 {date_str} · {weekday}

> [!summary] 今日概览
> {summary}

---

{timeline}

---

## 🗓️ 今日时间表

{timetable}

---

## ✏️ 今日计划

> [!todo] 自定义事项（随时在此添加）
> - [ ]
> - [ ]
> - [ ]

---

## 📊 今日作息记录

> [!note] 填写时间帮助 Claudian 分析你的习惯
>
> | 项目 | 时间 | 备注 |
> |------|------|------|
> | 🌅 起床 | | |
> | 🍽 早饭 | | |
> | 📖 开始学习 | | |
> | 🏃 锻炼 | | |
> | 🌙 睡觉 | | |

---

## 💡 Claudian 建议

<!-- 由 Claude Skill 填写，每次运行自动更新 -->

> [!tip] ⏳ 时间管理
> （Claude 根据今日课程安排生成）

> [!warning] 📅 学业提醒
> （Claude 根据近期课程节点生成）

{tomorrow_preview}

---

## 📝 今日回顾

> 睡前填写，记录今天的收获、遇到的问题、明天的重点

<!-- 在此自由书写 -->
"""


# ── Section-aware merge ────────────────────────────────────────────────────
# Note block order: [frontmatter] [时间线] [时间表] [计划] [作息] [Claudian建议+明日] [回顾]
# ALWAYS refresh:   frontmatter, 今日时间线
# ALWAYS preserve:  今日时间表 (user edits throughout the day), 今日作息记录
# Preserve if non-placeholder: 今日计划, 今日回顾, 💡 Claudian 建议

_PLACEHOLDER_CLAUDIAN = "（Claude 根据今日课程安排生成）"
_PLACEHOLDER_PLAN     = "> - [ ] \n> - [ ] \n> - [ ] "
_PLACEHOLDER_REVIEW   = "<!-- 在此自由书写 -->"


def _extract_section(heading: str, text: str):
    """Extract content from heading to next '\\n---\\n' or end-of-string."""
    pattern = rf"({re.escape(heading)}\n.*?)(?=\n---\n|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1) if m else None


def _plan_is_placeholder(plan_section: str) -> bool:
    """
    True if the plan section still contains only the 3 default empty checkboxes.
    Used to decide whether to inject carry-forward items.
    """
    items = re.findall(r"^> - \[.\](.*)", plan_section, re.MULTILINE)
    return len(items) == 3 and all(not item.strip() for item in items)


def parse_incomplete_tasks(note_content: str) -> list:
    """
    Extract user-written tasks from a note's timetable that were NOT marked ✅.
    Skips: empty rows, continuation arrows (→), and course slots (🏫).
    Returns a list of task description strings.

    Parses by splitting on '|' to handle both empty and non-empty ✓ cells robustly.
    """
    section = _extract_section("## 🗓️ 今日时间表", note_content)
    if not section:
        return []

    incomplete = []
    for line in section.split("\n"):
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue

        # Split into cells, strip whitespace, ignore first/last empty segments
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue

        time_cell, task, status = cells[0], cells[1], cells[2]

        # Must be a time row (HH:MM)
        if not re.match(r"^\d{2}:\d{2}$", time_cell):
            continue
        # Skip empty tasks, continuation markers, and course blocks
        if not task or task in ("→", "↕") or task.startswith("🏫"):
            continue
        # Skip items marked done
        if "✅" in status:
            continue

        incomplete.append(task)

    return incomplete


def inject_carry_forward(date_str: str, note_content: str) -> str:
    """
    Look at yesterday's timetable for incomplete tasks.
    If today's 今日计划 is still at placeholder state, append those tasks there.
    Idempotent: if plan is already edited/populated, does nothing.
    """
    plan_sec = _extract_section("## ✏️ 今日计划", note_content)
    if not plan_sec or not _plan_is_placeholder(plan_sec):
        return note_content  # User has already added content → don't touch

    dt_prev   = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
    prev_path = SCHEDULE_DIR / f"{dt_prev.strftime('%Y-%m-%d')}.md"
    if not prev_path.exists():
        return note_content

    incomplete = parse_incomplete_tasks(prev_path.read_text(encoding="utf-8"))
    if not incomplete:
        return note_content

    date_label = dt_prev.strftime("%m/%d")
    cf_lines   = "\n".join(f"> - [ ] {task}" for task in incomplete)
    carry_block = f">\n> **📋 昨日未完成（{date_label}）：**\n{cf_lines}"

    # Append carry-forward block after the 3 placeholder checkboxes
    new_plan_sec = re.sub(
        r"((?:> - \[ \]\n){2}> - \[ \])",
        rf"\1\n{carry_block}",
        plan_sec,
        count=1,
    )

    if new_plan_sec == plan_sec:
        return note_content  # regex didn't match, leave as-is

    print(f"  📋 继承昨日未完成事项 {len(incomplete)} 条")
    return note_content.replace(plan_sec, new_plan_sec, 1)


def merge_notes(existing: str, new_note: str) -> str:
    """
    Merge new_note with existing:
    - Always refresh:  frontmatter, 今日时间线, 明日预告 block
    - Preserve if non-empty / non-placeholder: 今日计划, 今日作息记录, 今日回顾
    - Preserve Claudian 建议 if it's been written (not placeholder)
    """
    if not existing.strip():
        return new_note

    result = new_note

    sections_to_preserve = [
        ("## 🗓️ 今日时间表",    None),   # always preserve (user edits throughout day)
        ("## ✏️ 今日计划",      _PLACEHOLDER_PLAN),
        ("## 📊 今日作息记录",   None),   # always preserve habit table
        ("## 📝 今日回顾",       _PLACEHOLDER_REVIEW),
    ]

    for heading, placeholder in sections_to_preserve:
        old_sec = _extract_section(heading, existing)
        new_sec = _extract_section(heading, new_note)
        if old_sec and new_sec:
            # Preserve if: no placeholder given, OR placeholder is absent from old
            if placeholder is None or placeholder not in old_sec:
                result = result.replace(new_sec, old_sec, 1)

    # Preserve Claudian 建议 only if Claude has already filled it in
    old_cl = _extract_section("## 💡 Claudian 建议", existing)
    new_cl = _extract_section("## 💡 Claudian 建议", new_note)
    if old_cl and new_cl and _PLACEHOLDER_CLAUDIAN not in old_cl:
        result = result.replace(new_cl, old_cl, 1)

    return result


# ── Generation ─────────────────────────────────────────────────────────────
def generate_for_date(date_str: str, courses: list) -> list:
    """Generate (or update) the schedule note for date_str."""
    dt_tmr     = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    date_tmr   = dt_tmr.strftime("%Y-%m-%d")

    courses_today = get_courses_for_date(courses, date_str)
    courses_tmr   = get_courses_for_date(courses, date_tmr)

    note_path = SCHEDULE_DIR / f"{date_str}.md"
    existing  = note_path.read_text(encoding="utf-8") if note_path.exists() else ""

    new_note   = build_note(date_str, courses_today, courses_tmr)
    final_note = merge_notes(existing, new_note)

    # Carry forward yesterday's incomplete tasks → today's 今日计划
    final_note = inject_carry_forward(date_str, final_note)

    note_path.write_text(final_note, encoding="utf-8")

    n = len(courses_today)
    label = " / ".join(c["course"][:10] for c in courses_today) if n else "无课"
    print(f"✅ {date_str}  {n} 节课  {label}")
    return courses_today


# ── Habit sync & long-term memory ─────────────────────────────────────────
def sync_habits_to_log() -> dict:
    """
    Scan ALL schedule notes in SCHEDULE_DIR, extract habit data,
    and persist to habit_log.json (long-term memory that survives note deletion).
    Returns the updated log dict {date_str: {field: value}}.
    """
    log: dict = {}
    if HABIT_LOG.exists():
        try:
            log = json.loads(HABIT_LOG.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            log = {}

    _HABIT_RE = re.compile(
        r"\| 🌅 起床 \| *(.*?) *\|.*?\n"
        r".*?\| 🍽 早饭 \| *(.*?) *\|.*?\n"
        r".*?\| 📖 开始学习 \| *(.*?) *\|.*?\n"
        r".*?\| 🏃 锻炼 \| *(.*?) *\|.*?\n"
        r".*?\| 🌙 睡觉 \| *(.*?) *\|",
        re.DOTALL,
    )

    updated = 0
    for note_path in sorted(SCHEDULE_DIR.glob("????-??-??.md")):
        date_str = note_path.stem
        content  = note_path.read_text(encoding="utf-8")
        m = _HABIT_RE.search(content)
        if not m:
            continue

        entry = {
            "weekday":   WEEKDAY_ZH[datetime.strptime(date_str, "%Y-%m-%d").weekday()],
            "wake":      m.group(1).strip(),
            "breakfast": m.group(2).strip(),
            "study":     m.group(3).strip(),
            "exercise":  m.group(4).strip(),
            "sleep":     m.group(5).strip(),
        }
        # Only persist if at least one time field is filled
        if entry["wake"] or entry["sleep"] or entry["study"]:
            if log.get(date_str) != entry:
                log[date_str] = entry
                updated += 1

    HABIT_LOG.write_text(
        json.dumps(log, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    total = len(log)
    if updated:
        print(f"📝 habit_log.json 已同步 +{updated} 条新记录（历史共 {total} 天）")
    else:
        print(f"📝 habit_log.json 已是最新（历史共 {total} 天有记录）")
    return log


# ── Habit report ───────────────────────────────────────────────────────────
def habit_report(days: int = 14):
    # Always sync notes → JSON first so we get the latest data
    log = sync_habits_to_log()

    today   = datetime.now()
    records = []

    for i in range(days, 0, -1):
        dt       = today - timedelta(days=i)
        date_str = dt.strftime("%Y-%m-%d")
        if date_str not in log:
            continue
        entry = log[date_str]
        if entry.get("wake") or entry.get("sleep"):
            records.append({"date": date_str, **entry})

    if not records:
        # Also show how many historical days we have even if recent has none
        print(f"📊 近 {days} 天暂无作息记录（请在日程笔记「作息记录」表格中填写时间）")
        if log:
            oldest = min(log.keys())
            print(f"   历史记录最早至 {oldest}，共 {len(log)} 天")
        return

    print(f"📊 近 {days} 天作息统计（{len(records)} 天有记录 · 历史总计 {len(log)} 天）\n")

    wake_mins  = [m for r in records if (m := time_to_minutes(r["wake"]))  is not None]
    sleep_mins = [m for r in records if (m := time_to_minutes(r["sleep"])) is not None]

    if wake_mins:
        avg = int(sum(wake_mins) / len(wake_mins))
        print(f"  🌅 平均起床：{minutes_to_time(avg)}"
              f"  (最早 {minutes_to_time(min(wake_mins))}，最晚 {minutes_to_time(max(wake_mins))})")

    if sleep_mins:
        adj     = [m + 1440 if m < 360 else m for m in sleep_mins]
        avg_adj = int(sum(adj) / len(adj)) % 1440
        print(f"  🌙 平均入睡：{minutes_to_time(avg_adj)}"
              f"  (最早 {minutes_to_time(min(sleep_mins))}，最晚 {minutes_to_time(max(sleep_mins))})")

    # Sleep duration check
    short_sleep = []
    for r in records:
        w = time_to_minutes(r["wake"])
        s = time_to_minutes(r["sleep"])
        if w is None or s is None:
            continue
        s_adj    = s + 1440 if s < 360 else s
        duration = (w + 1440 - s_adj) % 1440
        if duration < 7 * 60:
            short_sleep.append(r["date"])

    if short_sleep:
        print(f"\n  ⚠️  共 {len(short_sleep)} 天睡眠不足 7h：{', '.join(short_sleep[-3:])}")
    else:
        print("\n  ✅ 近期睡眠时长充足（≥7h）")

    exercise_days = [r for r in records if r.get("exercise")]
    print(f"  🏃 锻炼：{len(exercise_days)} / {len(records)} 天")

    print("\n  📋 最近 7 天明细：")
    for r in records[-7:]:
        print(f"    {r['date']} {r['weekday']}  起床 {r['wake'] or '-'}  睡觉 {r['sleep'] or '-'}")


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Daily Schedule Generator – 研一日程管理"
    )
    parser.add_argument(
        "--init", action="store_true",
        help="Parse Excel and generate courses.json (needs openpyxl via --with)"
    )
    parser.add_argument(
        "--date", type=str, metavar="YYYY-MM-DD",
        help="Generate note for a specific date instead of today+tomorrow"
    )
    parser.add_argument(
        "--habit-report", action="store_true",
        help="Print habit statistics (reads from habit_log.json, syncs first)"
    )
    parser.add_argument(
        "--sync-habits", action="store_true",
        help="Sync all note habit data → habit_log.json (long-term memory)"
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Days to look back for habit report (default: 30)"
    )
    args = parser.parse_args()

    if args.init:
        init_from_excel()
        return

    if args.sync_habits:
        sync_habits_to_log()
        return

    if args.habit_report:
        habit_report(args.days)
        return

    courses = load_courses()

    if args.date:
        generate_for_date(args.date, courses)
    else:
        today = datetime.now()
        for delta in (0, 1):
            d = (today + timedelta(days=delta)).strftime("%Y-%m-%d")
            generate_for_date(d, courses)


if __name__ == "__main__":
    main()
