def test_metrics_exposes_request_and_pool_metrics(client):
    client.get("/health")

    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")

    body = r.text
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in body
    assert "http_request_duration_seconds_bucket" in body
    assert "http_requests_in_progress" in body
    assert "db_pool_size" in body
    assert "db_pool_checked_out" in body


def test_metrics_endpoint_is_not_self_instrumented(client):
    client.get("/metrics")

    r = client.get("/metrics")
    assert 'path="/metrics"' not in r.text


def test_unmatched_routes_use_bounded_label(client):
    client.get("/does-not-exist-12345")

    r = client.get("/metrics")
    assert 'path="unmatched",status="404"' in r.text
    assert "does-not-exist-12345" not in r.text
