// tests/ui/debug-trace.spec.ts
// Trace Viewer 调试演示 - 故意制造失败的测试用例
//
// 使用方式：
// 1. 去掉 test.fixme(...) 中的 fixme，改为 test(...) 来启用失败测试
// 2. 运行：npx playwright test debug-trace.spec.ts
// 3. 测试失败后会生成 trace.zip
// 4. 查看 trace：npx playwright show-trace test-results/**/trace.zip
// 5. 在 Trace Viewer 界面中：
//    - 左侧：测试步骤时间线（每一步耗时）
//    - 中间：每一步的页面截图和 DOM 快照
//    - 右侧：网络请求、控制台日志、选择器信息
// 6. 体验完毕后，重新加回 test.fixme(...) 避免影响 CI

import { test, expect } from '@playwright/test';

test.describe('Trace Viewer 调试演示', () => {
  // 此测试被标记为 fixme，不会在 CI 中运行
  // 移除 .fixme 即可启用失败测试来体验 Trace Viewer 调试流程
  test.fixme('故意失败的断言 - 用于演示 Trace Viewer', async ({ page }) => {
    await page.goto('http://localhost:8000');
    // 故意写一个会失败的断言
    expect(false).toBeTruthy();
  });

  test.fixme('故意超时的操作 - 用于演示 Trace Viewer', async ({ page }) => {
    await page.goto('http://localhost:8000');
    // 故意等待一个不存在的元素，会超时失败
    await page.waitForSelector('#nonexistent-element', { timeout: 3000 });
  });

  test.fixme('故意错误的响应码 - 用于演示 Trace Viewer', async ({ page }) => {
    const response = await page.request.get('/items');
    // 故意期望错误的响应码
    expect(response.status()).toBe(500);
  });
});
