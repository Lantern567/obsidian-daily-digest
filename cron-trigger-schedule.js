/**
 * Daily Schedule - Obsidian Cron 触发器
 * ========================================
 * 将此脚本内容粘贴到 Obsidian Cron 插件的 Job 设置中
 * (Settings → Cron → Add Job → 选择 "Run JS" 模式)
 *
 * 推荐 Cron 表达式:
 *   0 9 * * *     每天早上 09:00 自动生成今日 + 明日日程
 *
 * 触发后 Claudian 会:
 *   1. 生成今日 / 明日笔记框架（课程自动填入时间表）
 *   2. 读取近 14 天作息数据
 *   3. 填写时间管理建议、学业提醒区块
 */

(async () => {
  const SKILL_COMMAND = "/daily-schedule";
  const VIEW_TYPE     = "claudian-view";
  const DELAY_MS      = 1500;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // Step 1: 确保 Claudian view 已打开
  const existingLeaves = app.workspace.getLeavesOfType(VIEW_TYPE);
  if (existingLeaves.length === 0) {
    app.commands.executeCommandById("claudian:open-view");
    await sleep(DELAY_MS);
  }

  // Step 2: 获取 view
  const leaf = app.workspace.getLeavesOfType(VIEW_TYPE)[0];
  if (!leaf) {
    new Notice("❌ Daily Schedule: 无法打开 Claudian 视图", 5000);
    return;
  }

  const view       = leaf.view;
  const tabManager = view?.getTabManager?.();
  if (!tabManager) {
    new Notice("❌ Daily Schedule: TabManager 未就绪", 5000);
    return;
  }

  // Step 3: 确保有活跃 Tab
  let activeTab = tabManager.getActiveTab?.();
  if (!activeTab) {
    await tabManager.createTab?.();
    await sleep(500);
    activeTab = tabManager.getActiveTab?.();
  }

  if (!activeTab) {
    new Notice("❌ Daily Schedule: 无法获取活跃 Tab", 5000);
    return;
  }

  // Step 4: 等待 inputController 就绪
  let retries = 10;
  while (!activeTab.controllers?.inputController && retries > 0) {
    await sleep(300);
    retries--;
  }

  const inputController = activeTab.controllers?.inputController;
  if (!inputController) {
    new Notice("❌ Daily Schedule: InputController 未就绪，请稍后重试", 5000);
    return;
  }

  // Step 5: 避免打断正在进行的对话
  if (activeTab.state?.isStreaming) {
    new Notice("⏳ Daily Schedule: Claudian 正忙，跳过本次执行", 4000);
    return;
  }

  // Step 6: 发送 /daily-schedule 命令
  new Notice("📅 Daily Schedule 开始生成...", 3000);
  await inputController.sendMessage({ content: SKILL_COMMAND });
})();
