def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_create_and_list_event(client):
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


def test_counts(client):
    for event_type, x in (("a", 1), ("a", 2), ("b", 3)):
        client.post(
            "/events",
            json={"event_type": event_type, "source": "s", "user_id": None, "payload": {"x": x}},
        )

    r = client.get("/analytics/counts?group_by=event_type")
    assert r.status_code == 200
    rows = r.json()["results"]
    counts = {row["key"]: row["count"] for row in rows}
    assert counts["a"] == 2
    assert counts["b"] == 1
