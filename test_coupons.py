import os
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base

# Load environment so TEST_DATABASE_URL can be read from .env
load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set. "
        "Create a Postgres test DB and set TEST_DATABASE_URL in your .env, e.g.\n"
        'TEST_DATABASE_URL=postgresql+psycopg://coupons_user:StrongPassword@localhost:5432/coupons_test'
    )

# Postgres engine for tests
engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the app's DB dependency to use the test engine/session
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Fresh schema for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_cart_wise_coupon():
    """Test creating a cart-wise coupon"""
    coupon_data = {
        "type": "cart-wise",
        "details": {
            "threshold": 100,
            "discount": 10,
            "discount_type": "percentage"
        }
    }

    response = client.post("/coupons", json=coupon_data)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "cart-wise"
    assert data["details"]["threshold"] == 100
    assert data["details"]["discount"] == 10


def test_create_product_wise_coupon():
    """Test creating a product-wise coupon"""
    coupon_data = {
        "type": "product-wise",
        "details": {
            "product_id": 1,
            "discount": 20,
            "discount_type": "percentage"
        }
    }

    response = client.post("/coupons", json=coupon_data)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "product-wise"
    assert data["details"]["product_id"] == 1


def test_create_bxgy_coupon():
    """Test creating a BxGy coupon"""
    coupon_data = {
        "type": "bxgy",
        "details": {
            "buy_products": [
                {"product_id": 1, "quantity": 3},
                {"product_id": 2, "quantity": 3}
            ],
            "get_products": [
                {"product_id": 3, "quantity": 1}
            ],
            "repetition_limit": 2
        }
    }

    response = client.post("/coupons", json=coupon_data)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "bxgy"
    assert len(data["details"]["buy_products"]) == 2


def test_get_coupons():
    """Test getting all coupons"""
    # First create a coupon
    coupon_data = {
        "type": "cart-wise",
        "details": {
            "threshold": 100,
            "discount": 10,
            "discount_type": "percentage"
        }
    }
    client.post("/coupons", json=coupon_data)

    # Then get all coupons
    response = client.get("/coupons")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_apply_cart_wise_coupon():
    """Test applying a cart-wise coupon"""
    # Create coupon
    coupon_data = {
        "type": "cart-wise",
        "details": {
            "threshold": 100,
            "discount": 10,
            "discount_type": "percentage"
        }
    }
    coupon_response = client.post("/coupons", json=coupon_data)
    assert coupon_response.status_code == 201
    coupon_id = coupon_response.json()["id"]

    # Create cart
    cart_data = {
            "items": [
                {"product_id": 1, "quantity": 2, "price": 50},
                {"product_id": 2, "quantity": 1, "price": 100}
            ]

    }

    # Apply coupon
    response = client.post(f"/apply-coupon/{coupon_id}", json=cart_data)
    assert response.status_code == 200
    data = response.json()
    assert data["updated_cart"]["total_discount"] == 20.0  # 10% of 200
    assert data["updated_cart"]["final_price"] == 180.0


def test_applicable_coupons():
    """Test getting applicable coupons for a cart"""
    # Create cart-wise coupon
    coupon_data = {
        "type": "cart-wise",
        "details": {
            "threshold": 100,
            "discount": 10,
            "discount_type": "percentage"
        }
    }
    client.post("/coupons", json=coupon_data)

    # Test with cart above threshold
    cart_data = {
        "items": [
            {"product_id": 1, "quantity": 2, "price": 60}
        ]
    }

    response = client.post("/applicable-coupons", json=cart_data)
    assert response.status_code == 200
    data = response.json()
    assert "applicable_coupons" in data
    assert len(data["applicable_coupons"]) >= 1


def test_invalid_coupon_type():
    """Test creating coupon with invalid type"""
    coupon_data = {
        "type": "invalid-type",
        "details": {
            "threshold": 100,
            "discount": 10
        }
    }

    response = client.post("/coupons", json=coupon_data)
    # Service rejects unsupported type with HTTP 400
    assert response.status_code == 400


def test_coupon_not_found():
    """Test getting non-existent coupon"""
    response = client.get("/coupons/999999")
    assert response.status_code == 404


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
