"""Tests for Web Security: Host Header validation (DNS Rebinding), CSRF defense, and Payload Limits."""

from fastapi.testclient import TestClient

from core.main import app

client = TestClient(app)


def test_trusted_host_allows_legitimate_hosts():
    """TrustedHostMiddleware allows localhost, 127.0.0.1, and testserver."""
    # TestClient default host is "testserver"
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # Explicit localhost host
    res_local = client.get("/health", headers={"Host": "localhost"})
    assert res_local.status_code == 200

    # Explicit 127.0.0.1 host
    res_ip = client.get("/health", headers={"Host": "127.0.0.1"})
    assert res_ip.status_code == 200


def test_trusted_host_blocks_dns_rebinding():
    """TrustedHostMiddleware blocks untrusted Host headers (DNS rebinding attack)."""
    res = client.get("/health", headers={"Host": "evil-rebinding.attacker.com"})
    assert res.status_code == 400


def test_csrf_sec_fetch_site_cross_site_blocked():
    """Mutating state-changing requests with Sec-Fetch-Site: cross-site are blocked with 403."""
    # 1. Cross-site POST is blocked
    res_post = client.post(
        "/api/monitor/executions/dummy_id/abort",
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert res_post.status_code == 403
    assert "Cross-site state-changing request blocked" in res_post.json()["detail"]

    # 2. Cross-site DELETE is blocked
    res_del = client.delete(
        "/api/rules/rule_1",
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert res_del.status_code == 403

    # 3. Same-origin or no Sec-Fetch-Site (e.g. non-browser API client or internal dashboard) is allowed past CSRF guard
    res_same = client.post(
        "/api/monitor/executions/dummy_id/abort",
        headers={"Sec-Fetch-Site": "same-origin"},
    )
    # Reaches application route handler (returns 400 for state error, NOT 403 CSRF blocked)
    assert res_same.status_code != 403


def test_request_body_size_limit():
    """Requests exceeding maximum body size return 413 Payload Too Large."""
    # Simulating a 20MB request body Content-Length
    res = client.post(
        "/api/rules",
        headers={"Content-Length": str(20 * 1024 * 1024)},
        content=b"x" * 10,
    )
    assert res.status_code == 413
    assert "Payload too large" in res.json()["detail"]


def test_security_headers_present():
    """Responses include hardened browser security headers."""
    res = client.get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
