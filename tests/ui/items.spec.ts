// tests/ui/items.spec.ts
import { test, expect } from '@playwright/test';

test.describe('商品管理 UI 测试', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8000');
  });

  test('商品列表页面正常显示', async ({ page }) => {
    const response = await page.request.get('/items');
    expect(response.ok()).toBeTruthy();
    const items = await response.json();
    expect(Array.isArray(items)).toBeTruthy();
  });

  test('创建商品后列表更新', async ({ page }) => {
    const createResp = await page.request.post('/items', {
      data: { name: 'test_product_' + Date.now(), price: 99.9 },
    });
    expect(createResp.ok()).toBeTruthy();

    const listResp = await page.request.get('/items');
    const items = await listResp.json();
    const found = items.find((i: { name: string }) => i.name.includes('test_product_'));
    expect(found).toBeTruthy();
  });

  test('空名称创建应返回错误', async ({ page }) => {
    const resp = await page.request.post('/items', {
      data: { name: '', price: 10 },
    });
    expect(resp.status()).toBe(422);
  });

  test('负数价格应返回错误', async ({ page }) => {
    const resp = await page.request.post('/items', {
      data: { name: 'neg_price', price: -1 },
    });
    expect(resp.status()).toBe(422);
  });

  test('批量创建后列表数量正确', async ({ page }) => {
    const beforeResp = await page.request.get('/items');
    const beforeItems = await beforeResp.json();
    const beforeCount = beforeItems.length;

    for (let i = 0; i < 3; i++) {
      await page.request.post('/items', {
        data: { name: 'batch_' + i, price: 10 + i },
      });
    }

    const afterResp = await page.request.get('/items');
    const afterItems = await afterResp.json();
    expect(afterItems.length).toBe(beforeCount + 3);
  });
});
