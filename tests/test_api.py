from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

CALCULATE_PAYLOAD = {
    "cart_items": [
        {
            "product": {
                "id": "prod-puma-tshirt-001",
                "brand": "PUMA",
                "brand_tier": "premium",
                "category": "T-shirts",
                "base_price": "1500.00",
                "current_price": "1500.00",
            },
            "quantity": 1,
            "size": "M",
        }
    ],
    "customer": {"id": "cust-001", "tier": "regular"},
    "payment_info": {"method": "CARD", "bank_name": "ICICI", "card_type": "CREDIT"},
}


def test_calculate_discounts_endpoint_stacks_brand_category_and_bank_offer():
    response = client.post("/discounts/calculate", json=CALCULATE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["id"]
    assert body["created_at"] > 0
    assert body["original_price"] == "1500.00"
    assert body["final_price"] == "729.00"
    assert body["applied_discounts"]["Min 40% off on PUMA"] == "600.00"


def test_validate_discount_code_endpoint_true_for_applicable_voucher():
    response = client.post(
        "/discounts/validate",
        json={
            "code": "SUPER69",
            "cart_items": CALCULATE_PAYLOAD["cart_items"],
            "customer": CALCULATE_PAYLOAD["customer"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"valid": True}


def test_validate_discount_code_endpoint_false_for_unknown_code():
    response = client.post(
        "/discounts/validate",
        json={
            "code": "DOESNOTEXIST",
            "cart_items": CALCULATE_PAYLOAD["cart_items"],
            "customer": CALCULATE_PAYLOAD["customer"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"valid": False}
