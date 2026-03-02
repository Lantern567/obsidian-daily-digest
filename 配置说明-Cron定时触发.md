---
type: setup-guide
tags: [daily-digest, cron, automation]
created: 2026-03-01
---

# 配置定时自动触发 Daily Digest

## 完整流程图

```
每天 9:00
  Obsidian Cron 插件
       │
       ▼ 执行 JS 脚本
  打开 Claudian 视图
       │
       ▼ 发送 /daily-digest
  我（Claudian）开始工作
  ├── 运行 Python 采集脚本（GitHub/RSS/YouTube）
  ├── 读取原始数据
  ├── 直接做摘要筛选（我就是 AI，不需要额外 Key）
  └── 写入 Daily Digest/YYYY-MM-DD.md
```

**需要的 API Key：只有 GitHub Token（免费）**

---

## 第一步：安装 Obsidian Cron 插件

1. 打开 Obsidian → 设置 → 第三方插件 → 浏览
2. 搜索 **Cron**（作者：cdloh）
3. 安装并启用

---

## 第二步：创建 Cron Job

打开 设置 → Cron → **Add Job**，填写以下内容：

| 字段 | 填写内容 |
|------|---------|
| Job Name | `Daily Digest` |
| Cron Expression | `0 9 * * *`（每天早上9点） |
| Run Mode | **Run JS** |
| JS Code | 粘贴下方代码 |

**JS 代码（复制整段）：**

```javascript
(async () => {
  const SKILL_COMMAND = "/daily-digest";
  const VIEW_TYPE = "claudian-view";
  const DELAY_MS = 1500;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const existingLeaves = app.workspace.getLeavesOfType(VIEW_TYPE);
  if (existingLeaves.length === 0) {
    app.commands.executeCommandById("claudian:open-view");
    await sleep(DELAY_MS);
  }

  const leaf = app.workspace.getLeavesOfType(VIEW_TYPE)[0];
  if (!leaf) { new Notice("Daily Digest: 无法打开 Claudian 视图", 5000); return; }

  const view = leaf.view;
  const tabManager = view?.getTabManager?.();
  if (!tabManager) { new Notice("Daily Digest: TabManager 未就绪", 5000); return; }

  let activeTab = tabManager.getActiveTab?.();
  if (!activeTab) {
    await tabManager.createTab?.();
    await sleep(500);
    activeTab = tabManager.getActiveTab?.();
  }

  if (!activeTab) { new Notice("Daily Digest: 无法获取活跃 Tab", 5000); return; }

  let retries = 10;
  while (!activeTab.controllers?.inputController && retries > 0) {
    await sleep(300); retries--;
  }

  const inputController = activeTab.controllers?.inputController;
  if (!inputController) { new Notice("Daily Digest: InputController 未就绪", 5000); return; }

  if (activeTab.state?.isStreaming) { new Notice("Daily Digest: Claudian 正忙，跳过", 4000); return; }

  new Notice("Daily Digest 开始生成...", 3000);
  await inputController.sendMessage({ content: SKILL_COMMAND });
})();
```

---

## 第三步：配置 GitHub Token（可选但推荐）

1. 访问 https://github.com/settings/tokens
2. Generate new token (classic)
3. 只勾选 `public_repo`
4. 复制 Token，粘贴到 `_tools/daily-digest/.env` 文件：

```
GITHUB_TOKEN=ghp_你的token
```

---

## 常用 Cron 表达式

| 表达式 | 含义 |
|--------|------|
| `0 9 * * *` | 每天早上 9:00 |
| `0 8 * * 1-5` | 工作日早上 8:00 |
| `0 7 * * *` | 每天早上 7:00 |
| `0 9 * * 1` | 每周一早上 9:00 |

---

## 注意事项

- **Obsidian 需要保持运行**（可以最小化到系统托盘）
- 日报生成完成后会出现在 `Daily Digest/` 文件夹
- 如果当天已有日报，Claudian 会询问是否覆盖
