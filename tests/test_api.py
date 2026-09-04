import pytest
import requests

BASE_URL = "http://localhost:8000"


class TestAPI:

    def test_health_check(self):
        """健康检查 - 基础断言"""
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_create_and_query(self):
        """创建后查询 - 数据一致性验证"""
        payload = {"name": "ci_test", "price": 19.9}
        resp = requests.post(f"{BASE_URL}/items", json=payload)
        assert resp.status_code == 200

        resp = requests.get(f"{BASE_URL}/items")
        assert resp.status_code == 200
        items = resp.json()
        assert any(i["name"] == "ci_test" for i in items)

    def test_create_invalid_data(self):
        """异常输入 - 参数校验"""
        resp = requests.post(f"{BASE_URL}/items", json={"name": ""})
        assert resp.status_code == 422

    def test_price_negative(self):
        """边界值 - 负数价格"""
        resp = requests.post(f"{BASE_URL}/items", json={"name": "neg", "price": -1})
        assert resp.status_code == 422
