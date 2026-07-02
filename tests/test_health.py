from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.main import app


def test_live(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_ready_ok(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_ready_returns_503_when_db_unreachable(client):
    bad_engine = create_engine(
        "postgresql+psycopg2://nope:nope@127.0.0.1:1/nope",
        connect_args={"connect_timeout": 1},
    )
    BadSession = sessionmaker(bind=bad_engine)

    def bad_db():
        db = BadSession()
        try:
            yield db
        finally:
            db.close()

    original = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = bad_db
    try:
        r = client.get("/health/ready")
        assert r.status_code == 503
        assert r.json()["status"] == "not ready"
    finally:
        app.dependency_overrides[get_db] = original
