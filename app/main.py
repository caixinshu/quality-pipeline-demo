import asyncio
import gc
import hashlib
import os
import sqlite3
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

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


# ---------------------------------------------------------------------------
# 优化接口（项目二 Week 2 Day 12：性能优化实战）
#
# 针对 Day 11 定位出的两个热点（main.py 的 sha256 循环、_leaky_cache 无限增长）
# 按「不做 → 少做 → 做得更快 → 并行做」优先级各实现一组对照接口，
# 用与 Day 11 完全相同的压测参数做 A/B 对比，验证优化收益。
# ---------------------------------------------------------------------------


# ---- CPU 优化 1：缓存结果（「少做」——同样的输入只算一次） -----------------


@lru_cache(maxsize=128)
def _cached_hash_chain(seed: bytes, rounds: int) -> bytes:
    """与 slow_cpu 完全相同的计算，但结果被 lru_cache 记忆。"""
    data = seed
    for _ in range(rounds * 1000):
        data = hashlib.sha256(data).digest()
    return data


@app.get("/slow/cpu/opt/cache")
def slow_cpu_opt_cache(rounds: int = 100):
    """CPU 优化·缓存：首轮慢（真实计算），之后同参数请求直接命中缓存。

    适用前提：相同输入会被重复请求——这正是「缓存」类优化的边界条件。
    """
    data = _cached_hash_chain(b"perf-bottleneck-demo", rounds)
    return {"rounds": rounds, "digest_hex": data.hex()[:16], "opt": "lru_cache"}


# ---- CPU 优化 2：换更快算法（「做得更快」——blake2b 同安全性下更快） -------


@app.get("/slow/cpu/opt/blake2")
def slow_cpu_opt_blake2(rounds: int = 100):
    """CPU 优化·算法：同样轮数换成 blake2b（现代哈希，软件实现快于 sha256）。"""
    data = b"perf-bottleneck-demo"
    for _ in range(rounds * 1000):
        data = hashlib.blake2b(data, digest_size=32).digest()
    return {"rounds": rounds, "digest_hex": data.hex()[:16], "opt": "blake2b"}


# ---- CPU 优化 3：多进程并行（「并行做」——绕开 GIL，用满多核） -------------


def _hash_chunk(seed: bytes, iterations: int) -> bytes:
    """进程池工作函数：必须是模块级函数才可被 pickle 到子进程。"""
    data = seed
    for _ in range(iterations):
        data = hashlib.sha256(data).digest()
    return data


_cpu_pool = None  # ProcessPoolExecutor 单例，懒加载（Py3.9 环境不用 X | None 注解）


def _get_cpu_pool() -> ProcessPoolExecutor:
    """懒加载全局进程池：避免每请求重复 spawn 进程的开销。"""
    global _cpu_pool
    if _cpu_pool is None:
        _cpu_pool = ProcessPoolExecutor(max_workers=4)
    return _cpu_pool


@app.get("/slow/cpu/opt/parallel")
async def slow_cpu_opt_parallel(rounds: int = 100):
    """CPU 优化·并行：把总计算量切 4 份扔进进程池，多核并行。

    Day 11 已验证线程池对 CPU 密集无效（GIL 串行），
    所以这里用 ProcessPoolExecutor 绕开 GIL——代价是进程间通信与 spawn 开销。
    """
    pool = _get_cpu_pool()
    loop = asyncio.get_running_loop()
    total = rounds * 1000
    chunk = total // 4
    futures = [
        loop.run_in_executor(pool, _hash_chunk, b"perf-bottleneck-demo", chunk)
        for _ in range(4)
    ]
    results = await asyncio.gather(*futures)
    return {
        "rounds": rounds,
        "workers": 4,
        "digest_hex": results[0].hex()[:16],
        "opt": "process_pool",
    }


# ---- 内存优化 1：容量上限（deque(maxlen) 自动淘汰最旧数据） ---------------


_bounded_cache: deque[bytes] = deque(maxlen=1000)  # 上限 1000 条 × 100KB ≈ 100MB 封顶


@app.get("/slow/memory/opt/bounded")
def slow_memory_opt_bounded(size_kb: int = 100):
    """内存优化·容量上限：有界缓存，写满后自动淘汰最旧条目。

    与泄漏版同样的写入速率，但内存占用有硬顶——压测时 RSS 应先升后平。
    """
    _bounded_cache.append(b"x" * (size_kb * 1024))
    cache_mb = len(_bounded_cache) * size_kb / 1024
    return {
        "cached_chunks": len(_bounded_cache),
        "cache_mb": round(cache_mb, 2),
        "opt": "bounded_deque",
    }


# ---- 内存优化 2：用完即放（不保留引用，根本不进缓存） ---------------------


@app.get("/slow/memory/opt/release")
def slow_memory_opt_release(size_kb: int = 100):
    """内存优化·及时释放：数据仅本次请求内使用，不挂到任何全局对象。

    局部变量出作用域即被引用计数回收，RSS 全程平稳。
    对应真实场景：流式处理/用完即弃，而不是万物皆缓存。
    """
    data = b"x" * (size_kb * 1024)
    checksum = hash(data)  # 模拟「使用」这份数据
    del data  # 显式释放引用（其实出作用域也会回收，写出来是强调意图）
    return {"processed_kb": size_kb, "checksum": checksum, "opt": "release"}
