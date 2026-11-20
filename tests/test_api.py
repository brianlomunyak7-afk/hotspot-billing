import os
import sys
import unittest

# conftest.py sets env vars and sys.path before any backend imports

from database import Base, engine
from main import app, bootstrap
from fastapi.testclient import TestClient

Base.metadata.create_all(bind=engine)
bootstrap()

client = TestClient(app, raise_server_exceptions=False)


def get_admin_token():
    res = client.post("/auth/login", json={"username": "testadmin", "password": "testpass123"})
    return res.json()["access_token"]


class HealthTests(unittest.TestCase):
    def test_root(self):
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_health(self):
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")


class AuthTests(unittest.TestCase):
    def test_login_success(self):
        res = client.post("/auth/login", json={"username": "testadmin", "password": "testpass123"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.json())

    def test_login_wrong_password(self):
        res = client.post("/auth/login", json={"username": "testadmin", "password": "wrong"})
        self.assertEqual(res.status_code, 401)

    def test_login_nonexistent_user(self):
        res = client.post("/auth/login", json={"username": "nobody", "password": "whatever"})
        self.assertEqual(res.status_code, 401)

    def test_protected_endpoint_no_token(self):
        res = client.get("/tenants/")
        self.assertEqual(res.status_code, 401)

    def test_protected_endpoint_bad_token(self):
        res = client.get("/tenants/", headers={"Authorization": "Bearer invalid"})
        self.assertEqual(res.status_code, 401)


class DashboardTests(unittest.TestCase):
    def test_stats(self):
        token = get_admin_token()
        res = client.get("/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_tenants", data)
        self.assertIn("total_revenue", data)
        self.assertIn("daily_revenue", data)
        self.assertEqual(len(data["daily_revenue"]), 7)


class PackageTests(unittest.TestCase):
    def test_create_and_list_package(self):
        token = get_admin_token()
        res = client.post("/packages/", json={"name": "Test 30min", "duration_days": 30, "price": 50, "duration_type": "minutes"},
                          headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        pkg_id = res.json()["id"]

        res = client.get("/packages/")
        self.assertEqual(res.status_code, 200)
        names = [p["name"] for p in res.json()]
        self.assertIn("Test 30min", names)

        res = client.put(f"/packages/{pkg_id}", json={"name": "Test 60min", "duration_days": 60, "price": 80, "duration_type": "minutes"},
                         headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Test 60min")

    def test_delete_package(self):
        token = get_admin_token()
        res = client.post("/packages/", json={"name": "ToDelete", "duration_days": 1, "price": 10, "duration_type": "days"},
                          headers={"Authorization": f"Bearer {token}"})
        pkg_id = res.json()["id"]
        res = client.delete(f"/packages/{pkg_id}", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)


class TenantTests(unittest.TestCase):
    def test_list_tenants_paginated(self):
        token = get_admin_token()
        res = client.get("/tenants/?limit=10&offset=0", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_search_tenants(self):
        token = get_admin_token()
        res = client.get("/tenants/?search=nonexistent", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total"], 0)

    def test_public_tenant_lookup(self):
        res = client.get("/tenants/public?phone=254000000000")
        self.assertEqual(res.status_code, 200)

    def test_public_status_check(self):
        res = client.get("/tenants/public/status?phone=254000000000")
        self.assertEqual(res.status_code, 200)
        self.assertIn("found", res.json())


class UserManagementTests(unittest.TestCase):
    def test_list_users(self):
        token = get_admin_token()
        res = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()) >= 1)

    def test_create_and_delete_user(self):
        token = get_admin_token()
        res = client.post("/users/", json={"username": "newuser2", "password": "pass123", "role": "viewer"},
                          headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 201)
        user_id = res.json()["id"]

        res = client.delete(f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)

    def test_create_duplicate_user(self):
        token = get_admin_token()
        client.post("/users/", json={"username": "dupuser2", "password": "pass123", "role": "admin"},
                    headers={"Authorization": f"Bearer {token}"})
        res = client.post("/users/", json={"username": "dupuser2", "password": "pass123", "role": "admin"},
                          headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 409)

    def test_change_password(self):
        token = get_admin_token()
        res = client.put("/users/me/password", json={"current_password": "testpass123", "new_password": "newpass456"},
                         headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        new_token_res = client.post("/auth/login", json={"username": "testadmin", "password": "newpass456"})
        new_token = new_token_res.json()["access_token"]
        client.put("/users/me/password", json={"current_password": "newpass456", "new_password": "testpass123"},
                   headers={"Authorization": f"Bearer {new_token}"})

    def test_change_password_wrong_current(self):
        token = get_admin_token()
        res = client.put("/users/me/password", json={"current_password": "wrongpass", "new_password": "newpass456"},
                         headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 400)


class OrganizationTests(unittest.TestCase):
    def test_get_profile(self):
        token = get_admin_token()
        res = client.get("/organizations/profile", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("name", res.json())

    def test_update_profile(self):
        token = get_admin_token()
        res = client.put("/organizations/profile", json={"name": "Updated Hotspot"},
                         headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Updated Hotspot")


class SubscriptionTests(unittest.TestCase):
    def test_list_subscriptions(self):
        token = get_admin_token()
        res = client.get("/subscriptions/?limit=10&offset=0", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_expiring_soon(self):
        token = get_admin_token()
        res = client.get("/subscriptions/expiring", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)


class PaymentTests(unittest.TestCase):
    def test_list_payments_paginated(self):
        token = get_admin_token()
        res = client.get("/payments/all?limit=10&offset=0", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_payment_status_unknown(self):
        res = client.get("/payments/status/unknown-checkout-id")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "pending")


def tearDownModule():
    for f in ("test_hotspot.db", "test_api.db", "test_temp.db"):
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    unittest.main()
