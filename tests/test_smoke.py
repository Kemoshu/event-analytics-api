import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://app:app@db_test:5432/events_test"
)

engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_create_and_list_event():
    payload = {
        "event_type": "robot.menu.updated",
        "source": "admin-panel",
        "user_id": "kevin",
        "payload": {"menuId": "coffee-01", "changes": 2},
    }

    r = client.post("/events", json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["event_type"] == "robot.menu.updated"

    r2 = client.get("/events?limit=10&offset=0")
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 1
    assert items[0]["id"] == created["id"]

def test_counts():
    client.post("/events", json={"event_type":"a","source":"s","user_id":None,"payload":{"x":1}})
    client.post("/events", json={"event_type":"a","source":"s","user_id":None,"payload":{"x":2}})
    client.post("/events", json={"event_type":"b","source":"s","user_id":None,"payload":{"x":3}})

    r = client.get("/analytics/counts?group_by=event_type")
    assert r.status_code == 200
    rows = r.json()["results"]
    counts = {row["key"]: row["count"] for row in rows}
    assert counts["a"] == 2
    assert counts["b"] == 1
