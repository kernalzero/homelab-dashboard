import importlib

from fastapi.testclient import TestClient


def test_demo_state(monkeypatch):
    monkeypatch.setenv("DASHBOARD_DEMO", "1")
    import app.main as main
    importlib.reload(main)
    with TestClient(main.app) as c:
        assert c.get("/healthz").json() == {"ok": True}
        assert "<title>" in c.get("/").text
        s = c.get("/api/state").json()
    assert set(s["integrations"]) == {"unifi", "proxmox", "truenas"}
    assert "_ips" not in s["integrations"]["proxmox"]["data"]
    groups = {x["group"] for x in s["services"]}
    assert groups == {"Infrastructure", "TrueNAS apps", "Proxmox guests"}
    assert any(x["health"] and x["health"]["up"] for x in s["services"])


def test_unconfigured_starts_cleanly(monkeypatch, tmp_path):
    monkeypatch.delenv("DASHBOARD_DEMO", raising=False)
    monkeypatch.setenv("DASHBOARD_CONFIG", str(tmp_path / "missing.yaml"))
    import app.main as main
    importlib.reload(main)
    with TestClient(main.app) as c:
        s = c.get("/api/state").json()
    assert s["integrations"] == {}
