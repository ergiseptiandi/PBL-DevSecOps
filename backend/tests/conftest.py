import os
import sys
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "pbl_devsecops_test.db"

# Set env SEBELUM app di-import.
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["APP_COLOR"] = "blue"
os.environ["APP_VERSION"] = "9.9.9-test"
os.environ["APP_NAME"] = "Task Manager API"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def clean_tasks_table():
    from app.db import SessionLocal
    from app.models import Task

    db = SessionLocal()
    try:
        db.query(Task).delete()
        db.commit()
    finally:
        db.close()
    yield
