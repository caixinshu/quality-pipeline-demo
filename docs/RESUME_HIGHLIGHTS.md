# 简历亮点提炼

> 项目一：质量流水线与 CI/CD 平台 · 简历可用素材

---

## 简历项目卡片

**项目名称**：质量流水线与 CI/CD 平台

**项目角色**：测试开发工程师（独立完成）

**项目周期**：4 周

**技术栈**：Python, FastAPI, pytest, Playwright, Docker, GitHub Actions, Allure, ECharts, pylint/flake8/bandit, coverage.py

---

## 五条简历亮点

### 亮点 1：四层 CI/CD 流水线

> 搭建四层 CI/CD 流水线（提交级/合并级/每日级/发布级），PR 流水线从 8 分钟优化到 5 分钟，节省 37% 等待时间。通过分层设计实现"提交要快、合并要全、每日要深、发布要稳"的质量策略。

- **问题**：所有测试都跑一遍，PR 等待时间过长
- **方案**：分层设计 + 并行执行 + 五层缓存（pip/Docker/Playwright/Allure/npm）
- **效果**：PR 从 8min → 5min（-37%），每日级全量回归 20min 内完成

### 亮点 2：三条质量门禁

> 设计三条质量门禁（用例通过率/代码扫描/覆盖率），配合 GitHub 分支保护规则，实现不合规代码自动阻断合并。门禁分级设计——严重问题阻断，一般问题只警告，灰度上线后逐步收紧。

- **问题**：不合格代码可以直接合并到主干
- **方案**：quality_gate.py 脚本 + GitHub branch protection + 灰度接入策略
- **效果**：100% 通过率才能合并 PR，覆盖率门槛 70%，HIGH 级漏洞零容忍

### 亮点 3：精准测试工具

> 实现基于代码 diff 的精准测试工具（Python），召回率 80%+，平均减少 50% 的测试执行量。支持 PR 模式（只跑变更相关用例）和全量模式（评估精准度）。

- **问题**：每次 PR 都跑全部测试，浪费时间
- **方案**：git diff 分析变更文件 → 正则匹配关联测试 → 只执行相关用例
- **效果**：召回率 80%+，执行量减少 50%，PR 测试时间缩短一半

### 亮点 4：质量度量看板

> 搭建质量度量看板（ECharts + GitHub Pages），14 个指标可视化（6 过程 + 4 结果 + 4 效率），CI 自动更新数据，在线可访问。

- **问题**：质量数据散落在各 CI artifact 中，无法统一查看
- **方案**：ECharts 前端 + JSON 数据文件 + GitHub Pages 托管 + CI 自动更新
- **效果**：14 个指标一屏可见，在线访问地址：https://caixinshu.github.io/quality-pipeline-demo/

### 亮点 5：Playwright UI 自动化

> 接入 Playwright UI 自动化到流水线，支持 Chromium/Firefox/WebKit 三浏览器并行矩阵，失败时自动保留 Trace 供调试。PR 级只跑 Chromium 保速度，每日级跑三浏览器保覆盖。

- **问题**：CI 中只有 API 测试，缺少 UI 层验证
- **方案**：Playwright + 官方 Docker 镜像 + matrix 并行 + Trace Viewer
- **效果**：10+ UI 用例，三浏览器并行，失败可下载 trace.zip 回放调试

---

## 简历写法建议

### 推荐写法（量化 + 对比）

```
搭建四层 CI/CD 流水线（提交/合并/每日/发布），PR 流水线从 8min 优化到 5min（-37%），
包含三条质量门禁（通过率/扫描/覆盖率），实现不合规代码自动阻断合并。
```

### 不推荐写法（模糊 + 形容词）

```
负责 CI/CD 流水线搭建，优化了测试流程，提高了开发效率。
```

### 区别

- 量化：8min → 5min、-37%、三条门禁、14 个指标
- 对比：优化前后数据
- 具体：四层流水线、三条门禁、明确的技术方案

---

## 技术栈关键词（简历搜索优化）

```
CI/CD, GitHub Actions, Docker, pytest, Playwright, Allure,
质量门禁, 精准测试, 代码覆盖率, ECharts, GitHub Pages,
flake8, pylint, bandit, FastAPI, Python, 分支保护
```
