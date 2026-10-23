# 项目二预习：性能测试基础概念

> 项目一完成后，为项目二（性能测试）做预习准备

---

## 一、性能测试核心概念

### 1. 关键指标

| 指标 | 全称 | 含义 | 典型场景 |
|------|------|------|----------|
| TPS | Transactions Per Second | 每秒事务数 | 电商下单：500 TPS 为目标 |
| RT | Response Time | 响应时间 | API < 200ms 为达标 |
| QPS | Queries Per Second | 每秒查询数 | 读接口：2000 QPS |
| 并发用户数 | Concurrent Users | 同时在线用户数 | 1000 并发为基准 |
| 错误率 | Error Rate | 失败请求占比 | < 0.1% 为达标 |
| P95 | 95th Percentile | 95% 请求的响应时间 | P95 < 500ms |
| P99 | 99th Percentile | 99% 请求的响应时间 | P99 < 1s |

### 2. TPS vs QPS

- **TPS**：一个事务可能包含多个请求（如：登录 → 浏览商品 → 下单 → 支付 = 1 个事务，4 个请求）
- **QPS**：单个接口的请求频率
- 关系：TPS × 每事务请求数 ≈ QPS

### 3. 响应时间分层

| 层级 | 范围 | 用户感受 |
|------|------|----------|
| 优秀 | < 100ms | 即时响应 |
| 良好 | 100ms - 500ms | 流畅 |
| 可接受 | 500ms - 1s | 可感知延迟 |
| 需优化 | 1s - 3s | 慢 |
| 不可接受 | > 3s | 用户流失 |

---

## 二、性能测试类型

| 类型 | 目的 | 加压方式 | 典型工具 |
|------|------|----------|----------|
| 基线测试 | 建立性能基线 | 固定并发 | k6 / JMeter |
| 负载测试 | 找到最大承载能力 | 逐步加压 | k6 / JMeter |
| 压力测试 | 验证超负载行为 | 超过峰值 | k6 / JMeter |
| 稳定性测试 | 长时间运行 | 持续负载 | k6 / JMeter |
| 并发测试 | 验证并发处理 | 同时请求 | k6 / JMeter |
| 容量测试 | 规划资源 | 不同数据量 | JMeter |

---

## 三、性能测试工具对比

### k6 vs JMeter

| 维度 | k6 | JMeter |
|------|-----|--------|
| 语言 | JavaScript（Go 引擎） | Java |
| 脚本编写 | 代码式，开发友好 | GUI 录制，上手快 |
| 资源占用 | 低（单进程） | 高（JVM） |
| CI 集成 | 原生支持 | 需要插件 |
| 分布式 | k6 Cloud（付费） | JMeter Cluster |
| 报告 | JSON + 多种输出 | HTML + Dashboard |
| 适合场景 | API 性能测试 / CI 集成 | 复杂场景 / GUI 操作 |

### 推荐选择

- **项目二推荐 k6**：
  - 与项目一的 GitHub Actions CI 无缝集成
  - JavaScript 脚本和 Playwright 技术栈一致
  - 轻量级，CI 中运行快
  - 原生支持阈值断言（pass/fail）

---

## 四、性能瓶颈定位方法

### 四层分析法

```
请求 → [网络] → [应用层] → [数据库] → [存储层]
```

| 层级 | 排查工具 | 典型瓶颈 |
|------|----------|----------|
| 网络 | ping / traceroute / tcpdump | 带宽不足、延迟高 |
| 应用层 | top / htop / py-spy / flamegraph | CPU 100%、内存泄漏、GIL |
| 数据库 | EXPLAIN / slow_query_log | 慢查询、缺索引、锁竞争 |
| 存储层 | iostat / iotop | 磁盘 I/O 饱和 |

### 常见瓶颈模式

1. **CPU 密集型**：响应时间随并发线性增长 → 优化算法 / 加缓存
2. **I/O 密集型**：响应时间在某个并发点跳变 → 加连接池 / 异步化
3. **数据库瓶颈**：慢查询导致连接池耗尽 → 加索引 / 读写分离
4. **内存泄漏**：长时间运行后 RT 逐渐增大 → 用 valgrind / memory_profiler 定位

---

## 五、如果要给当前项目做性能测试

### 测试场景规划

| 场景 | 目标指标 | 测试方式 |
|------|----------|----------|
| GET /items 列表查询 | TPS > 500，P95 < 200ms | 100-500 并发逐步加压 |
| POST /items 创建商品 | TPS > 100，P95 < 500ms | 50-200 并发逐步加压 |
| GET /health 健康检查 | TPS > 2000，P95 < 50ms | 500-2000 并发持续加压 |
| 混合场景（读:写 = 8:2） | 整体 TPS > 300 | 模拟真实流量比例 |

### k6 脚本示例

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 100 },  // 30 秒内加到 100 并发
    { duration: '1m', target: 100 },    // 维持 100 并发 1 分钟
    { duration: '30s', target: 0 },     // 30 秒内降到 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'],   // P95 < 200ms
    http_req_failed: ['rate<0.01'],     // 错误率 < 1%
  },
};

export default function () {
  const res = http.get('http://localhost:8000/items');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });
  sleep(0.1);  // 模拟用户思考时间
}
```

### CI 集成思路

```yaml
performance-test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Build & start API
      run: |
        docker build -t demo-api .
        docker compose up -d api
    - name: Run k6 test
      run: |
        k6 run --out json=results.json tests/performance/load.js
    - name: Check thresholds
      run: |
        # 解析 results.json，检查是否有未达标的阈值
        cat results.json | jq '.metrics.http_req_duration.threshold.result'
```

---

## 六、预习清单

- [ ] 了解 TPS / RT / P95 / P99 的含义和计算方式
- [ ] 了解基线测试 / 负载测试 / 压力测试的区别
- [ ] 了解 k6 的基本用法（安装、脚本、阈值、报告）
- [ ] 了解性能瓶颈定位的四层分析法
- [ ] 思考：当前项目哪些接口需要做性能测试？
- [ ] 思考：性能测试如何接入 CI/CD 流水线？
