import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from fastapi.testclient import TestClient

# Configure test database path before importing app
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ewaste.db")
os.environ["EWASTE_DB_PATH"] = TEST_DB_PATH

from main import app
from database import init_db
import crud

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure database schema is ready and table is clean before each test."""
    init_db()
    crud.clear_all_requests()
    yield
    crud.clear_all_requests()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


def test_health_and_categories():
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json() == {"status": "healthy"}

    r_cats = client.get("/api/categories")
    assert r_cats.status_code == 200
    cats = r_cats.json()["categories"]
    assert "Mobile Phones" in cats
    assert "Laptops" in cats


def test_create_request_success():
    payload = {
        "full_name": "Aditya Verma",
        "email": "aditya.v@example.com",
        "phone": "+91 98765 12345",
        "address": "45 Lakeview Residency, Sector 5",
        "city": "Pune",
        "pincode": "411001",
        "category": "Laptops",
        "item_description": "HP Pavilion 14-inch, broken screen, no power adapter",
        "quantity": 1,
        "condition": "Semi-functional",
        "preferred_date": "2026-10-20",
        "special_notes": "Please call before arriving"
    }

    response = client.post("/api/requests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["tracking_id"].startswith("EW-")
    assert data["full_name"] == "Aditya Verma"
    assert data["status"] == "Pending"
    assert data["quantity"] == 1


def test_create_request_validation():
    # Missing required field full_name
    bad_payload = {
        "email": "invalid-email",
        "phone": "123",
        "address": "Short",
        "city": "P",
        "pincode": "1",
        "category": "Laptops",
        "item_description": "X",
        "quantity": 0,
        "condition": "Unknown",
        "preferred_date": "2026-10-20"
    }
    response = client.post("/api/requests", json=bad_payload)
    assert response.status_code == 422


def test_get_and_filter_requests():
    # Create two requests
    r1 = client.post("/api/requests", json={
        "full_name": "Sunita Rao",
        "email": "sunita@example.com",
        "phone": "+91 99887 76655",
        "address": "101 Green Avenue",
        "city": "Hyderabad",
        "pincode": "500001",
        "category": "Mobile Phones",
        "item_description": "Redmi Note 9 with swollen battery",
        "quantity": 2,
        "condition": "Non-functional / Scrap",
        "preferred_date": "2026-10-22",
    }).json()

    r2 = client.post("/api/requests", json={
        "full_name": "Karan Mehra",
        "email": "karan@example.com",
        "phone": "+91 91234 56789",
        "address": "304 Blue Ridge, Hinjewadi",
        "city": "Pune",
        "pincode": "411057",
        "category": "Televisions",
        "item_description": "Old LG CRT Television 21 inch",
        "quantity": 1,
        "condition": "Semi-functional",
        "preferred_date": "2026-10-25",
    }).json()

    # List all
    res = client.get("/api/requests")
    assert res.status_code == 200
    assert len(res.json()["requests"]) == 2

    # Filter by category
    res_cat = client.get("/api/requests?category=Mobile%20Phones")
    assert len(res_cat.json()["requests"]) == 1
    assert res_cat.json()["requests"][0]["category"] == "Mobile Phones"

    # Search by city or customer name
    res_search = client.get("/api/requests?search=Hinjewadi")
    assert len(res_search.json()["requests"]) == 1
    assert res_search.json()["requests"][0]["full_name"] == "Karan Mehra"


def test_update_request_status():
    created = client.post("/api/requests", json={
        "full_name": "Divya Nair",
        "email": "divya@example.com",
        "phone": "+91 98450 11223",
        "address": "77 Palm Boulevard",
        "city": "Kochi",
        "pincode": "682001",
        "category": "Batteries",
        "item_description": "Lead-acid inverter battery 150Ah",
        "quantity": 1,
        "condition": "Non-functional / Scrap",
        "preferred_date": "2026-10-18",
    }).json()

    req_id = created["id"]

    # Update to Scheduled
    patch_res = client.patch(f"/api/requests/{req_id}/status", json={"status": "Scheduled"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Scheduled"

    # Update to Collected
    patch_res2 = client.patch(f"/api/requests/{req_id}/status", json={"status": "Collected"})
    assert patch_res2.status_code == 200
    assert patch_res2.json()["status"] == "Collected"

    # Invalid status
    bad_res = client.patch(f"/api/requests/{req_id}/status", json={"status": "ShippedToMars"})
    assert bad_res.status_code == 422


def test_delete_and_not_found():
    created = client.post("/api/requests", json={
        "full_name": "Ravi Teja",
        "email": "ravi@example.com",
        "phone": "+91 97000 88990",
        "address": "B-12 Jubilee Hills",
        "city": "Hyderabad",
        "pincode": "500033",
        "category": "Computers",
        "item_description": "Keyboards and mouse scrap lot",
        "quantity": 5,
        "condition": "Non-functional / Scrap",
        "preferred_date": "2026-10-21",
    }).json()

    req_id = created["id"]

    # Delete
    del_res = client.delete(f"/api/requests/{req_id}")
    assert del_res.status_code == 200

    # Verify not found
    get_res = client.get(f"/api/requests/{req_id}")
    assert get_res.status_code == 404


def test_dashboard_stats():
    # Seed sample requests
    client.post("/api/requests", json={
        "full_name": "User 1",
        "email": "u1@example.com",
        "phone": "9876543210",
        "address": "Addr 1",
        "city": "City 1",
        "pincode": "111111",
        "category": "Laptops",
        "item_description": "Laptop 1",
        "quantity": 1,
        "condition": "Working",
        "preferred_date": "2026-10-16",
    })

    client.post("/api/requests", json={
        "full_name": "User 2",
        "email": "u2@example.com",
        "phone": "9876543211",
        "address": "Addr 2",
        "city": "City 2",
        "pincode": "222222",
        "category": "Laptops",
        "item_description": "Laptop 2",
        "quantity": 2,
        "condition": "Semi-functional",
        "preferred_date": "2026-10-17",
    })

    stats_res = client.get("/api/dashboard/stats")
    assert stats_res.status_code == 200
    data = stats_res.json()
    assert data["total_requests"] == 2
    assert data["pending"] == 2
    assert data["scheduled"] == 0
    assert data["category_counts"]["Laptops"] == 2


def test_demo_data_endpoints():
    seed_res = client.post("/api/demo/seed")
    assert seed_res.status_code == 200
    assert seed_res.json()["count"] > 0

    stats = client.get("/api/dashboard/stats").json()
    assert stats["total_requests"] > 0

    clear_res = client.post("/api/demo/clear")
    assert clear_res.status_code == 200

    stats_after = client.get("/api/dashboard/stats").json()
    assert stats_after["total_requests"] == 0


def test_auth_login_and_roles():
    # Admin login
    admin_login = client.post("/api/auth/login", json={"email": "admin@ewaste.com", "password": "admin123"})
    assert admin_login.status_code == 200
    admin_data = admin_login.json()
    assert "token" in admin_data
    assert admin_data["user"]["role"] == "admin"
    admin_token = admin_data["token"]

    # Verify /api/auth/me for admin
    me_admin = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me_admin.status_code == 200
    assert me_admin.json()["role"] == "admin"

    # User login
    user_login = client.post("/api/auth/login", json={"email": "user@ewaste.com", "password": "user123"})
    assert user_login.status_code == 200
    user_data = user_login.json()
    assert user_data["user"]["role"] == "user"

    # Invalid login
    bad_login = client.post("/api/auth/login", json={"email": "admin@ewaste.com", "password": "wrongpassword"})
    assert bad_login.status_code == 401


def test_user_role_permissions_and_scoping():
    # 1. Create a request from another customer
    r_other = client.post("/api/requests", json={
        "full_name": "Other User",
        "email": "other@example.com",
        "phone": "+91 99887 76655",
        "address": "404 Nowhere St",
        "city": "Mumbai",
        "pincode": "400001",
        "category": "Laptops",
        "item_description": "Old Laptop",
        "quantity": 1,
        "condition": "Working",
        "preferred_date": "2026-10-25"
    }).json()
    other_id = r_other["id"]

    # 2. Create a request for the demo user
    client.post("/api/requests", json={
        "full_name": "Demo Resident",
        "email": "user@ewaste.com",
        "phone": "+91 91234 56789",
        "address": "12 User Colony",
        "city": "Bengaluru",
        "pincode": "560001",
        "category": "Mobile Phones",
        "item_description": "Old Smartphone",
        "quantity": 1,
        "condition": "Semi-functional",
        "preferred_date": "2026-10-26"
    })

    # Log in as regular user
    user_res = client.post("/api/auth/login", json={"email": "user@ewaste.com", "password": "user123"}).json()
    user_token = user_res["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # User requests should ONLY return user@ewaste.com's requests
    user_requests = client.get("/api/requests", headers=user_headers).json()["requests"]
    assert len(user_requests) == 1
    assert user_requests[0]["email"] == "user@ewaste.com"

    # User dashboard stats should be scoped to 1 request
    user_stats = client.get("/api/dashboard/stats", headers=user_headers).json()
    assert user_stats["total_requests"] == 1

    # Regular user CANNOT update status (403 Forbidden)
    status_attempt = client.patch(f"/api/requests/{other_id}/status", json={"status": "Scheduled"}, headers=user_headers)
    assert status_attempt.status_code == 403

    # Regular user CANNOT delete request (403 Forbidden)
    delete_attempt = client.delete(f"/api/requests/{other_id}", headers=user_headers)
    assert delete_attempt.status_code == 403

    # Regular user CANNOT seed demo data (403 Forbidden)
    seed_attempt = client.post("/api/demo/seed", headers=user_headers)
    assert seed_attempt.status_code == 403

    # User logout
    logout_res = client.post("/api/auth/logout", headers=user_headers)
    assert logout_res.status_code == 200

    # Token now invalid
    me_after = client.get("/api/auth/me", headers=user_headers)
    assert me_after.status_code == 401


def test_auth_signup_flow():
    # 1. Successful resident user registration
    payload = {
        "full_name": "Kavita Reddy",
        "email": "kavita.reddy@example.com",
        "password": "mypassword123"
    }
    signup_res = client.post("/api/auth/signup", json=payload)
    assert signup_res.status_code == 201
    data = signup_res.json()
    assert "token" in data
    assert data["user"]["full_name"] == "Kavita Reddy"
    assert data["user"]["email"] == "kavita.reddy@example.com"
    assert data["user"]["role"] == "user"  # Role is strictly resident user

    # 2. Duplicate registration attempt with same email
    dup_res = client.post("/api/auth/signup", json=payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 3. Registration with password too short (< 6 chars)
    short_res = client.post("/api/auth/signup", json={
        "full_name": "Test Short",
        "email": "short@example.com",
        "password": "123"
    })
    assert short_res.status_code == 422

    # 4. Login with the newly registered user credentials
    login_res = client.post("/api/auth/login", json={
        "email": "kavita.reddy@example.com",
        "password": "mypassword123"
    })
    assert login_res.status_code == 200
    assert login_res.json()["user"]["role"] == "user"
