# 踩坑记录（TROUBLESHOOTING）

本文档记录项目一第 1 周搭建过程中遇到的所有问题、解决思路和最终方案。这些排障经验是面试时最好的素材。

---

## 一、环境问题

### 问题 1：Windows 电脑不支持 WSL2，无法安装 Docker Desktop

**现象**：
电脑没有 WSL2 功能，Docker Desktop 无法安装，本地无法运行 Docker 容器。

**分析思路**：
1. 先确认核心目标：本周的重点是 CI 流水线，不是本地 Docker
2. GitHub Actions 的 `ubuntu-latest` runner 自带 Docker，CI 环境不受影响
3. 本地只是无法预览 Docker 服务，但代码和配置文件照样能写
4. 本地验证可以改用 Python 虚拟环境直接运行 FastAPI 服务

**解决方案**：
- Dockerfile 和 docker-compose.yml **照常创建**（CI 需要）
- 本地测试用 Python venv + uvicorn 直接启动服务
- CI 中正常使用 docker compose 拉起环境

**总结**：工具受限时，先区分「核心目标」和「辅助手段」。Docker 是辅助手段，CI 流水线跑通才是核心目标。

---

## 二、CI 配置问题

### 问题 2：`if: always` 报语法错误

**现象**：
CI 启动失败，报错 `Unrecognized named-value: 'always'`。

**分析思路**：
1. 报错说 `always` 不是合法的 named-value
2. 回想 GitHub Actions 表达式语法，`always` 应该是一个函数
3. 函数调用需要括号：`always()`

**解决方案**：
```yaml
# 错误写法
if: always

# 正确写法
if: always()
```

**总结**：GitHub Actions 表达式中，`always()`、`failure()`、`success()`、`cancelled()` 都是函数，必须加括号。

---

### 问题 3：`docker-compose` 命令不存在

**现象**：
CI 中 `docker-compose down` 报 exit code 127（命令未找到）。

**分析思路**：
1. exit code 127 = command not found
2. GitHub Runner 上有 Docker，但命令可能是新版语法
3. 查 Docker 版本演进：v1 用 `docker-compose`（有横杠），v2 用 `docker compose`（无横杠）
4. 当前 ubuntu-latest runner 默认装的是 Docker Compose v2

**解决方案**：
```yaml
# 错误写法（v1）
docker-compose up -d
docker-compose down

# 正确写法（v2）
docker compose up -d
docker compose down
```

**总结**：Docker Compose v1 到 v2 是重大变更，命令从独立的 `docker-compose` 变成了 docker 的子命令 `docker compose`。用的时候注意版本。

---

## 三、Docker 问题

### 问题 4：Docker build 失败，`/data/demo.db` 目录不存在

**现象**：
Dockerfile 中初始化数据库的步骤报错，因为 `/data` 目录不存在。

**分析思路**：
1. 报错指向 `sqlite3.connect('/data/demo.db')` 失败
2. SQLite 创建数据库文件时，要求上级目录必须存在
3. `python:3.11-slim` 镜像里默认没有 `/data` 目录
4. 需要在初始化数据库之前先创建目录

**解决方案**：
在 Dockerfile 中加一行 `mkdir -p /data`：
```dockerfile
# 初始化数据库
RUN mkdir -p /data
RUN python -c "import sqlite3; c=sqlite3.connect('/data/demo.db'); ..."
```

**总结**：容器镜像里的目录结构和本地不一样，不要假设目录存在。用到的路径最好显式创建。

---

### 问题 5：docker compose healthcheck 失败

**现象**：
用 `docker compose up -d --wait` 启动服务后，healthcheck 一直不通过，服务起不来。

**分析思路**：
1. healthcheck 配置用的是 `curl -f http://localhost:8000/health`
2. `python:3.11-slim` 是精简版镜像，默认没有装 `curl`
3. healthcheck 里的命令执行失败，Docker 认为服务不健康

**解决方案**：
在 Dockerfile 中安装 curl：
```dockerfile
RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*
```

**总结**：slim 镜像体积小但缺工具，用到的命令要自己装。

---

## 四、测试脚本问题

### 问题 6：负数价格测试失败，期望 422 实际返回 200

**现象**：
`test_price_negative` 测试发送 `price: -1`，期望返回 422（参数校验失败），但实际返回了 200（创建成功）。

**分析思路**：
1. 先看后端代码：`price: float` — Pydantic 的 float 类型允许任何浮点数，包括负数
2. 前端/接口层面没有做「价格必须大于 0」的业务校验
3. 测试用例的期望是对的（业务上价格不应该为负），但后端没实现这个校验
4. 应该在后端的 Pydantic 模型里加约束

**解决方案**：
在 `app/main.py` 中用 `Field(gt=0)` 添加校验：
```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str
    price: float = Field(gt=0, description="商品价格，必须大于 0")
```

**总结**：写接口测试时，不能只测「正常路径」，还要测「业务约束」。如果测试失败，先判断是测试写错了还是后端有 bug，不要盲目改测试。

---

## 五、Allure 报告问题

### 问题 7：Allure 报告生成失败，找不到 Java

**现象**：
CI 中执行 `allure generate` 报错，提示需要 Java 运行环境。

**分析思路**：
1. Allure 是基于 Java 的工具，运行时依赖 JRE
2. GitHub Runner 默认没有装 Java
3. 需要先装 JRE，再下载 Allure 二进制包

**解决方案**：
在 CI 中增加安装步骤：
```yaml
- name: Install Allure
  run: |
    sudo apt-get update
    sudo apt-get install -y openjdk-11-jre
    wget https://github.com/allure-framework/allure2/releases/download/2.24.0/allure-2.24.0.tgz
    tar -xzf allure-2.24.0.tgz
    echo "$(pwd)/allure-2.24.0/bin" >> $GITHUB_PATH
```

**总结**：使用第三方工具前，先确认它的依赖环境。Allure 依赖 Java，pytest 依赖 Python，工具链的依赖关系要理清楚。

---

## 排障方法论

本周踩了这么多坑，总结出一套排障思路：

1. **看报错信息** — 先把错误信息读完整，exit code、报错栈、上下文
2. **定位范围** — 是环境问题？配置问题？代码问题？先缩小排查范围
3. **Google/搜索** — 把报错信息复制去搜，大概率有人遇到过
4. **逐一验证** — 不要一次改多处，改一个验证一个，找到真正的原因
5. **记录下来** — 解决后立刻记录，否则下次还会踩同样的坑

---

## 六、第 2 周问题（代码扫描 / 分层流水线 / 门禁）

### 问题 8：flake8 报 `W503` 和 `E501` 告警过多

**现象**：
首次运行 flake8，输出大量 W503（运算符换行）和 E501（行过长）告警。

**分析思路**：
1. W503 是 PEP8 中关于运算符换行的规则，和项目风格无关
2. E501 是行长度限制，项目已配置 max-line-length=120，但有些行超过限制
3. 这些不是真正的代码质量问题，是风格偏好

**解决方案**：
在 `.flake8` 中忽略 W503，E501 通过调整代码格式解决：
```ini
[flake8]
ignore = E501, W503
```

**总结**：不要追求零告警，重要的是理解每条告警的含义。配置文件就是用来做取舍的。

---

### 问题 9：pylint 评分从 0.00 到 10.00 的优化过程

**现象**：
首次运行 pylint，评分 0.00/10，报出大量 C0114（缺模块文档）、C0115（缺类文档）等告警。

**分析思路**：
1. 缺文档字符串的告警对 MVP 项目不实用
2. 未使用的 import 是真正需要修的
3. 函数间空行不够是格式问题

**解决方案**：
```ini
# .pylintrc
[MESSAGES CONTROL]
disable=C0114, C0115, C0116, R0903, R0913
```
代码层面：删除未使用的 `HTTPException`，调整 import 顺序，函数间加空行。

**总结**：pylint 的 disable 列表要定期 review，避免永久忽略重要规则。

---

### 问题 10：pytest marker 未注册导致警告

**现象**：
运行 `pytest -m smoke` 时输出 `PytestUnknownMarkWarning: Unknown markers`。

**分析思路**：
1. pytest 默认不认识自定义 marker
2. 需要在 `pytest.ini` 中显式注册
3. 加 `--strict-markers` 可以在 CI 中强制检查

**解决方案**：
创建 `pytest.ini`：
```ini
[pytest]
markers =
    smoke: 冒烟测试用例（核心链路）
    regression: 回归测试用例（全量）
addopts = --strict-markers
```

**总结**：pytest 的 marker 是用例分级的基础，必须正式注册而不是忽略警告。

---

### 问题 11：覆盖率门禁首次运行不达标

**现象**：
CI 中 `--cov-fail-under=70` 导致构建失败，覆盖率只有 ~40%。

**分析思路**：
1. 原来只有 3 条测试，覆盖了 happy path
2. Pydantic 校验的各个分支没有覆盖
3. 需要补充异常输入、边界值的测试用例

**解决方案**：
从 3 条扩展到 10 条测试，覆盖缺 name、缺 price、负数、零、类型错误等场景，覆盖率提升到 70%+。

**总结**：覆盖率门禁先设一个可达的阈值（如 70%），再逐步提高。古德哈特定律提醒我们：覆盖率不能作为唯一指标。

---

### 问题 12：分支保护配置后无法直接 push

**现象**：
配置 branch protection rule 后，直接 `git push origin main` 被拒绝。

**分析思路**：
1. 这是分支保护的预期行为
2. main 和 develop 受保护，必须走 PR 流程
3. 需要先 push 到 feature 分支，再创建 PR

**解决方案**：
```bash
git checkout -b feature/xxx
git push origin feature/xxx
# 然后在 GitHub 网页创建 PR
```

**总结**：分支保护是质量门禁的最后一道防线，确保所有代码都经过 review 和 CI 检查。

---

## 第 2 周排障补充

1. **灰度接入策略** — 新工具先用 `continue-on-error: true` 接入，看数据再收紧阈值
2. **pip 缓存** — `actions/setup-python` 内置 `cache: pip` 参数，一行配置加速 50%
3. **门禁白名单** — 加 `--skip` 参数或环境变量，特殊情况可临时豁免
4. **四层流水线不重复** — 每层职责明确，冒烟只在 PR 跑，全量只在每日跑
