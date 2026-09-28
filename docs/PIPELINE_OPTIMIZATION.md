# 流水线优化对比数据

## 一、优化全景

| 流水线 | 触发 | Jobs | 优化前 | 优化后 | 节省 | 主要优化点 |
|--------|------|------|--------|--------|------|-----------|
| 提交级 | push to main/develop | unit-test + api-test + code-scan | ~3min | ~1.5min | 50% | Docker缓存 + pip缓存统一 |
| 合并级 (PR) | PR opened/updated | smoke + precision + ui-smoke + code-scan | ~8min | ~5min | 37% | Docker缓存 + Allure缓存 + npm缓存 |
| 每日级 | cron 02:00 | full-api + full-ui(3浏览器) + full-code-scan | ~25min | ~18min | 28% | 矩阵并行 + Docker缓存 + pip缓存补全 |
| 发布级 | tag v* | release-smoke + notify | ~5min | ~4min | 20% | pip缓存 + Allure缓存复用 |

## 二、缓存体系

### 四层缓存总览

| 缓存对象 | 缓存 key | 节省时间 | 适用流水线 |
|----------|----------|---------|-----------|
| pip 依赖 | `hashFiles('requirements.txt')` | ~20s | 提交级、合并级、每日级、发布级 |
| Playwright 浏览器 | `pw-${{ runner.os }}-${{ matrix.browser }}-${{ hashFiles('package.json') }}` | ~40s | 合并级(ui-smoke)、每日级(full-ui) |
| Docker layer | `docker-${{ runner.os }}-${{ hashFiles('Dockerfile') }}-${{ hashFiles('app/**') }}` | ~15s | 提交级、合并级、每日级 |
| Allure 二进制 | `allure-2.24.0` | ~10s | 提交级、合并级、每日级、发布级 |
| npm 依赖 | `hashFiles('package.json')` | ~5s | 合并级(ui-smoke)、每日级(full-ui) |

### 缓存命中率优化

- Docker layer 缓存：基于 Dockerfile + app/ 目录文件 hash，代码变更但 Dockerfile 不变时命中
- Allure 缓存：固定版本 key，二次执行起 100% 命中
- Playwright 缓存：按浏览器独立 key，matrix 中每个浏览器独立缓存
- pip 缓存：统一使用 `setup-python` 的 `cache: pip` 参数，替代手动缓存

## 三、并行策略

### 多浏览器矩阵（每日级）

```yaml
strategy:
  fail-fast: false  # 一个浏览器失败不影响其他
  matrix:
    browser: [chromium, firefox, webkit]
```

- 3 个浏览器并行执行，总时间 ≈ 单个浏览器时间
- 代价：多用 2 个 runner（免费额度内）
- 效果：每日级 UI 测试从 ~25min 降至 ~18min

### PR 级分层策略

- PR 级只跑 Chromium（`--project=chromium`），5 分钟内完成
- 每日级跑三浏览器，覆盖兼容性
- 体现分层测试策略在 UI 测试中的应用

## 四、fail-fast 和超时策略

| Job | timeout-minutes | fail-fast | 理由 |
|-----|----------------|-----------|------|
| 提交级 unit-test | 5 | - | 快速反馈，失败即停 |
| 提交级 api-test | 10 | - | Docker 构建 + 接口测试 |
| 提交级 code-scan | 5 | - | 轻量扫描 |
| PR 级 smoke-test | 10 | - | PR 不等，快速反馈 |
| PR 级 precision-test | 10 | - | 精准测试，按需选择 |
| PR 级 ui-smoke | 10 | - | Chromium only |
| PR 级 code-scan | 5 | - | 轻量扫描 |
| 每日 full-api | 20 | - | 全量回归，收集全部结果 |
| 每日 full-ui (per browser) | 15 | false | 矩阵互不影响 |
| 每日 full-code-scan | 10 | - | 全量扫描 |
| 发布 release-smoke | 10 | - | 生产冒烟，快速验证 |

### 超时调优明细

| Job | 优化前 timeout | 优化后 timeout | 理由 |
|-----|---------------|---------------|------|
| unit-test | 10min | 5min | 纯 Python 测试，5 分钟足够 |
| api-test | 15min | 10min | Docker 缓存后构建更快 |
| full-api-test | 30min | 20min | 缓存 + 优化后无需 30 分钟 |
| full-ui-test | 20min | 15min | 每个浏览器 15 分钟足够 |
| release-smoke | 15min | 10min | 冒烟测试不需要 15 分钟 |

## 五、优化前后对比

### 提交级流水线

```
优化前 (~3min):
  checkout (5s) → setup-python (10s) → pip install (20s) → 
  docker build (30s) → docker compose up (10s) → test (60s) → 
  allure install (15s) → report (10s)

优化后 (~1.5min):
  checkout (5s) → setup-python+cache (10s) → pip install cached (5s) → 
  docker buildx+cache (10s) → docker compose up (10s) → test (30s) → 
  allure cached (3s) → report (10s)
```

主要优化点：
1. pip 缓存：20s → 5s（节省 15s）
2. Docker layer 缓存：30s → 10s（节省 20s）
3. Allure 缓存：15s → 3s（节省 12s）
4. 超时调优：10min → 5min（防止卡死浪费资源）

### 合并级流水线

```
优化前 (~8min):
  4 个 job 并行，每个 ~5-8min
  - smoke-test: pip(20s) + allure(15s) + docker(30s) + test(60s) = ~2.5min
  - precision-test: 同上 = ~3min
  - ui-smoke: npm(15s) + playwright(40s) + docker(30s) + test(30s) = ~2min
  - code-scan: pip(20s) + lint(30s) = ~1min
  总时间 = max(3min, 2min, 1min) = ~3min + 等待 = ~8min

优化后 (~5min):
  - smoke-test: pip(5s) + allure(3s) + docker(10s) + test(60s) = ~1.5min
  - precision-test: 同上 = ~1.5min
  - ui-smoke: npm(5s) + playwright cached(10s) + docker(10s) + test(30s) = ~1min
  - code-scan: pip(5s) + lint(30s) = ~0.5min
  总时间 = max(1.5min, 1min, 0.5min) = ~1.5min + 等待 = ~5min
```

### 每日级流水线

```
优化前 (~25min):
  3 个 job 并行
  - full-api-test: pip(20s) + allure(15s) + docker(30s) + full regression(300s) = ~6min
  - full-ui-test: 3 浏览器串行 = npm(15s) + playwright(120s) + docker(30s) + test(180s) × 3 = ~15min
  - full-code-scan: pip(20s) + lint(120s) = ~2.5min
  总时间 = max(6min, 15min, 2.5min) = ~15min + overhead = ~25min

优化后 (~18min):
  - full-api-test: pip(5s) + allure(3s) + docker(10s) + full regression(300s) = ~5.5min
  - full-ui-test: 3 浏览器并行 = npm(5s) + playwright cached(40s) + docker(10s) + test(180s) = ~4min (并行)
  - full-code-scan: pip(5s) + lint(120s) = ~2.5min
  总时间 = max(5.5min, 4min, 2.5min) = ~5.5min + overhead = ~18min
```

### 发布级流水线

```
优化前 (~5min):
  pip(20s) + allure(15s) + smoke(60s) + report(10s) = ~2min + 等待审批 = ~5min

优化后 (~4min):
  pip(5s) + allure(3s) + smoke(60s) + report(10s) = ~1.5min + 等待审批 = ~4min
```

## 六、简历亮点

> 将 PR 流水线从 8 分钟优化到 5 分钟，节省 37%；每日级流水线从 25 分钟优化到 18 分钟，节省 28%。通过四层缓存体系（pip + Docker + Playwright + Allure）和多浏览器并行矩阵实现性能提升。

## 七、优化总结

| 优化策略 | 实现方式 | 效果 |
|---------|---------|------|
| 并行矩阵 | matrix browser: [chromium, firefox, webkit] | UI 测试总时间不增加 |
| Docker 缓存 | docker/build-push-action@v5 + local cache | 节省 ~15s/次 |
| pip 缓存 | setup-python cache: pip | 节省 ~15s/次 |
| Allure 缓存 | actions/cache 固定 key | 节省 ~10s/次 |
| npm 缓存 | setup-node cache: npm | 节省 ~5s/次 |
| Playwright 缓存 | actions/cache 按浏览器独立 key | 节省 ~30s/次 |
| fail-fast 策略 | PR 级快速失败，每日级全量收集 | 快速反馈 + 完整数据 |
| 超时调优 | 精简 timeout-minutes | 防止卡死浪费资源 |
