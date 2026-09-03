import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_item():
    """测试创建商品"""
    response = client.post("/items", json={"name": "book", "price": 12.5})
    assert response.status_code == 200
    assert response.json()["item"]["name"] == "book"


def test_list_items():
    """测试查询列表"""
    client.post("/items", json={"name": "pen", "price": 3.0})
    response = client.get("/items")
    assert response.status_code == 200
    assert len(response.json()) >= 1
