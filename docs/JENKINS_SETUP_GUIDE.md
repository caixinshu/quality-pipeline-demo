# Jenkins 搭建指南：四层质量流水线

> 如果项目从 GitHub Actions 迁移到 Jenkins，如何搭建同等的四层流水线 + 三条质量门禁 + 精准测试 + UI 自动化

---

## 一、GitHub Actions vs Jenkins 架构对比

| 维度 | GitHub Actions | Jenkins |
|------|---------------|---------|
| 部署方式 | SaaS（无需运维） | 自建服务器（需运维） |
| 配置文件 | `.github/workflows/*.yml` | `Jenkinsfile`（Groovy DSL） |
| 触发方式 | push / PR / cron / tag | webhook / poll / cron / 手动 |
| 缓存机制 | `actions/cache` | Jenkins 自带 workspace 缓存 |
| 并行执行 | `strategy.matrix` | `parallel` + `agent` 分布式 |
| 报告托管 | artifact（14 天过期） | Jenkins 自带持久化报告 |
| 分支保护 | GitHub branch protection | GitHub branch protection 或 Jenkins gate |
| 插件生态 | Marketplace | 插件市场更大（1800+） |
| 成本 | 公开仓库免费 | 服务器成本 |

---

## 二、Jenkins 环境准备

### 2.1 安装 Jenkins

```bash
# Ubuntu/Debian
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo tee /usr/share/keyrings/jenkins-keyring.asc
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" | sudo tee /etc/apt/sources.list.d/jenkins.list
sudo apt-get update
sudo apt-get install -y jenkins

# 启动
sudo systemctl start jenkins
sudo systemctl enable jenkins

# 查看初始密码
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

### 2.2 安装必需插件

进入 `Manage Jenkins → Plugins → Available plugins`，安装：

| 插件 | 用途 | 对标 GitHub Actions |
|------|------|---------------------|
| Pipeline | Jenkinsfile 执行引擎 | workflows/*.yml |
| Git | 代码拉取 | actions/checkout |
| Docker | Docker 集成 | docker build / compose |
| Allure Jenkins Plugin | Allure 报告持久化 | allure generate + upload-artifact |
| HTML Publisher | HTML 报告托管 | upload-artifact |
| JUnit | 测试结果可视化 | junitxml + upload-artifact |
| Cobertura | 覆盖率报告 | coverage.xml |
| NodeJS | Playwright 环境 | actions/setup-node |
| ws-cleanup | workspace 清理 | docker compose down |
| Job DSL | 流水线即代码 | workflow 定义 |

### 2.3 全局工具配置

进入 `Manage Jenkins → Global Tool Configuration`：

**JDK**：
- 安装 JDK 11（Allure 依赖）
- `JAVA_HOME` = `/usr/lib/jvm/java-11-openjdk-amd64`

**Allure Commandline**：
- 自动安装 Allure 2.24.0
- 配置后 Jenkins 自动管理 Allure 路径

**Python**：
- 安装 Python 3.11

**NodeJS**：
- 安装 Node.js 20（用于 Playwright）

### 2.4 配置 Agent（分布式构建节点）

```bash
# 在 Jenkins 服务器上创建 agent 工作目录
sudo mkdir -p /var/jenkins/agent-workspace
sudo chown -R jenkins:jenkins /var/jenkins/agent-workspace

# 进入 Manage Jenkins → Nodes → New Node
# 名称: build-agent-1
# 类型: Permanent Agent
# Remote root: /var/jenkins/agent-workspace
# Labels: linux docker python node
# 用途: 尽可能使用
```

如果需要多浏览器并行（WebKit 需要 macOS），可以添加 macOS agent：
```
# 在 Mac 上启动 agent
java -jar agent.jar -jnlpUrl http://jenkins-server/computer/macos-agent/slave-agent.jnlp
# Labels: macos webkit
```

---

## 三、四层流水线 Jenkinsfile

### 3.1 提交级流水线（Commit Pipeline）

**对标**：`.github/workflows/ci.yml`

**触发方式**：Push 到 main/develop 分支

```groovy
// Jenkinsfile.commit
pipeline {
    agent any
    environment {
        PYTHON_VERSION = '3.11'
        HOME = '.'
    }
    options {
        timeout(time: 5, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '50'))
    }
    triggers {
        // 方式一：webhook（GitHub 配置后自动触发，无需 poll）
        // 方式二：poll SCM（无 webhook 时使用）
        pollSCM('H/2 * * * *')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scmGit(
                    branches: [[name: '*/develop']],
                    userRemoteConfigs: [[url: 'https://github.com/caixinshu/quality-pipeline-demo.git']]
                )
            }
        }
        
        stage('Setup Python') {
            steps {
                sh '''
                    python3.11 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install pytest pytest-cov
                '''
            }
        }
        
        stage('Unit Test + Coverage') {
            parallel {
                stage('Unit Test') {
                    steps {
                        sh '''
                            . .venv/bin/activate
                            pytest tests/test_unit.py -v \
                                --cov=app \
                                --cov-report=term \
                                --cov-report=html \
                                --cov-report=xml \
                                --cov-fail-under=70 \
                                --junitxml=test-results.xml
                        '''
                    }
                    post {
                        always {
                            junit 'test-results.xml'
                            publishHTML([
                                reportDir: 'htmlcov',
                                reportName: 'Coverage Report',
                                reportFiles: 'index.html'
                            ])
                        }
                    }
                }
                
                stage('Code Scan') {
                    steps {
                        sh '''
                            . .venv/bin/activate
                            pip install flake8 pylint bandit
                            
                            flake8 app/ --count --statistics || true
                            pylint app/ --output-format=text || true
                            bandit -r app/ -f txt -o bandit-report.txt || true
                        '''
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'bandit-report.txt', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs(cleanWhenAborted: true, cleanWhenFailure: true, cleanWhenSuccess: true)
        }
    }
}
```

### 3.2 合并级流水线（PR Pipeline）

**对标**：`.github/workflows/pr-pipeline.yml`

**触发方式**：GitHub PR Webhook → Jenkins Multibranch Pipeline

```groovy
// Jenkinsfile.pr
pipeline {
    agent any
    environment {
        PYTHON_VERSION = '3.11'
        DOCKER_BUILDKIT = '1'
    }
    options {
        timeout(time: 10, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scmGit(
                    branches: [[name: '*/develop']],
                    extensions: [[$class: 'CloneOption', shallow: false, depth: 0]],
                    userRemoteConfigs: [[url: 'https://github.com/caixinshu/quality-pipeline-demo.git']]
                )
            }
        }
        
        // 并行执行四个 job：冒烟 / 精准 / UI 冒烟 / 代码扫描
        stage('PR Pipeline') {
            parallel {
                // === Job 1: 接口冒烟测试 ===
                stage('Smoke Test') {
                    stages {
                        stage('Setup Python') {
                            steps {
                                sh '''
                                    python3.11 -m venv .venv-smoke
                                    . .venv-smoke/bin/activate
                                    pip install -r requirements.txt
                                    pip install pytest requests allure-pytest
                                '''
                            }
                        }
                        stage('Build & Start API') {
                            steps {
                                sh '''
                                    docker build -t demo-api .
                                    docker compose up -d api
                                    for i in $(seq 1 30); do
                                        if curl -sf http://localhost:8000/health; then
                                            echo "Service is ready!"
                                            break
                                        fi
                                        echo "Waiting... ($i)"
                                        sleep 2
                                    done
                                '''
                            }
                        }
                        stage('Run Smoke Tests') {
                            steps {
                                sh '''
                                    . .venv-smoke/bin/activate
                                    pytest tests/ -m smoke -v \
                                        --alluredir=allure-results-smoke \
                                        --clean-alluredir \
                                        --junitxml=smoke-results.xml
                                '''
                            }
                        }
                        stage('Quality Gate') {
                            steps {
                                sh '''
                                    . .venv-smoke/bin/activate
                                    python scripts/quality_gate.py --junit smoke-results.xml --min-pass-rate 1.0
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            script {
                                // Allure 报告（Jenkins 插件持久化，不会过期）
                                allure = load 'allure-jenkins.groovy'
                            }
                            allure([
                                includeProperties: false,
                                jdk: '',
                                properties: [],
                                report: 'allure-report-smoke',
                                results: [[path: 'allure-results-smoke']]
                            ])
                            junit 'smoke-results.xml'
                            sh 'docker compose down || true'
                        }
                    }
                }
                
                // === Job 2: 精准测试 ===
                stage('Precision Test') {
                    stages {
                        stage('Setup') {
                            steps {
                                sh '''
                                    python3.11 -m venv .venv-precision
                                    . .venv-precision/bin/activate
                                    pip install -r requirements.txt
                                    pip install pytest requests allure-pytest
                                '''
                            }
                        }
                        stage('Analyze Changes') {
                            steps {
                                sh '''
                                    . .venv-precision/bin/activate
                                    python scripts/precision_test.py --mode pr --output .precision_cmd.txt --dry-run
                                    cat .precision_cmd.txt
                                '''
                            }
                        }
                        stage('Build & Start API') {
                            steps {
                                sh '''
                                    docker build -t demo-api .
                                    docker compose up -d api
                                    for i in $(seq 1 30); do
                                        if curl -sf http://localhost:8000/health; then
                                            echo "Service is ready!"
                                            break
                                        fi
                                        echo "Waiting... ($i)"
                                        sleep 2
                                    done
                                '''
                            }
                        }
                        stage('Run Selected Tests') {
                            steps {
                                script {
                                    def cmd = sh(script: 'cat .precision_cmd.txt', returnStdout: true).trim()
                                    echo "Precision selected: ${cmd}"
                                    sh """
                                        . .venv-precision/bin/activate
                                        ${cmd} \
                                            --alluredir=allure-results-precision \
                                            --clean-alluredir \
                                            --junitxml=precision-results.xml
                                    """
                                }
                            }
                        }
                        stage('Quality Gate') {
                            steps {
                                sh '''
                                    . .venv-precision/bin/activate
                                    python scripts/quality_gate.py --junit precision-results.xml --min-pass-rate 1.0
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            allure([
                                report: 'allure-report-precision',
                                results: [[path: 'allure-results-precision']]
                            ])
                            junit 'precision-results.xml'
                            sh 'docker compose down || true'
                        }
                    }
                }
                
                // === Job 3: UI 冒烟测试 ===
                stage('UI Smoke Test') {
                    stages {
                        stage('Setup Node') {
                            steps {
                                sh '''
                                    npm install @playwright/test
                                    npx playwright install --with-deps chromium
                                '''
                            }
                        }
                        stage('Setup Python') {
                            steps {
                                sh '''
                                    python3.11 -m venv .venv-ui
                                    . .venv-ui/bin/activate
                                    pip install -r requirements.txt
                                '''
                            }
                        }
                        stage('Build & Start API') {
                            steps {
                                sh '''
                                    docker build -t demo-api .
                                    docker compose up -d api
                                    for i in $(seq 1 30); do
                                        if curl -sf http://localhost:8000/health; then
                                            echo "Service is ready!"
                                            break
                                        fi
                                        echo "Waiting... ($i)"
                                        sleep 2
                                    done
                                '''
                            }
                        }
                        stage('Run UI Smoke Tests') {
                            steps {
                                sh 'npx playwright test tests/ui/smoke.spec.ts --project=chromium'
                            }
                        }
                    }
                    post {
                        always {
                            publishHTML([
                                reportDir: 'playwright-report',
                                reportName: 'Playwright Report',
                                reportFiles: 'index.html',
                                keepAll: true
                            ])
                            // 失败时归档 trace 文件
                            archiveArtifacts artifacts: 'test-results/**/trace.zip', allowEmptyArchive: true
                            sh 'docker compose down || true'
                        }
                    }
                }
                
                // === Job 4: 代码扫描 ===
                stage('Code Scan') {
                    stages {
                        stage('Setup') {
                            steps {
                                sh '''
                                    python3.11 -m venv .venv-scan
                                    . .venv-scan/bin/activate
                                    pip install flake8 bandit
                                '''
                            }
                        }
                        stage('Run Scans') {
                            steps {
                                sh '''
                                    . .venv-scan/bin/activate
                                    flake8 app/ --count --statistics || true
                                    bandit -r app/ -f txt -o bandit-report.txt || true
                                '''
                            }
                        }
                        stage('Security Gate') {
                            steps {
                                sh '''
                                    . .venv-scan/bin/activate
                                    python scripts/quality_gate.py --bandit bandit-report.txt
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'bandit-report.txt', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs(cleanWhenSuccess: false)  // 成功时保留 workspace 用于缓存
        }
    }
}
```

### 3.3 每日级流水线（Daily Pipeline）

**对标**：`.github/workflows/daily-pipeline.yml`

**触发方式**：Jenkins 定时触发（cron）

```groovy
// Jenkinsfile.daily
pipeline {
    agent any
    environment {
        DOCKER_BUILDKIT = '1'
    }
    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }
    triggers {
        cron('0 2 * * *')  // 每天凌晨 2 点（北京时间）
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scmGit(
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[url: 'https://github.com/caixinshu/quality-pipeline-demo.git']]
                )
            }
        }
        
        stage('Full Pipeline') {
            parallel {
                // === 全量 API 回归 ===
                stage('Full API Test') {
                    stages {
                        stage('Setup') {
                            steps {
                                sh '''
                                    python3.11 -m venv .venv-api
                                    . .venv-api/bin/activate
                                    pip install -r requirements.txt
                                    pip install pytest pytest-cov requests allure-pytest
                                '''
                            }
                        }
                        stage('Build & Start') {
                            steps {
                                sh '''
                                    docker build -t demo-api .
                                    docker compose up -d api
                                    for i in $(seq 1 30); do
                                        if curl -sf http://localhost:8000/health; then
                                            echo "Service is ready!"
                                            break
                                        fi
                                        sleep 2
                                    done
                                '''
                            }
                        }
                        stage('Full Regression') {
                            steps {
                                sh '''
                                    . .venv-api/bin/activate
                                    pytest tests/ -v \
                                        --alluredir=allure-results-full \
                                        --clean-alluredir \
                                        --junitxml=full-results.xml \
                                        --cov=app \
                                        --cov-report=xml \
                                        --cov-report=html \
                                        --cov-fail-under=70
                                '''
                            }
                        }
                        stage('Quality Gate') {
                            steps {
                                sh '''
                                    . .venv-api/bin/activate
                                    python scripts/quality_gate.py --junit full-results.xml --min-pass-rate 1.0
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            allure([
                                report: 'allure-report-full',
                                results: [[path: 'allure-results-full']]
                            ])
                            junit 'full-results.xml'
                            publishHTML([
                                reportDir: 'htmlcov',
                                reportName: 'Coverage Report',
                                reportFiles: 'index.html'
                            ])
                            archiveArtifacts artifacts: 'coverage.xml,full-results.xml', allowEmptyArchive: true
                            sh 'docker compose down || true'
                        }
                    }
                }
                
                // === 全量代码扫描 ===
                stage('Full Code Scan') {
                    stages {
                        stage('Setup') {
                            steps {
                                sh '''
                                    python3.11 -m venv .venv-scan
                                    . .venv-scan/bin/activate
                                    pip install pylint flake8 bandit
                                '''
                            }
                        }
                        stage('Run All Scanners') {
                            steps {
                                sh '''
                                    . .venv-scan/bin/activate
                                    flake8 app/ --count --statistics || true
                                    pylint app/ --output-format=text || true
                                    bandit -r app/ -f txt -o bandit-report.txt || true
                                '''
                            }
                        }
                        stage('Security Gate') {
                            steps {
                                sh '''
                                    . .venv-scan/bin/activate
                                    python scripts/quality_gate.py --bandit bandit-report.txt
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'bandit-report.txt', allowEmptyArchive: true
                        }
                    }
                }
                
                // === 多浏览器 UI 测试 ===
                stage('Full UI Test') {
                    // 用 matrix 实现（Jenkins 需要 Matrix Project 插件）
                    // 或手动展开为三个并行 stage
                    parallel {
                        stage('UI - Chromium') {
                            steps {
                                script {
                                    runUITests('chromium')
                                }
                            }
                        }
                        stage('UI - Firefox') {
                            steps {
                                script {
                                    runUITests('firefox')
                                }
                            }
                        }
                        stage('UI - WebKit') {
                            agent { label 'macos' }  // WebKit 需要 macOS 或特定依赖
                            steps {
                                script {
                                    runUITests('webkit')
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs(cleanWhenSuccess: false)
        }
    }
}

// 多浏览器 UI 测试函数
def runUITests(String browser) {
    sh """
        npm install @playwright/test
        npx playwright install --with-deps ${browser}
        
        docker build -t demo-api .
        docker compose up -d api
        for i in \$(seq 1 30); do
            if curl -sf http://localhost:8000/health; then
                echo "Service is ready!"
                break
            fi
            sleep 2
        done
        
        npx playwright test --project=${browser}
    """
    
    publishHTML([
        reportDir: 'playwright-report',
        reportName: "UI Report - ${browser}",
        reportFiles: 'index.html',
        keepAll: true
    ])
    archiveArtifacts artifacts: 'test-results/**/trace.zip', allowEmptyArchive: true
    sh 'docker compose down || true'
}
```

### 3.4 发布级流水线（Release Pipeline）

**对标**：`.github/workflows/release-pipeline.yml`

**触发方式**：Git tag `v*` + 人工审批

```groovy
// Jenkinsfile.release
pipeline {
    agent any
    options {
        timeout(time: 15, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    triggers {
        // 方式一：Generic Webhook（GitHub tag push 触发）
        // 方式二：手动触发（Build with Parameters）
    }
    parameters {
        string(name: 'RELEASE_TAG', defaultValue: 'v1.0.0', description: '发布版本号')
        booleanParam(name: 'SKIP_APPROVAL', defaultValue: false, description: '跳过人工审批（仅测试用）')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scmGit(
                    branches: [[name: "refs/tags/${params.RELEASE_TAG}"]],
                    userRemoteConfigs: [[url: 'https://github.com/caixinshu/quality-pipeline-demo.git']]
                )
            }
        }
        
        stage('Setup') {
            steps {
                sh '''
                    python3.11 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt
                    pip install pytest requests allure-pytest
                '''
            }
        }
        
        stage('Production Smoke Test') {
            environment {
                BASE_URL = credentials('prod-base-url')  // Jenkins 凭据管理
            }
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest tests/ -m smoke -v \
                        --alluredir=allure-results-release \
                        --clean-alluredir \
                        --junitxml=release-results.xml
                '''
            }
            post {
                always {
                    allure([
                        report: 'allure-report-release',
                        results: [[path: 'allure-results-release']]
                    ])
                    junit 'release-results.xml'
                }
            }
        }
        
        stage('Quality Gate') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python scripts/quality_gate.py --junit release-results.xml --min-pass-rate 1.0
                '''
            }
        }
        
        // 人工审批（对标 GitHub Actions environment: production）
        stage('Approval') {
            when {
                expression { !params.SKIP_APPROVAL }
            }
            steps {
                input(
                    message: "确认发布 ${params.RELEASE_TAG} 到生产环境？",
                    ok: "确认发布",
                    submitter: 'release-managers',  // 只有 release-managers 组可以审批
                    parameters: [
                        string(name: 'APPROVAL_REASON', defaultValue: '', description: '审批理由')
                    ]
                )
            }
        }
        
        stage('Deploy') {
            steps {
                echo "Deploying ${params.RELEASE_TAG} to production..."
                // 部署脚本
                // sh './deploy.sh --tag ${params.RELEASE_TAG}'
            }
        }
    }
    
    post {
        success {
            echo "Release ${params.RELEASE_TAG} deployed successfully!"
            // 可以加通知：Slack / 飞书 / 邮件
        }
        failure {
            echo "Release ${params.RELEASE_TAG} FAILED! Do not deploy."
            // sh './notify.sh --status failed --tag ${params.RELEASE_TAG}'
        }
    }
}
```

---

## 四、触发方式配置

### 4.1 Webhook 触发（推荐）

在 GitHub 仓库 Settings → Webhooks → Add webhook：
```
Payload URL: http://<jenkins-url>/github-webhook/
Content type: application/json
Events: Push, Pull request, Create (for tags)
```

Jenkins 端配置：
- Multibranch Pipeline 自动发现 PR 分支
- `Jenkinsfile.pr` 在 PR 打开/更新时触发
- `Jenkinsfile.commit` 在 push 到 main/develop 时触发

### 4.2 Poll SCM（无 Webhook 时）

```groovy
triggers {
    pollSCM('H/2 * * * *')  // 每 2 分钟检查一次
}
```

### 4.3 定时触发

```groovy
triggers {
    cron('0 2 * * *')  // 每天凌晨 2 点
}
```

### 4.4 手动触发

Jenkins 内置 "Build Now" 按钮，也可通过 `parameters` 实现参数化构建。

---

## 五、缓存策略对比

| 缓存类型 | GitHub Actions | Jenkins |
|----------|---------------|---------|
| pip 缓存 | `cache: pip` | workspace 天然缓存（同节点复用） |
| Docker 缓存 | 无（已回退） | `docker build` 天然缓存（同节点复用） |
| Playwright 浏览器 | `actions/cache` | workspace 天然缓存 |
| Allure | `actions/cache` | Jenkins 全局工具管理 |
| npm 缓存 | `cache: "npm"` | workspace 天然缓存 |

**Jenkins 的缓存优势**：Jenkins agent 的 workspace 在多次构建之间默认保留，不需要显式配置缓存策略。只要用同一个 agent，pip 包、Docker layer、node_modules 都会自动复用。

**注意事项**：如果用 Docker/K8s 动态 agent，workspace 不持久，需要额外配置持久卷或 `actions/cache` 类似的缓存机制。

---

## 六、质量门禁实现

### 6.1 质量门禁脚本（复用）

Jenkins 和 GitHub Actions 复用同一个 `quality_gate.py`，无需修改：

```groovy
stage('Quality Gate') {
    steps {
        sh '''
            . .venv/bin/activate
            python scripts/quality_gate.py --junit test-results.xml --min-pass-rate 1.0
        '''
    }
}
```

### 6.2 分支保护（GitHub 端）

即使 CI 换成 Jenkins，分支保护仍在 GitHub 端配置：
- Settings → Branches → Branch protection rules
- Require status checks to pass → 选择 Jenkins 的 check
- Settings → Webhooks → 配置 Jenkins webhook 回调

### 6.3 分支保护（Jenkins 端）

Jenkins 的 `input` 步骤实现人工审批门禁：
```groovy
stage('Approval Gate') {
    steps {
        input(
            message: '确认合并到 main？',
            ok: '确认',
            submitter: 'release-managers'
        )
    }
}
```

---

## 七、Allure 报告对比

| 维度 | GitHub Actions | Jenkins |
|------|---------------|---------|
| 报告存储 | artifact（14 天过期） | Jenkins 持久化存储（不过期） |
| 历史趋势 | 需要额外配置 | Allure 插件内置趋势图 |
| 报告 URL | artifact 下载后查看 | Jenkins 直接在线浏览 |
| 配置方式 | `allure generate` + upload | `allure([...])` 一行配置 |

Jenkins 的 Allure 插件是最大优势——报告持久化、历史趋势、在线浏览，不需要下载 artifact。

---

## 八、质量看板部署

GitHub Pages 部署在 Jenkins 中改为：

```groovy
stage('Deploy Dashboard') {
    steps {
        sh '''
            # 更新看板数据
            python scripts/generate_dashboard_data.py
            
            # 推送到 gh-pages 分支
            git config user.name "Jenkins CI"
            git config user.email "jenkins@ci.local"
            git checkout --orphan gh-pages
            git add quality-dashboard/
            git commit -m "Update quality dashboard [skip ci]"
            git push origin gh-pages --force
        '''
    }
}
```

或者用 Jenkins 自带的 `publishHTML` 直接托管看板：
```groovy
publishHTML([
    reportDir: 'quality-dashboard',
    reportName: 'Quality Dashboard',
    reportFiles: 'index.html',
    keepAll: true
])
```

---

## 九、Docker 配置注意事项

### 9.1 Jenkins 用户权限

Jenkins 用户需要加入 docker 组：
```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

### 9.2 Docker-in-Docker（如果 Jenkins 本身在容器中）

如果 Jenkins 本身跑在容器中，需要 Docker-in-Docker 或 Docker-outside-of-Docker：

```yaml
# docker-compose.yml（Jenkins 容器化部署）
services:
  jenkins:
    image: jenkins/jenkins:lts
    ports:
      - "8080:8080"
    volumes:
      - jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock  # 挂载宿主机 Docker
      - /usr/bin/docker:/usr/bin/docker
    user: root  # 避免 docker 权限问题
volumes:
  jenkins_home:
```

---

## 十、迁移检查清单

| 检查项 | GitHub Actions | Jenkins | 状态 |
|--------|---------------|---------|------|
| 提交级流水线 | ci.yml | Jenkinsfile.commit | |
| 合并级流水线 | pr-pipeline.yml | Jenkinsfile.pr | |
| 每日级流水线 | daily-pipeline.yml | Jenkinsfile.daily | |
| 发布级流水线 | release-pipeline.yml | Jenkinsfile.release | |
| 质量门禁 | quality_gate.py | 复用（无需修改） | |
| 精准测试 | precision_test.py | 复用（无需修改） | |
| Allure 报告 | artifact + cache | Allure 插件（持久化） | |
| 覆盖率报告 | artifact | Cobertura 插件 + HTML | |
| JUnit 报告 | artifact | JUnit 插件（可视化） | |
| UI 测试 | Playwright + matrix | Playwright + parallel | |
| 多浏览器 | strategy.matrix | parallel stages | |
| 缓存 | actions/cache | workspace 天然缓存 | |
| 人工审批 | environment: production | input step | |
| 分支保护 | GitHub branch protection | GitHub branch protection | |
| 触发方式 | push/PR/cron/tag | webhook/cron/手动 | |
| Docker | docker build | docker build（同 agent） | |

---

## 十一、总结

从 GitHub Actions 迁移到 Jenkins 的核心变化：

1. **配置语言**：YAML → Groovy DSL（学习曲线略陡，但更灵活）
2. **缓存策略**：显式缓存 → workspace 天然缓存（更简单）
3. **报告托管**：artifact 过期 → Jenkins 持久化（更可靠）
4. **触发方式**：原生集成 → webhook 配置（多一步配置）
5. **运维成本**：零运维 → 需要维护服务器（最大差异）
6. **并行执行**：matrix → parallel stages（功能等价）
7. **人工审批**：environment → input step（Jenkins 更灵活）

选择建议：
- **个人项目 / 开源项目** → GitHub Actions（零成本、零运维）
- **企业项目 / 私有代码** → Jenkins（数据可控、插件生态丰富）
- **混合方案** → GitHub Actions 跑 CI，Jenkins 跑 CD（兼顾成本和控制）
