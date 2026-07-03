from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import TelemetryEvent


def _token(client: TestClient, username: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": "demo1234"})
    assert r.status_code == 200
    return r.json()["token"]


def _cleanup() -> None:
    with SessionLocal() as db:
        db.query(TelemetryEvent).delete()
        db.commit()


def test_ingest_valid_and_invalid_event():
    _cleanup()
    try:
        with TestClient(app) as client:
            h = {"Authorization": f"Bearer {_token(client, 'editor')}"}
            ok = client.post("/api/telemetry", json={"eventType": "dismiss", "variantId": "v3", "position": 3}, headers=h)
            assert ok.status_code == 200 and ok.json()["ok"] is True
            with SessionLocal() as db:
                assert db.query(TelemetryEvent).count() == 1

            bad = client.post("/api/telemetry", json={"eventType": "nonsense"}, headers=h)
            assert bad.status_code == 422
    finally:
        _cleanup()


def test_confirm_records_adopt_and_summary():
    _cleanup()
    try:
        with TestClient(app) as client:
            eh = {"Authorization": f"Bearer {_token(client, 'editor')}"}
            r = client.post("/api/variants/v1/confirm", headers=eh)
            assert r.status_code == 200 and r.json()["ok"] is True
            client.post("/api/variants/v1/confirm", headers=eh)  # adopt v1 twice
            client.post("/api/variants/v2/confirm", headers=eh)

            # 未知变体 -> 404
            assert client.post("/api/variants/nope/confirm", headers=eh).status_code == 404

            # summary 仅管理员
            assert client.get("/api/telemetry/summary", headers=eh).status_code == 403
            ah = {"Authorization": f"Bearer {_token(client, 'admin')}"}
            s = client.get("/api/telemetry/summary", headers=ah).json()
            assert s["total"] == 3
            assert {"eventType": "adopt", "count": 3} in s["byType"]
            # v1 采用 2 次应排在最前
            assert s["topAdopted"][0] == {"variantId": "v1", "count": 2}
    finally:
        _cleanup()
