"""Check request shape (URLs, auth headers) for the HTTP integrations using a mock transport."""
import httpx

from app import demo
from app.integrations import proxmox, unifi


def _patch(monkeypatch, module, handler):
    def fake_client(cfg, **kw):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw)
    monkeypatch.setattr(module, "client", fake_client)


async def test_unifi_api_key(monkeypatch):
    seen = []

    def handler(req):
        seen.append((req.method, req.url.path, req.headers.get("x-api-key")))
        data = demo.UNIFI_HEALTH if req.url.path.endswith("health") else demo.UNIFI_DEVICES
        return httpx.Response(200, json={"meta": {"rc": "ok"}, "data": data})

    _patch(monkeypatch, unifi, handler)
    d = await unifi.fetch({"url": "https://udm/", "api_key": "k"})
    assert seen == [("GET", "/proxy/network/api/s/default/stat/health", "k"),
                    ("GET", "/proxy/network/api/s/default/stat/device", "k")]
    assert d["clients"]["wireless"] == 31


async def test_unifi_password_login(monkeypatch):
    paths = []

    def handler(req):
        paths.append(req.url.path)
        if req.url.path == "/api/auth/login":
            return httpx.Response(200, json={}, headers={"set-cookie": "TOKEN=abc; Path=/"})
        assert req.headers.get("cookie") == "TOKEN=abc"
        return httpx.Response(200, json={"data": []})

    _patch(monkeypatch, unifi, handler)
    await unifi.fetch({"url": "https://udm", "username": "u", "password": "p", "site": "lab"})
    assert paths[0] == "/api/auth/login" and paths[1] == "/proxy/network/api/s/lab/stat/health"


async def test_proxmox_token_and_ips(monkeypatch):
    def handler(req):
        assert req.headers["authorization"] == "PVEAPIToken=dash@pve!ro=secret"
        p = req.url.path
        if p.endswith("/cluster/resources"):
            return httpx.Response(200, json={"data": demo.PVE_RESOURCES})
        if p.endswith("/lxc/102/interfaces"):
            return httpx.Response(200, json={"data": [{"name": "eth0", "inet": "10.1.1.22/24"}]})
        if p.endswith("/qemu/200/agent/network-get-interfaces"):
            return httpx.Response(200, json={"data": {"result": [
                {"name": "enp0s18", "ip-addresses": [{"ip-address-type": "ipv4", "ip-address": "10.1.1.30"}]}]}})
        return httpx.Response(500, json={"data": None})

    _patch(monkeypatch, proxmox, handler)
    cfg = {"url": "https://pve:8006", "token_id": "dash@pve!ro", "token_secret": "secret"}
    d = await proxmox.fetch(cfg)
    ips = await proxmox.guest_ips(cfg, d["guests"])
    assert ips == {102: "10.1.1.22", 200: "10.1.1.30"}
