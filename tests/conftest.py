import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hotspot.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ADMIN_USERNAME"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "testpass123"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["RATE_LIMIT_PER_MINUTE"] = "9999"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
