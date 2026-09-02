# Quality Pipeline Demo

搭建一套可运行的最小 CI/CD 闭环：push 代码 → CI 自动触发 → 拉起 Docker 环境 → 跑接口自动化 → 生成 Allure 报告 → 失败发通知。

## 技术栈

- GitHub Actions (CI/CD 引擎)
- Docker + Compose (环境容器化)
- pytest (接口测试框架)
- Allure Report (测试报告)

## 快速开始

```bash
# 本地运行
docker-compose up -d --build

# 运行测试
pytest tests/ -v

# 查看服务健康状态
curl http://localhost:8000/health
```

## CI 流程

1. push 到 main/develop 分支自动触发
2. checkout → 安装 Python → 安装依赖 → 运行单测
3. Docker 拉起被测服务 → 健康检查 → 接口自动化测试
4. 生成 Allure 报告 → 失败发通知

## 目录结构

```
quality-pipeline-demo/
├── .github/workflows/
│   └── ci.yml          # CI 流水线配置
├── app/                # 被测服务
├── tests/              # 测试用例
├── Dockerfile          # 服务容器化
├── docker-compose.yml  # 环境编排
├── requirements.txt    # Python 依赖
└── README.md
```
