import os
import sqlite3

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Demo API")
DB_PATH = os.environ.get("DB_PATH", "/data/demo.db")


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


@app.post("/items")
def create_item(item: Item):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO items (name, price) VALUES (?, ?)",
        (item.name, item.price),
    )
    conn.commit()
    conn.close()
    return {"message": "created", "item": item}
