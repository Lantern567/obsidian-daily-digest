---
type: tool-guide
tags:
  - daily-digest
  - setup
created: 2026-03-01
---

# 🗞️ Daily Digest · 每日技术精选 使用说明

> 一个定时抓取 GitHub / YouTube / RSS 内容，由 Claude AI 摘要筛选，并在 Obsidian 中生成每日日报的本地工具。支持**你给内容打分 → Claude 学习你的品味**的闭环反馈机制。

---

## 📁 文件结构

```
_tools/daily-digest/
├── .env.example          ← API 密钥模板（复制为 .env 后填入）
├── .env                  ← 实际密钥（不会同步，不要提交到 git）
├── config.py             ← 信源偏好、关键词、输出设置
├── requirements.txt      ← Python 依赖
│
├── collectors/
│   ├── github_collector.py   ← GitHub 热门项目抓取
│   ├── youtube_collector.py  ← YouTube 视频 + 字幕抓取
│   └── rss_collector.py      ← RSS/Atom 订阅抓取
│
├── summarizer.py         ← Claude 打分 + 摘要 + 品味学习
├── digest_writer.py      ← 生成 Obsidian Markdown 日报
├── feedback.py           ← 交互式打分，记录偏好
├── main.py               ← 主入口（手动运行）
├── scheduler.py          ← 定时自动运行
└── feedback.db           ← SQLite 反馈数据库（自动创建）
```

---

## 🚀 一次性安装步骤

### 第一步：配置 API 密钥

```bash
# 进入工具目录
cd _tools/daily-digest

# 复制密钥模板
copy .env.example .env
```

用文本编辑器打开 `.env`，填入三个密钥：

| 密钥 | 获取地址 | 是否必须 |
|------|---------|---------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/settings/keys) | **必须** |
| `GITHUB_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) → 勾选 `public_repo` | 推荐（否则速率受限） |
| `YOUTUBE_API_KEY` | [Google Cloud Console](https://console.cloud.google.com) → 启用 YouTube Data API v3 → 创建凭据 | 可选 |

### 第二步：安装 Python 依赖

```bash
pip install -r requirements.txt
```

> 需要 Python 3.10+

### 第三步：配置你的兴趣偏好

打开 `config.py`，根据注释修改：

- `GITHUB_TOPICS` → 你关注的 GitHub 话题标签
- `YOUTUBE_CHANNEL_IDS` → 你订阅的 YouTube 频道 ID
- `YOUTUBE_KEYWORDS` → 用于视频搜索的关键词
- `RSS_FEEDS` → 你想订阅的 RSS 源链接

---

## 💻 日常使用

### 手动运行（生成今日日报）

```bash
cd _tools/daily-digest
python main.py
```

日报将生成在 Obsidian vault 的 `Daily Digest/YYYY-MM-DD.md`。

### 测试单个信源

```bash
python main.py --dry-run --source rss        # 只测试 RSS，不写文件
python main.py --dry-run --source github     # 只测试 GitHub
python main.py --source github rss           # 只用 GitHub + RSS 生成日报
```

### 为日报打分（帮 Claude 学习你的品味）

```bash
python feedback.py                    # 交互式为今日日报打分
python feedback.py --date 2026-03-01  # 为指定日期打分
python feedback.py --stats            # 查看你的偏好统计
```

打分完成后，下次生成日报时 Claude 会参考你的历史高分内容来调整筛选偏好。

---

## ⏰ 设置每天自动运行

### 方式一：Python 调度器（持续运行）

```bash
python scheduler.py                   # 默认每天 08:00 运行
python scheduler.py --time 07:30      # 自定义时间
```

> 进程需保持运行（可用 tmux / screen）。

### 方式二：Windows 任务计划程序（推荐）

1. 打开「任务计划程序」→ 创建基本任务
2. 触发器：每天，选择你希望的时间
3. 操作：启动程序
   - 程序：`python`（或 Python 完整路径，如 `C:\Python312\python.exe`）
   - 参数：`main.py`
   - 起始位置：`D:\obsidian_projects\fluid_model\_tools\daily-digest`

---

## 🧠 品味学习机制说明

系统使用 **few-shot 学习**方式让 Claude 了解你的偏好：

```
你打高分的内容
      ↓
存入 feedback.db
      ↓
下次生成日报时，历史高分内容作为示例注入 Claude 的 System Prompt
      ↓
Claude 会模仿这些高分内容的特征来筛选和评价新内容
```

**建议**：前 1-2 周坚持打分，大约积累 20-30 条反馈后，Claude 的推荐质量会明显提升。

---

## 📊 日报示例

生成的日报文件在 `[[Daily Digest/2026-03-01.md]]`，格式如下：

```
# 🗞️ 每日精选 · 2026-03-01

## 🐙 GitHub 项目
### [anthropic/claude-sdk](https://github.com/...)
> 🔥 极度推荐  ·  ⭐ 2,341 Stars  ·  Python
> Claude 官方 Python SDK，新增 Agent 工具调用支持...
> **为什么推荐**: 与你过去高分的 AI 工具类内容高度匹配

## 📺 YouTube 视频
...

## 💬 今日评分
| # | 标题 | 来源 | AI评分 | 你的评分 | 备注 |
|---|------|------|--------|---------|------|
| 1 | claude-sdk | 🐙 GITHUB | 9/10 |  |  |
```

---

## ❓ 常见问题

**Q: GitHub 报 403 错误？**
A: 未认证时每小时只有 60 次请求，配置 `GITHUB_TOKEN` 后提升到 5000 次。

**Q: YouTube 视频没有字幕摘要？**
A: 部分视频没有字幕（特别是非英/中文视频），系统会回退使用视频描述文字摘要。

**Q: 日报内容不够相关？**
A: 修改 `config.py` 中的 `GITHUB_TOPICS` 和 `YOUTUBE_KEYWORDS`，使其更贴近你的兴趣；同时坚持打分，积累偏好数据。

**Q: 如何添加更多 RSS 源？**
A: 在 `config.py` 的 `RSS_FEEDS` 列表中添加 RSS 链接即可。推荐网站：
- 博客通常有 `/rss` 或 `/feed` 路径
- [rsshub.app](https://rsshub.app) 可以给没有 RSS 的网站生成订阅源
