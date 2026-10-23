# 项目一总复盘报告

> 质量流水线与 CI/CD 平台 · 四周完整复盘

---

## 一、四周成果总览

| 周次 | 主题 | 核心产出 | 技能提升 |
|------|------|----------|----------|
| Week 1 | 流水线骨架 | Docker + GitHub Actions + Allure 最小闭环 | CI/CD 基础 + Docker 容器化 |
| Week 2 | 分层 + 门禁 | 四层流水线 + 三条质量门禁 + 分支保护 | 质量工程思维 + 门禁设计 |
| Week 3 | 精准 + 度量 | 精准测试脚本 + 质量看板 + 14 个指标 | 精准测试原理 + 数据可视化 |
| Week 4 | UI + 收官 | UI 自动化接入 + 多浏览器 + 最终优化 | Playwright CI + 性能优化 |

---

## 二、Week 1：流水线骨架（Day 1-7）

### 核心产出

1. **GitHub 仓库初始化**：创建 `quality-pipeline-demo` 仓库，配置 `.gitignore`（Python + Node + JetBrains）
2. **FastAPI 被测服务**：商品 CRUD 接口 + SQLite 持久化 + Pydantic 参数校验
3. **Docker 容器化**：Dockerfile + docker-compose.yml + healthcheck 配置
4. **CI 流水线骨架**：`.github/workflows/ci.yml`，包含 lint → unit test → build → api test
5. **Allure 报告集成**：CI 中自动生成测试报告并上传 artifact
6. **项目文档**：README.md + TROUBLESHOOTING.md 初始版本

### 关键决策

- **选择 Docker 镜像方案**：与 docker-compose 体系一致，CI 环境开箱即用
- **GitHub Actions 而非 Jenkins**：零运维成本，与 GitHub 仓库原生集成
- **Allure 而非 pytest-html**：支持富文本报告 + 历史趋势 + 分类筛选

### 踩坑记录

- Windows 不支持 WSL2 → 改用 CI 环境运行 Docker，本地用 venv
- `if: always` 语法错误 → 必须写成 `if: always()`
- `docker-compose` 命令不存在 → Docker Compose v2 用 `docker compose`
- Docker build 失败 `/data` 不存在 → Dockerfile 加 `RUN mkdir -p /data`
- slim 镜像缺 curl → 手动安装用于 healthcheck

---

## 三、Week 2：分层 + 门禁（Day 8-14）

### 核心产出

1. **四层流水线架构**：
   - 提交级（ci.yml）：Push 触发，lint + unit test
   - 合并级（pr-pipeline.yml）：PR 触发，smoke test + 精准测试 + UI 冒烟
   - 每日级（daily-pipeline.yml）：cron 触发，全量回归 + 全量扫描
   - 发布级（release-pipeline.yml）：tag 触发，全量验证 + 人工审批
2. **三条质量门禁**：
   - 用例通过率门禁：`quality_gate.py --junit` 阈值 100%（PR）/ 95%（每日）
   - 代码扫描门禁：`quality_gate.py --bandit` 阻断 HIGH 级别漏洞
   - 覆盖率门禁：`--cov-fail-under=70`，未达标阻断合并
3. **GitHub 分支保护**：main/develop 分支必须通过 CI + PR review
4. **代码扫描体系**：flake8 + pylint + bandit，`continue-on-error` 灰度接入
5. **pytest marker 分级**：`@pytest.mark.smoke` / `@pytest.mark.regression`

### 关键决策

- **灰度接入策略**：新工具先用 `continue-on-error: true` 跑起来，看数据再收紧阈值
- **门禁分级设计**：严重问题阻断，一般问题只警告
- **四层不重复**：每层职责明确，冒烟只在 PR 跑，全量只在每日跑

### 踩坑记录

- flake8 W503/E501 告警过多 → 配置文件忽略风格规则
- pylint 评分 0.00 → disable 非必要规则 + 修代码格式
- pytest marker 未注册 → pytest.ini 显式注册 + `--strict-markers`
- 覆盖率 40% 不达标 → 扩展边界测试用例到 10 条，提升到 70%+
- 分支保护后无法直接 push → 改用 feature 分支 + PR 流程

---

## 四、Week 3：精准 + 度量（Day 15-21）

### 核心产出

1. **精准测试工具**（`scripts/precision_test.py`）：
   - 基于 git diff 分析变更文件
   - 正则匹配关联测试用例
   - 召回率 80%+，平均减少 50% 测试执行量
   - 支持 `--mode pr` / `--mode full` 两种运行模式
2. **精准测试评估工具**（`scripts/evaluate_precision.py`）：
   - 自动评估召回率和执行减少率
   - 生成评估报告
3. **质量度量看板**（`quality-dashboard/`）：
   - ECharts + 原生 HTML/CSS/JS
   - 14 个指标可视化（6 过程 + 4 结果 + 4 效率）
   - GitHub Pages 自动部署，在线可访问
4. **质量门禁增强**：
   - `quality_gate.py` 支持 `--skip` 参数和 `SKIP_QUALITY_GATE` 环境变量
   - 错误处理优化，避免 Python 栈追踪

### 关键决策

- **L1 精准测试（文件匹配）**：投入产出比最优，L2/L3 投入过大
- **ECharts 而非 Grafana**：零运维，静态部署，满足需求
- **GitHub Pages 部署看板**：免费托管，CI 自动更新数据

### 踩坑记录

- `re.match` 匹配子目录文件失败 → 改用 `.*(md|yml)$` 正则
- GitHub Pages 首次部署 "Get Pages site failed" → 先手动配置 Pages site
- `configure-pages` 步骤失败阻断部署 → 加 `continue-on-error: true`
- koa-connect 导致 ctx 泄漏 → 原生 Koa 重写

---

## 五、Week 4：UI + 收官（Day 22-28）

### 核心产出

1. **Playwright UI 自动化**：
   - UI 冒烟测试（`smoke.spec.ts`）：4 条核心链路测试
   - 功能测试（`items.spec.ts`）：5 条商品管理功能 + 边界测试
   - 移动端测试（`mobile.spec.ts`）：Pixel 5 模拟
   - 调试演示（`debug-trace.spec.ts`）：故意失败 + Trace Viewer
2. **多浏览器矩阵**：
   - Chromium + Firefox + WebKit 三浏览器并行
   - PR 级只跑 Chromium，每日级跑三浏览器
   - `fail-fast: false` 确保矩阵互不影响
3. **Trace Viewer 调试体系**：
   - `trace: 'on-first-retry'` 失败自动保留
   - `screenshot: 'only-on-failure'` + `video: 'retain-on-failure'`
   - CI 中 trace.zip 上传 artifact
4. **流水线最终优化**：
   - 五层缓存：pip + Docker + Playwright + Allure + npm
   - 超时调优：PR 10min，每日 15-20min
   - PR 流水线从 8min 优化到 5min（节省 37%）
5. **项目文档全面更新**：
   - README.md：架构图 + 技术栈 + 快速开始 + 四层流水线说明
   - PIPELINE_DESIGN.md：设计理由 + 分层原则 + 门禁矩阵
   - QUALITY_METRICS_DESIGN.md：14 指标定义 + 关系图
   - PIPELINE_OPTIMIZATION.md：优化前后对比数据
   - TRACE_VIEWER_GUIDE.md：调试指南
6. **项目复盘 + 简历准备**：本文档 + 简历亮点 + 面试话术

### 关键决策

- **Playwright 而非 Selenium**：原生多浏览器、自动等待、Trace 调试、CI 集成简单
- **分层浏览器策略**：PR 级 Chromium 保速度，每日级三浏览器保覆盖
- **Docker layer cache 回退**：buildx local cache 在 GitHub Actions 不兼容，回退到 `docker build`

### 踩坑记录

- `npm ci` 失败（无 package-lock.json）→ 改用 `npm install`
- `docker compose up -d` 启动 ui-test 导致构建失败 → 改为 `docker compose up -d api`
- `docker/build-push-action` local cache 不兼容 → 回退到 `docker build`
- GitHub Actions buildx 不支持 local cache backend → 删除 Docker layer cache

---

## 六、技能提升清单

### 硬技能

| 技能领域 | 入项水平 | 出项水平 | 关键证据 |
|----------|---------|---------|----------|
| CI/CD | 了解概念 | 独立设计四层流水线 | 4 个 workflow YAML |
| Docker | 不会用 | 容器化 + compose 编排 | Dockerfile + docker-compose.yml |
| Python 测试 | 写过简单脚本 | pytest + Allure + 覆盖率 | 10+ 测试用例 + marker 分级 |
| UI 自动化 | 没用过 | Playwright + 多浏览器 + Trace | 10+ E2E 用例 |
| 质量工程 | 只做功能测试 | 门禁设计 + 精准测试 + 度量 | quality_gate.py + precision_test.py |
| 数据可视化 | 没做过 | ECharts 看板 + GitHub Pages | 14 指标在线看板 |
| Git 工作流 | 会基本操作 | 分支保护 + PR + release | main/develop 分支策略 |

### 软技能

| 技能 | 提升点 |
|------|--------|
| 排障能力 | 形成五步排障法：看报错 → 定范围 → 搜索 → 逐一验证 → 记录 |
| 工程思维 | 灰度接入、分层设计、投入产出比评估 |
| 文档能力 | 设计文档 + 排障文档 + README + 复盘报告 |
| 项目管理 | 四周 7 个里程碑，每日任务拆解 + 验收 |

---

## 七、量化成果汇总

| 指标 | 数值 |
|------|------|
| 流水线条数 | 4 条（提交/合并/每日/发布） |
| 质量门禁数 | 3 条（通过率/扫描/覆盖率） |
| 测试用例数 | 10+ API + 10+ UI |
| 代码行数 | ~2000 行（含测试 + 脚本 + 配置） |
| 覆盖率 | 40% → 70%+ |
| PR 耗时 | 8min → 5min（-37%） |
| 精准测试召回率 | 80%+ |
| 测试执行减少 | 50% |
| 度量指标数 | 14 个 |
| 浏览器数 | 3（Chromium/Firefox/WebKit） |
| 缓存层 | 5 层（pip/Docker/Playwright/Allure/npm） |
| 踩坑数 | 16+ 个（全部记录在 TROUBLESHOOTING.md） |

---

## 八、项目不足与改进方向

### 当前不足

1. **精准测试 L1 限制**：文件匹配召回率上限 70-80%，需 L2（覆盖率映射）提升到 90%+
2. **无持久化测试报告**：Allure 报告在 artifact 中，14 天后过期，未接入 Allure Server
3. **无性能测试**：当前只有功能测试，缺少 TPS/响应时间/并发等性能指标
4. **UI 测试覆盖不足**：只有 10+ 条 UI 用例，未覆盖完整用户旅程
5. **无安全测试**：bandit 只做静态扫描，无动态安全测试（DAST）

### 改进方向

1. 精准测试升级到 L2（coverage map）或 L3（call graph）
2. 接入 Allure Server 持久化测试报告
3. 项目二引入 k6/JMeter 性能测试
4. 扩展 UI 测试到完整用户旅程
5. 接入 OWASP ZAP 动态安全扫描

---

## 九、一句话总结

> 四周时间，从零搭建了一套四层 CI/CD 质量流水线，包含三条质量门禁、精准测试、质量看板和 UI 自动化——从代码提交到 UI 验证全链路自动化，PR 等待时间优化 37%，覆盖率从 40% 提升到 70%+。这是一个可以直接放进简历的 L4 级项目。
