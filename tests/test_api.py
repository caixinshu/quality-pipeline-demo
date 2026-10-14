import allure
import pytest
import requests

BASE_URL = "http://localhost:8000"


@allure.feature("商品管理")
class TestAPI:

    @pytest.mark.smoke
    @allure.story("健康检查")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_health_check(self):
        """验证服务健康状态"""
        with allure.step("发送 /health 请求"):
            resp = requests.get(f"{BASE_URL}/health")
        with allure.step("验证状态码和响应体"):
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    @pytest.mark.smoke
    @allure.story("创建与查询")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_and_query(self):
        """创建后查询 - 数据一致性验证"""
        payload = {"name": "ci_test", "price": 19.9}
        with allure.step("创建商品"):
            resp = requests.post(f"{BASE_URL}/items", json=payload)
        with allure.step("验证创建成功"):
            assert resp.status_code == 200

        with allure.step("查询商品列表"):
            resp = requests.get(f"{BASE_URL}/items")
        with allure.step("验证列表包含新创建的商品"):
            assert resp.status_code == 200
            items = resp.json()
            assert any(i["name"] == "ci_test" for i in items)

    @pytest.mark.regression
    @allure.story("异常输入校验")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_invalid_data(self):
        """异常输入 - 参数校验"""
        with allure.step("发送缺少字段的请求"):
            resp = requests.post(f"{BASE_URL}/items", json={"name": ""})
        with allure.step("验证返回 422"):
            assert resp.status_code == 422

    @pytest.mark.regression
    @allure.story("边界值测试")
    @allure.severity(allure.severity_level.NORMAL)
    def test_price_negative(self):
        """边界值 - 负数价格"""
        with allure.step("发送负数价格请求"):
            resp = requests.post(f"{BASE_URL}/items", json={"name": "neg", "price": -1})
        with allure.step("验证返回 422"):
            assert resp.status_code == 422
