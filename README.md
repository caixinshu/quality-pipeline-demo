# Quality Pipeline Demo

一个用于学习 CI/CD + 接口自动化测试的最小示例项目。通过 GitHub Actions 自动触发流水线，拉起 Docker 环境，运行单元测试和接口测试，生成 Allure 报告并在失败时发送通知。

> 本项目是「接口自动化进阶」第 1 周的练手项目，目标是跑通 **提交 → CI → Docker → 测试 → Allure 报告 → 通知** 的完整闭环。

---

## 架构图

```
代码提交 (push to develop)
        │
        ▼
┌─────────────────────┐
│   GitHub Actions    │
│      CI 流水线       │
├────────┬────────────┤
│unit-test│  api-test  │  ← 两个 job 并行执行
│ (单测)  │ (接口测试)  │
│        │   Docker   │
│        │  + Allure  │
└────────┴─────┬──────┘
               │
               ▼
       Allure Report Artifact
       （可下载的 HTML 报告）
               │
               ▼
        失败时 GitHub 通知
```

---

## 技术栈

| 技术 | 用途 |
|------|------|
| FastAPI | 被测后端服务 |
| SQLite | 数据存储 |
| Docker + Compose | 环境容器化 |
| pytest | 测试框架 |
| Allure Report | 测试报告 |
| GitHub Actions | CI/CD 引擎 |

---

## 目录结构

```
quality-pipeline-demo/
├── .github/
│   └── workflows/
│       └── ci.yml              # CI 流水线配置
├── app/
│   └── main.py                 # 被测服务（FastAPI）
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest 配置
│   ├── test_unit.py            # 单元测试
│   └── test_api.py             # 接口自动化测试（带 Allure 标注）
├── Dockerfile                  # 服务容器化配置
├── docker-compose.yml          # 环境编排
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明（本文件）
└── TROUBLESHOOTING.md          # 踩坑记录
```

---

## 本地运行

### 方式一：Python 直接运行（无需 Docker）

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（首次运行）
python -c "import sqlite3, os; os.makedirs('data', exist_ok=True); c=sqlite3.connect('data/demo.db'); c.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL)'); c.commit(); c.close()"

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 另开终端，运行测试
pytest tests/test_api.py -v
```

### 方式二：Docker 运行

> 需要先安装 Docker Desktop

```bash
# 构建镜像并启动服务
docker compose up -d --build

# 运行接口测试
pytest tests/test_api.py -v

# 停止服务
docker compose down
```

### 验证服务

```bash
curl http://localhost:8000/health
# 返回 {"status":"ok"} 表示正常
```

---

## CI 流水线说明

### 触发条件

- push 到 `main` 或 `develop` 分支
- 向 `main` 或 `develop` 发起 Pull Request

### Job 概览

| Job | 内容 | 耗时 |
|-----|------|------|
| unit-test | 单元测试 + 覆盖率报告 | ~30s |
| api-test | Docker 拉起服务 + 接口测试 + Allure 报告 | ~2min |

两个 job **并行执行**，互不依赖。

### 查看报告

1. 打开 GitHub 仓库 → Actions 标签
2. 点击任意一次 CI 执行记录
3. 页面底部 Artifacts 区域下载 `allure-report`
4. 解压后用本地 HTTP 服务器打开：
   ```bash
   cd allure-report
   python -m http.server 8080
   # 浏览器访问 http://localhost:8080
   ```

> ⚠️ 直接双击 `index.html` 可能显示空白（Allure 报告依赖 AJAX 加载，file:// 协议不支持）。

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/items` | 获取商品列表 |
| POST | `/items` | 创建商品 |

### 创建商品请求体

```json
{
  "name": "商品名称",
  "price": 19.9
}
```

---

## 测试用例

### 单元测试（test_unit.py）

- 健康检查返回 ok
- 创建商品成功
- 查询列表包含新创建的商品

### 接口测试（test_api.py）

| 用例 | 严重级别 | 说明 |
|------|----------|------|
| 健康检查 | BLOCKER | 验证服务可访问 |
| 创建与查询 | CRITICAL | 创建后查询，验证数据一致性 |
| 异常输入校验 | NORMAL | 缺少字段返回 422 |
| 边界值测试 | NORMAL | 负数价格返回 422 |

---

## 常见问题

详见 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## 学习路径

- **Week 1**：CI 基础 + Docker + 接口测试 + Allure 报告（本项目）
- **Week 2**：分层流水线 + 代码质量检查 + 分支保护
- **Week 3**：多环境部署 + 性能测试 + 安全扫描

---

## License

MIT
