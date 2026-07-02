import os

# Must be set before app modules are imported: the engine is created at import time.
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://app:app@localhost:5433/events_test",
)
os.environ.setdefault("DATABASE_URL", os.environ["TEST_DATABASE_URL"])

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app

engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
