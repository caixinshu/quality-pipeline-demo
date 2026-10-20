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
