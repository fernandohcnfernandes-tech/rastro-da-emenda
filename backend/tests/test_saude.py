from fastapi.testclient import TestClient

from rastro.api.main import app


def test_saude() -> None:
    resp = TestClient(app).get("/saude")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
