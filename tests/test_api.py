import base64
import pytest
from fastapi.testclient import TestClient
from cert_issuer_service import app as app_module, service
from cert_issuer_service.settings import Settings, get_settings

PDF = base64.b64encode(b"%PDF-1.7\nfake certificate").decode()
H = {"X-API-Key": "test-key"}


@pytest.fixture
def client(monkeypatch):
    fake_cids = iter(f"bafy{i}" for i in range(100))
    calls = []
    def fake_add(name, data, url, pin=True):
        calls.append(url)
        return next(fake_cids)
    monkeypatch.setattr(service, "add_bytes", fake_add)
    with TestClient(app_module.app) as c:
        c.ipfs_calls = calls
        yield c
    app_module.app.dependency_overrides.clear()


def test_rejects_missing_or_wrong_key(client):
    assert client.post("/wallets", json={}).status_code == 401
    assert client.post("/wallets", json={}, headers={"X-API-Key": "nope"}).status_code == 401


def test_fails_closed_without_server_key(client):
    app_module.app.dependency_overrides[get_settings] = lambda: Settings(api_key=None)
    assert client.post("/wallets", json={}, headers=H).status_code == 503


def test_wallet_create_and_export(client):
    r = client.post("/wallets", json={"student_ref": "S1"}, headers=H)
    assert r.status_code == 200
    addr = r.json()["address"]
    ks = client.post(f"/wallets/{addr}/export", json={"new_password": "longpass"}, headers=H)
    assert ks.status_code == 200 and "crypto" in ks.json()["keystore_json"]


def test_prepare_issue(client):
    body = {"holder_name": "Jane Doe", "degree_name": "BSc", "issued_date": "2025-11-30",
            "issuer_id": "did:example:uni", "pdf_b64": PDF, "wallet_mode": "generate"}
    r = client.post("/prepare-issue", json=body, headers=H)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["tokenURI"] == f"ipfs://{out['metadata_cid']}"
    assert out["manifestHash"].startswith("0x")


def test_no_server_file_read_and_no_caller_chosen_ipfs(client):
    body = {"holder_name": "X", "degree_name": "Y", "issued_date": "2025-01-01",
            "issuer_id": "Z", "pdf_path": "/etc/passwd", "ipfs_api_url": "http://169.254.169.254",
            "pdf_b64": PDF, "wallet_mode": "generate"}
    r = client.post("/prepare-issue", json=body, headers=H)
    assert r.status_code == 200
    assert all("169.254" not in u for u in client.ipfs_calls)


def test_rejects_non_pdf(client):
    body = {"holder_name": "X", "degree_name": "Y", "issued_date": "2025-01-01", "issuer_id": "Z",
            "pdf_b64": base64.b64encode(b"not a pdf").decode(), "wallet_mode": "generate"}
    assert client.post("/prepare-issue", json=body, headers=H).status_code == 400
