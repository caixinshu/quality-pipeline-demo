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


def test_create_item_missing_name():
    """异常输入 - 缺少 name 字段"""
    response = client.post("/items", json={"price": 10.0})
    assert response.status_code == 422


def test_create_item_missing_price():
    """异常输入 - 缺少 price 字段"""
    response = client.post("/items", json={"name": "test"})
    assert response.status_code == 422


def test_create_item_negative_price():
    """边界值 - 负数价格"""
    response = client.post("/items", json={"name": "neg", "price": -1})
    assert response.status_code == 422


def test_create_item_zero_price():
    """边界值 - 零价格"""
    response = client.post("/items", json={"name": "zero", "price": 0})
    assert response.status_code == 422


def test_create_item_wrong_type():
    """异常输入 - 价格类型错误"""
    response = client.post("/items", json={"name": "bad", "price": "abc"})
    assert response.status_code == 422


def test_list_items_returns_list():
    """验证返回结构是列表"""
    response = client.get("/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_and_verify_fields():
    """创建后验证返回字段完整性"""
    response = client.post("/items", json={"name": "desk", "price": 99.9})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["item"]["name"] == "desk"
    assert data["item"]["price"] == 99.9
