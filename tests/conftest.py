import os
from pathlib import Path


os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DB_DRIVER", "sqlite")
os.environ.setdefault("TEST_DB_PATH", "/tmp/wepay_pytest.sqlite3")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALLOW_EMAIL_TEST", "false")

path = Path(os.environ["TEST_DB_PATH"])
if path.exists():
    path.unlink()
