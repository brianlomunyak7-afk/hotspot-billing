import os
import sys
import unittest

# conftest.py handles env vars and sys.path

from routes.auth import hash_password, verify_password
from routes.payments import normalize_phone
from mikrotik import duration_to_uptime_limit


class PasswordTests(unittest.TestCase):
    def test_hashes_are_salted(self):
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)

    def test_verify_correct_password(self):
        hashed = hash_password("my-password")
        self.assertTrue(verify_password("my-password", hashed))

    def test_verify_wrong_password(self):
        hashed = hash_password("my-password")
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_verify_malformed_hash(self):
        self.assertFalse(verify_password("anything", "no-dollar-sign"))

    def test_empty_password(self):
        hashed = hash_password("")
        self.assertTrue(verify_password("", hashed))


class PhoneNormalizationTests(unittest.TestCase):
    def test_leading_zero(self):
        self.assertEqual(normalize_phone("0712345678"), "254712345678")

    def test_with_spaces(self):
        self.assertEqual(normalize_phone("0712 345 678"), "254712345678")

    def test_plus_prefix(self):
        self.assertEqual(normalize_phone("+254712345678"), "254712345678")

    def test_already_normalized(self):
        self.assertEqual(normalize_phone("254712345678"), "254712345678")

    def test_invalid_short_number(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            normalize_phone("12345")

    def test_non_digit_after_strip(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            normalize_phone("abcdefghij")


class MikroTikDurationTests(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(duration_to_uptime_limit(30, "minutes"), "30m")

    def test_days(self):
        self.assertEqual(duration_to_uptime_limit(7, "days"), "7d")

    def test_one_minute(self):
        self.assertEqual(duration_to_uptime_limit(1, "minutes"), "1m")

    def test_one_day(self):
        self.assertEqual(duration_to_uptime_limit(1, "days"), "1d")


class ModelImportTests(unittest.TestCase):
    def test_all_models_importable(self):
        from models import Tenant, Package, Subscription, Payment, PendingPayment, Organization, User
        self.assertTrue(hasattr(Tenant, "__tablename__"))
        self.assertTrue(hasattr(Package, "__tablename__"))
        self.assertTrue(hasattr(Subscription, "__tablename__"))
        self.assertTrue(hasattr(Payment, "__tablename__"))
        self.assertTrue(hasattr(PendingPayment, "__tablename__"))
        self.assertTrue(hasattr(Organization, "__tablename__"))
        self.assertTrue(hasattr(User, "__tablename__"))

    def test_organization_has_relationships(self):
        from models import Organization
        self.assertTrue(hasattr(Organization, "tenants"))
        self.assertTrue(hasattr(Organization, "packages"))


class NotificationTests(unittest.TestCase):
    def test_sms_skipped_without_config(self):
        os.environ.pop("TWILIO_ACCOUNT_SID", None)
        os.environ.pop("TWILIO_AUTH_TOKEN", None)
        import notifications
        notifications._client = None
        result = notifications.send_sms("+254700000000", "test")
        self.assertFalse(result)


class CrudImportTests(unittest.TestCase):
    def test_crud_functions_exist(self):
        import crud
        for fn in ("get_tenants", "create_tenant", "get_packages", "create_package",
                    "create_subscription", "expire_subscriptions", "confirm_payment",
                    "fail_payment", "cleanup_stale_payments", "get_expiring_soon"):
            self.assertTrue(callable(getattr(crud, fn, None)), f"{fn} missing from crud")


class RouteImportTests(unittest.TestCase):
    def test_all_route_modules_import(self):
        from routes import auth, packages, payments, subscriptions, tenants
        from routes import dashboard, users, organizations
        for mod in (auth, packages, payments, subscriptions, tenants, dashboard, users, organizations):
            self.assertTrue(hasattr(mod, "router"))


if __name__ == "__main__":
    unittest.main()
