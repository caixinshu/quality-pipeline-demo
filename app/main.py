import os
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Demo API")
DB_PATH = os.environ.get("DB_PATH", "/data/demo.db")


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
