import gc
import hashlib
import os
import sqlite3
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

# memory_profiler 运行时会向 builtins 注入 profile；正常启动时退化为无操作装饰器，
# 保证服务不装 memory_profiler 也能跑。
try:
    profile  # type: ignore[name-defined]  # noqa: B018
except NameError:
    def profile(func):  # type: ignore[no-redef]
        return func

app = FastAPI(title="Demo API")
DB_PATH = os.environ.get("DB_PATH", "/data/demo.db")

# ---------------------------------------------------------------------------
# Prometheus 指标埋点（项目二 Week 2 Day 8）
#
# 覆盖 RED 三要素：
#   Rate     -> REQUEST_COUNT（http_requests_total，Counter）
#   Errors   -> REQUEST_COUNT 的 status_code 标签（5xx/4xx 占比即错误率）
#   Duration -> REQUEST_DURATION（http_request_duration_seconds，Histogram）
# 另加 ACTIVE_REQUESTS（Gauge）观察并发饱和度。
#
# 两个工程细节：
# 1) /metrics 自身不计入业务指标——Prometheus 每几秒 scrape 一次，
#    若不排除，自监控流量会污染 Rate 统计（周计划坑 1）。
# 2) path 标签用路由模板（/items/{item_id}）而非实际 URL（/items/123），
#    否则每个 id 生成一条时间序列，标签基数爆炸。
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)
ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of active HTTP requests",
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # /metrics 是监控端点，不计入业务指标
    if request.url.path == "/metrics":
        return await call_next(request)

    ACTIVE_REQUESTS.inc()
    start_time = time.time()
    try:
        response = await call_next(request)
    finally:
        ACTIVE_REQUESTS.dec()

    duration = time.time() - start_time
    # call_next 完成后路由已匹配，可取到路由模板，避免 path 标签基数爆炸
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)

    REQUEST_COUNT.labels(
        method=request.method,
        path=path,
        status_code=str(response.status_code),
    ).inc()
    REQUEST_DURATION.labels(method=request.method, path=path).observe(duration)
    return response


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head><title>Demo API</title></head>
        <body>
            <h1>Demo API Service</h1>
            <p>Available endpoints:</p>
            <ul>
                <li>GET /health - Health check</li>
                <li>GET /items - List all items</li>
                <li>GET /items/{id} - Get a single item</li>
                <li>POST /items - Create a new item</li>
            </ul>
        </body>
    </html>
    """


class Item(BaseModel):
    name: str
    price: float = Field(gt=0, description="商品价格，必须大于 0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT * FROM items")
    items = [{"id": r[0], "name": r[1], "price": r[2]} for r in cursor]
    conn.close()
    return items


@app.get("/items/{item_id}")
def get_item(item_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": row[0], "name": row[1], "price": row[2]}


@app.post("/items")
def create_item(item: Item):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "INSERT INTO items (name, price) VALUES (?, ?)",
        (item.name, item.price),
    )
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"message": "created", "id": item_id, "item": item}


# ---------------------------------------------------------------------------
# 慢接口（项目二 Week 2 Day 11：CPU / 内存瓶颈分析实战）
#
# /slow/cpu          —— CPU 密集：sha256 循环哈希，用于 py-spy 火焰图定位热点
# /slow/memory       —— 内存泄漏：全局列表只增不减，用于 memory_profiler 定位泄漏点
# /slow/memory/clear —— 清理接口：清空列表 + gc.collect()，验证「清理后内存回落」
#
# 这些接口是 Day 12 性能优化实战的「靶子」，故意写得低效，请勿直接优化。
# ---------------------------------------------------------------------------


@app.get("/slow/cpu")
def slow_cpu(rounds: int = 100):
    """CPU 密集接口：对字符串做 rounds 轮 sha256 哈希。

    每轮哈希串行依赖上一轮结果，无法并行；纯计算、无 IO，
    压测时进程 CPU 使用率会顶到单核 100%，TPS 出现明显封顶。
    """
    data = b"perf-bottleneck-demo"
    for _ in range(rounds * 1000):
        data = hashlib.sha256(data).digest()
    return {"rounds": rounds, "digest_hex": data.hex()[:16]}


# 全局「漏水库」：模拟缓存只写不清的真实事故场景。
_leaky_cache: list[bytes] = []


@app.get("/slow/memory")
@profile  # memory_profiler 逐行统计入口（mprof run 时生效）
def slow_memory(size_kb: int = 100):
    """内存泄漏接口：每次请求向全局列表追加 size_kb KB 数据，永不清理。

    连续压测时进程 RSS 近似线性上涨；调用 /slow/memory/clear 后回落。
    返回当前泄漏总量，便于压测脚本断言趋势。
    """
    _leaky_cache.append(b"x" * (size_kb * 1024))
    cache_mb = len(_leaky_cache) * size_kb / 1024
    return {"cached_chunks": len(_leaky_cache), "cache_mb": round(cache_mb, 2)}


@app.post("/slow/memory/clear")
def slow_memory_clear():
    """清理接口：清空全局列表并强制 GC，验证内存是否可回收。"""
    _leaky_cache.clear()
    gc.collect()
    return {"cleared": True, "cached_chunks": len(_leaky_cache)}
