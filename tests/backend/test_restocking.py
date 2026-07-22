"""
Tests for the restocking recommendation and order-submission endpoints.
"""
import pytest


class TestRestockRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_zero_budget_returns_no_recommendations(self, client):
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0

    def test_large_budget_returns_multiple_items(self, client):
        response = client.get("/api/restocking/recommendations?budget=100000")
        assert response.status_code == 200

        data = response.json()
        assert len(data["recommendations"]) > 1

        skus = [r["sku"] for r in data["recommendations"]]
        assert "PSU-501" in skus

    def test_recommendations_are_internally_consistent(self, client):
        response = client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()

        for rec in data["recommendations"]:
            expected_line_total = round(rec["recommended_quantity"] * rec["unit_cost"], 2)
            assert abs(rec["line_total"] - expected_line_total) < 0.01
            assert rec["recommended_quantity"] > 0
            assert rec["shortfall"] == rec["forecasted_demand"] - rec["current_demand"]

        assert abs(data["total_cost"] - sum(r["line_total"] for r in data["recommendations"])) < 0.01
        assert abs(data["remaining_budget"] - (data["budget"] - data["total_cost"])) < 0.01

    def test_recommendations_ranked_by_shortfall_descending(self, client):
        response = client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()

        shortfalls = [r["shortfall"] for r in data["recommendations"]]
        assert shortfalls == sorted(shortfalls, reverse=True)

    def test_missing_budget_is_required(self, client):
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    def test_small_budget_limits_total_cost(self, client):
        response = client.get("/api/restocking/recommendations?budget=100")
        assert response.status_code == 200

        data = response.json()
        assert data["total_cost"] <= 100


class TestSubmitRestockOrder:
    """Test suite for POST /api/restocking/orders."""

    def test_place_valid_restock_order(self, client):
        response = client.post("/api/restocking/orders", json={
            "budget": 5000,
            "items": [{"sku": "PSU-501", "quantity": 50}]
        })
        assert response.status_code == 201

        data = response.json()
        assert data["source"] == "restock"
        assert data["status"] == "Processing"
        assert data["customer"] == "Internal Restocking"
        assert isinstance(data["lead_time_days"], int)
        assert data["lead_time_days"] > 0
        assert data["total_value"] == pytest.approx(50 * 18.99, abs=0.01)

        order_number = data["order_number"]
        assert order_number.startswith("ORD-")
        parts = order_number.split("-")
        assert len(parts) == 3
        assert len(parts[2]) == 4

    def test_order_number_does_not_collide_with_seeded_orders(self, client):
        before = client.get("/api/orders").json()
        existing_numbers = {o["order_number"] for o in before}

        response = client.post("/api/restocking/orders", json={
            "budget": 1000,
            "items": [{"sku": "PSU-501", "quantity": 10}]
        })
        assert response.status_code == 201
        assert response.json()["order_number"] not in existing_numbers

    def test_unknown_sku_returns_400(self, client):
        response = client.post("/api/restocking/orders", json={
            "budget": 1000,
            "items": [{"sku": "DOES-NOT-EXIST", "quantity": 10}]
        })
        assert response.status_code == 400

    def test_non_positive_quantity_returns_400(self, client):
        response = client.post("/api/restocking/orders", json={
            "budget": 1000,
            "items": [{"sku": "PSU-501", "quantity": 0}]
        })
        assert response.status_code == 400

    def test_submitted_order_appears_in_orders_list(self, client):
        response = client.post("/api/restocking/orders", json={
            "budget": 2000,
            "items": [{"sku": "PSU-501", "quantity": 20}]
        })
        assert response.status_code == 201
        order_number = response.json()["order_number"]

        orders_response = client.get("/api/orders")
        order_numbers = [o["order_number"] for o in orders_response.json()]
        assert order_number in order_numbers
