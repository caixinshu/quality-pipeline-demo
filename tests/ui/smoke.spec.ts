import { test, expect } from '@playwright/test';

test.describe('UI 冒烟测试', () => {
  test('首页可以正常打开', async ({ page }) => {
    await page.goto('http://localhost:8000');
    await expect(page).toHaveTitle(/Demo API/);
  });

  test('健康检查页面显示正常', async ({ page }) => {
    await page.goto('http://localhost:8000/health');
    const body = await page.textContent('body');
    expect(body).toContain('ok');
  });

  test('商品列表可以加载', async ({ page }) => {
    await page.goto('http://localhost:8000/items');
    const body = await page.textContent('body');
    expect(body).toMatch(/\[.*\]/);
  });

  test('创建商品功能正常', async ({ page }) => {
    const response = await page.request.post('http://localhost:8000/items', {
      data: { name: 'ui_test_item', price: 29.9 },
    });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.message).toBe('created');
  });
});
