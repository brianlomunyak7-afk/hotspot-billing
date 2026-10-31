import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routes.auth import hash_password, verify_password
from routes.payments import normalize_phone
from mikrotik import duration_to_uptime_limit


class CoreBehaviorTests(unittest.TestCase):
    def test_password_hashes_are_salted_and_verifiable(self):
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("correct horse battery staple", first))
        self.assertFalse(verify_password("wrong password", first))

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("0712 345 678"), "254712345678")
        self.assertEqual(normalize_phone("+254712345678"), "254712345678")

    def test_mikrotik_duration_conversion(self):
        self.assertEqual(duration_to_uptime_limit(30, "minutes"), "30m")
        self.assertEqual(duration_to_uptime_limit(7, "days"), "7d")


if __name__ == "__main__":
    unittest.main()
