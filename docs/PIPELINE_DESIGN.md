# CI/CD 流水线设计文档

## 一、设计目标

1. **快速反馈**：提交级 2 分钟内出结果，PR 级 6 分钟内
2. **质量保障**：三条门禁自动阻断不合规代码
3. **全面覆盖**：每日级全量回归 + 多浏览器 UI 测试
4. **可观测**：质量看板可视化所有指标，CI 自动更新数据

---

## 二、四层流水线架构

### 架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        四层流水线架构                                 │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│  提交级       │  合并级 (PR)  │  每日级       │  发布级                 │
│  ci.yml      │  pr-         │  daily-      │  release-              │
│              │  pipeline    │  pipeline    │  pipeline              │
│              │  .yml        │  .yml        │  .yml                  │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│  push to     │  PR opened/  │  cron 02:00  │  tag v*                │
│  main/develop│  synchronize │  + 手动       │  + 手动                 │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│  unit-test   │  smoke-test  │  full-api    │  release-smoke         │
│  api-test    │  precision   │  full-ui     │  notify                │
│  code-scan   │  ui-smoke    │  full-scan   │                        │
│              │  code-scan   │              │                        │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│  < 2min      │  < 6min      │  < 20min     │  < 5min                │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│  快速反馈     │  质量底线     │  全面回归      │  发布验证               │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
```

### 提交级（Commit Pipeline）

- **配置文件**：`.github/workflows/ci.yml`
- **触发**：push 到 `main` 或 `develop` 分支
- **Jobs**：
  - `unit-test`：单元测试 + 覆盖率门禁（≥70%），timeout 5min
  - `api-test`：Docker 拉起服务 + 接口测试 + Allure 报告，timeout 10min
  - `code-scan`：flake8 + pylint + bandit，timeout 5min
- **缓存**：pip 缓存 + Allure 二进制缓存
- **设计理由**：开发者最频繁的操作，必须快。只跑单元测试和快速接口测试，不跑 UI

### 合并级（PR Pipeline）

- **配置文件**：`.github/workflows/pr-pipeline.yml`
- **触发**：向 `main` 或 `develop` 发起 PR（opened/synchronize/reopened）
- **Jobs**：
  - `smoke-test`：接口冒烟测试（`-m smoke`）+ 质量门禁
  - `precision-test`：基于代码 diff 的精准测试，自动筛选受影响用例
  - `ui-smoke-test`：Playwright Chromium UI 冒烟测试
  - `code-scan`：flake8 + bandit + 安全质量门禁
- **缓存**：pip + npm + Playwright 浏览器 + Allure
- **设计理由**：合并前最后一道防线，必须全面但不拖沓。UI 只跑 Chromium 保证速度

### 每日级（Daily Pipeline）

- **配置文件**：`.github/workflows/daily-pipeline.yml`
- **触发**：cron `0 18 * * *`（UTC 18:00 = 北京时间 02:00）+ 手动 `workflow_dispatch`
- **Jobs**：
  - `full-api-test`：全量接口回归 + 覆盖率报告 + Allure 报告，timeout 20min
  - `full-ui-test`：多浏览器并行矩阵（Chromium/Firefox/WebKit），timeout 15min per browser
  - `full-code-scan`：flake8 + pylint + bandit 全量扫描，timeout 10min
- **并行策略**：`fail-fast: false`，矩阵互不影响
- **缓存**：pip + npm + Playwright 浏览器（按浏览器独立 key）
- **设计理由**：夜间全量回归，发现深层问题和跨浏览器兼容性问题

### 发布级（Release Pipeline）

- **配置文件**：`.github/workflows/release-pipeline.yml`
- **触发**：推送 `v*` 标签 + 手动 `workflow_dispatch`
- **Jobs**：
  - `release-smoke`：生产环境冒烟测试 + 质量门禁 + Allure 报告，timeout 10min
  - `notify`：发布通知（成功/失败），依赖 release-smoke 结果
- **环境保护**：`environment: production`，需审批人确认
- **设计理由**：发布后快速验证可用性，失败自动告警

---

## 三、质量门禁体系

### 三条核心门禁

| 门禁 | 规则 | 阈值 | 阻断层级 | 实现方式 |
|------|------|------|----------|----------|
| 用例通过率 | P0 用例必须全部通过 | 100% | 合并级 + 发布级 | `quality_gate.py --junit` |
| 代码扫描 | 高危安全问题必须为 0 | 0 个 | 合并级 + 每日级 | `quality_gate.py --bandit` |
| 覆盖率 | 行覆盖率不低于阈值 | ≥70% | 提交级 + 每日级 | `--cov-fail-under=70` |

### 门禁执行矩阵

| 流水线 | 通过率门禁 | 安全扫描门禁 | 覆盖率门禁 |
|--------|-----------|-------------|-----------|
| 提交级 | - | - | unit-test |
| 合并级 | smoke-test | code-scan | - |
| 每日级 | full-api-test | full-code-scan | full-api-test |
| 发布级 | release-smoke | - | - |

### 门禁脚本

`scripts/quality_gate.py` 支持以下参数：
- `--junit <path>`：检查测试通过率
- `--bandit <path>`：检查安全扫描结果
- `--skip`：白名单跳过（配合 PR label 使用）
- `SKIP_QUALITY_GATE`：环境变量跳过（紧急情况）

---

## 四、分层策略核心原则

1. **频率与范围成反比**：触发越频繁的流水线跑得越少越快
   - 提交级：只跑单测 → 最快
   - PR 级：冒烟 + 精准 → 适中
   - 每日级：全量 + 多浏览器 → 最慢但最全

2. **渐进式保障**：从单测到冒烟到全量，覆盖范围逐步扩大
   - 每一层都是前一层的超集

3. **快速失败**：任何一层发现问题立即阻断，不浪费后续资源
   - PR 级 fail-fast，一个 job 失败立即取消其他

4. **灰度接入**：新工具先用 `continue-on-error: true` 接入，不阻断
   - 代码扫描初期不阻断，稳定后再启用

5. **冒烟集兜底**：不确定时跑冒烟，冒烟集覆盖核心链路
   - 冒烟用例数量控制在总用例的 20-30%

6. **精准测试辅助**：减少每日级和 PR 级的测试执行范围
   - 基于代码 diff 自动筛选受影响用例

---

## 五、用例分级策略

| Marker | 范围 | 运行层级 | 数量 |
|--------|------|----------|------|
| `@pytest.mark.smoke` | 核心链路 | 合并级 PR | 冒烟集 |
| `@pytest.mark.regression` | 全量回归 | 每日级 | 全部 |

### 划分标准
- **冒烟用例**：服务能否启动、核心 API 能否正常调用
- **回归用例**：边界值、异常输入、负数、字段缺失等

### 维护规则
- 新增 API 必须同时新增冒烟用例
- 冒烟用例数量控制在总用例的 20-30%
- 回归用例持续积累，不删除

---

## 六、缓存体系

### 五层缓存

| 缓存对象 | 缓存 key | 节省时间 | 适用流水线 |
|----------|---------|---------|-----------|
| pip 依赖 | `hashFiles('requirements.txt')` | ~20s | 全部 |
| Playwright 浏览器 | `pw-${{ runner.os }}-${{ matrix.browser }}` | ~40s | 合并级 + 每日级 |
| Allure 二进制 | `allure-2.24.0` 固定 key | ~10s | 全部 |
| npm 依赖 | `hashFiles('package.json')` | ~5s | 合并级 + 每日级 |
| Docker layer | 通过 `docker build` 内置缓存 | ~15s | 全部 |

### fail-fast 和超时策略

| Job | timeout-minutes | fail-fast | 理由 |
|-----|----------------|-----------|------|
| 提交级 unit-test | 5 | - | 快速反馈，失败即停 |
| 提交级 api-test | 10 | - | Docker 构建 + 接口测试 |
| 合并级 smoke-test | 10 | - | PR 不等，快速反馈 |
| 合并级 precision-test | 10 | - | 精准测试 |
| 合并级 ui-smoke | 10 | - | Chromium only |
| 每日 full-api | 20 | - | 全量回归 |
| 每日 full-ui | 15 | false | 矩阵互不影响 |
| 发布 release-smoke | 10 | - | 快速验证 |

---

## 七、CI/CD 最佳实践总结

1. **缓存优先**：pip cache + Allure cache 可节省 50%+ 执行时间
2. **并行优于串行**：无依赖的 job 并行跑
3. **超时保护**：每个 job 设 `timeout-minutes`，避免卡死
4. **`if: always()`**：报告上传和清理步骤必须执行（注意括号语法）
5. **`continue-on-error`**：新工具灰度接入，不阻断流水线
6. **分支保护**：main/develop 必须走 PR，不能直接 push
7. **环境隔离**：发布级用 `environment: production` + 审批人
8. **Artifacts 保留**：测试报告和 trace 文件保留，方便回溯
9. **`docker compose up -d api`**：只启动需要的服务，避免无关服务构建失败
10. **矩阵并行**：多浏览器测试用 matrix 并行，总时间不增加
