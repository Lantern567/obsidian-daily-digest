/**
 * Daily Digest - Obsidian Cron 触发器
 * =====================================
 * 将此脚本内容粘贴到 Obsidian Cron 插件的 Job 设置中
 * (Settings → Cron → Add Job → 选择 "Run JS" 模式)
 *
 * Cron 表达式示例:
 *   0 9 * * *   每天早上 9:00
 *   0 8 * * 1-5 工作日早上 8:00
 *   0 7 * * *   每天早上 7:00
 */

(async () => {
  const SKILL_COMMAND = "/daily-digest";
  const VIEW_TYPE = "claudian-view";
  const DELAY_MS = 1500; // 等待 view 初始化的时间

  // 工具函数：等待
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // Step 1: 确保 Claudian view 已打开
  const existingLeaves = app.workspace.getLeavesOfType(VIEW_TYPE);
  if (existingLeaves.length === 0) {
    // View 未打开，执行 open-view 命令
    app.commands.executeCommandById("claudian:open-view");
    await sleep(DELAY_MS);
  }

  // Step 2: 获取 Claudian view
  const leaf = app.workspace.getLeavesOfType(VIEW_TYPE)[0];
  if (!leaf) {
    new Notice("❌ Daily Digest: 无法打开 Claudian 视图", 5000);
    return;
  }

  const view = leaf.view;
  const tabManager = view?.getTabManager?.();
  if (!tabManager) {
    new Notice("❌ Daily Digest: TabManager 未就绪", 5000);
    return;
  }

  // Step 3: 确保有活跃 Tab，如果没有则创建
  let activeTab = tabManager.getActiveTab?.();
  if (!activeTab) {
    await tabManager.createTab?.();
    await sleep(500);
    activeTab = tabManager.getActiveTab?.();
  }

  if (!activeTab) {
    new Notice("❌ Daily Digest: 无法获取活跃 Tab", 5000);
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
    new Notice("❌ Daily Digest: InputController 未就绪，请稍后重试", 5000);
    return;
  }

  // Step 5: 检查是否正在流式输出中（避免打断进行中的对话）
  if (activeTab.state?.isStreaming) {
    new Notice("⏳ Daily Digest: Claudian 正忙，跳过本次执行", 4000);
    return;
  }

  // Step 6: 发送 /daily-digest 命令
  new Notice("🗞️ Daily Digest 开始生成...", 3000);
  await inputController.sendMessage({ content: SKILL_COMMAND });
})();
