// tests/ui/mobile/mobile.spec.ts
// 移动端模拟测试 - 使用 Pixel 5 设备配置

import { test, expect } from '@playwright/test';

test.describe('移动端 UI 测试', () => {
  test('移动端首页可以正常打开', async ({ page }) => {
    await page.goto('http://localhost:8000');
    await expect(page).toHaveTitle(/Demo API/);
  });

  test('移动端商品列表可以加载', async ({ page }) => {
    await page.goto('http://localhost:8000/items');
    const body = await page.textContent('body');
    expect(body).toMatch(/\[.*\]/);
  });
});
