# Trace Viewer 调试指南

## 一、Trace Viewer 是什么

Trace Viewer 是 Playwright 内置的可视化调试工具，可以回放测试中的每一步操作，帮助你快速定位失败原因。

它包含以下信息：
- **时间线**：每一步操作的耗时和顺序
- **页面快照**：每一步操作时的 DOM 快照和截图
- **网络请求**：所有 API 请求和响应
- **控制台日志**：浏览器控制台输出
- **选择器信息**：元素定位详情

## 二、Trace 策略配置

在 `playwright.config.ts` 中配置 trace 策略：

```typescript
use: {
  // trace: 'off'               -> 不记录 trace（最快）
  // trace: 'on'                -> 永远记录（最慢但最全）
  // trace: 'retain-on-failure' -> 失败时保留
  // trace: 'on-first-retry'   -> 第一次重跑时记录（推荐）
  // trace: 'on-all-retries'   -> 每次重跑都记录
  trace: 'on-first-retry',
  // 截图策略
  screenshot: 'only-on-failure',
  // 视频策略
  video: 'retain-on-failure',
}
```

### 策略对比

| 策略 | 速度 | Trace 文件 | 适用场景 |
|------|------|-----------|---------|
| `off` | 最快 | 无 | 本地开发快速验证 |
| `on-first-retry` | 快 | 失败时有 | CI 推荐 |
| `retain-on-failure` | 中等 | 失败时有 | CI 备选 |
| `on` | 最慢 | 总是有 | 深度调试 |

## 三、调试流程

### 3.1 本地调试

```bash
# 运行测试（失败时自动生成 trace.zip）
npx playwright test tests/ui/items.spec.ts

# 查看 trace
npx playwright show-trace test-results/**/trace.zip
```

### 3.2 CI 中的调试流程

1. CI 中测试失败后，trace.zip 作为 artifact 自动上传
2. 从 GitHub Actions 下载 trace artifact
3. 解压后本地查看

```bash
# 下载 artifact 后
npx playwright show-trace trace.zip
```

### 3.3 故意制造失败并调试

项目中的 `tests/ui/debug-trace.spec.ts` 包含故意失败的测试用例，用于体验完整调试流程：

```bash
# 1. 编辑 debug-trace.spec.ts，将 test.fixme 改为 test 启用失败测试
# 2. 运行测试
npx playwright test debug-trace.spec.ts

# 3. 确认测试失败，trace.zip 已生成
# 4. 打开 Trace Viewer
npx playwright show-trace test-results/**/trace.zip

# 5. 在界面中：
#    - 左侧时间线找到标红的失败步骤
#    - 中间查看该步骤的页面快照和 DOM
#    - 右侧查看网络请求和控制台日志
# 6. 定位问题后，修复代码或测试
# 7. 将 test.fixme 加回，避免影响 CI
```

## 四、Trace Viewer 界面详解

打开 Trace Viewer 后，你会看到以下区域：

```
┌─────────────────────────────────────────────────────┐
│  顶部工具栏：测试名称、状态、浏览器                    │
├──────────┬──────────────────────┬───────────────────┤
│          │                      │                   │
│  时间线   │   页面快照/DOM       │   详细信息        │
│  (左侧)   │   (中间)             │   (右侧)          │
│          │                      │                   │
│  每一步   │   每步操作的          │   网络/控制台/     │
│  操作列表 │   页面截图和DOM      │   选择器/源码      │
│          │                      │                   │
├──────────┴──────────────────────┴───────────────────┤
│  底部：时间轴（可拖动定位到具体时刻）                   │
└─────────────────────────────────────────────────────┘
```

### 各区域功能

| 区域 | 功能 | 调试用途 |
|------|------|---------|
| 时间线 | 按顺序列出所有操作步骤 | 找到标红的失败步骤 |
| 页面快照 | 每一步操作后的 DOM 和截图 | 看失败时页面长什么样 |
| 网络 | 所有请求和响应 | 检查 API 是否正常 |
| 控制台 | 浏览器 console 日志 | 检查前端是否有报错 |
| 选择器 | 元素定位信息 | 调试选择器找不到的问题 |
| 源码 | 对应的测试代码行 | 跳转到失败代码行 |

## 五、CI 中的 Trace 自动上传

### PR 流水线（pr-pipeline.yml）

```yaml
- name: Upload trace files
  uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: playwright-traces
    path: test-results/**/trace.zip
```

### 每日流水线（daily-pipeline.yml）

```yaml
- name: Upload trace files
  uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: daily-ui-traces-${{ matrix.browser }}-${{ github.run_id }}
    path: test-results/**/trace.zip
```

### 下载流程

1. 进入 GitHub Actions 页面
2. 点击失败的 workflow run
3. 在 Artifacts 区域下载 trace 文件
4. 解压后用 `npx playwright show-trace trace.zip` 查看

## 六、常见问题

### Q: trace.zip 文件太大怎么办？

A: 调整 trace 策略为 `on-first-retry`，只在重跑时记录。成功时不会生成 trace。

### Q: CI 中找不到 trace.zip？

A: 确认 `if: failure()` 条件正确，且 `test-results/` 路径配置正确。

### Q: Trace Viewer 打开是空白？

A: 确认 Playwright 版本一致，trace.zip 文件没有损坏。尝试用相同版本的 Playwright 打开。

### Q: 如何在调试模式下运行测试？

A: 使用 `--debug` 标志：
```bash
npx playwright test --debug
```
这会打开 Playwright Inspector，可以步进执行每一步。
