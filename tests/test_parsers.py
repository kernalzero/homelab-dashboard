from app import catalog, demo, services
from app.config import load_config
from app.integrations import proxmox, truenas, unifi


def test_config_expands_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PVE_SECRET", "abc")
    p = tmp_path / "c.yaml"
    p.write_text("proxmox:\n  token_secret: ${PVE_SECRET}\n  other: ${MISSING:-fallback}\n")
    cfg = load_config(str(p))
    assert cfg["proxmox"] == {"token_secret": "abc", "other": "fallback"}


def test_missing_config_is_empty(tmp_path):
    assert load_config(str(tmp_path / "nope.yaml")) == {}


def test_unifi_parse():
    d = unifi.parse(demo.UNIFI_HEALTH, demo.UNIFI_DEVICES)
    assert d["wan"]["status"] == "ok"
    assert d["wan"]["rx_bps"] == 4_850_000 * 8
    assert d["clients"] == {"wired": 22, "wireless": 31, "guest": 2}
    assert d["devices_offline"] == 1
    assert d["devices"][0]["name"] == "Coop AP"  # offline devices sort first
    assert d["updates_available"] == 1
    assert d["gateway"]["cpu"] == 18.2


def test_unifi_parse_empty():
    d = unifi.parse([], [])
    assert d["wan"]["status"] == "unknown" and d["devices"] == []


def test_proxmox_parse():
    d = proxmox.parse(demo.PVE_RESOURCES)
    assert [n["name"] for n in d["nodes"]] == ["pve1", "pve2"]
    assert d["nodes"][0]["cpu"] == 21.0
    assert all(g["name"] != "ubuntu-template" for g in d["guests"])  # templates hidden
    assert d["running"] == 6 and d["stopped"] == 1
    assert d["guests"][-1]["name"] == "win11-lab"  # stopped last
    names = [s["name"] for s in d["storage"]]
    assert names.count("truenas-nfs") == 1 and names.count("local-lvm") == 2
    assert d["guests"][0]["tags"] == ["dns", "core"]


def test_proxmox_first_ipv4():
    assert proxmox._first_ipv4([{"name": "lo", "inet": "127.0.0.1/8"},
                                {"name": "eth0", "inet": "10.0.0.5/24"}]) == "10.0.0.5"
    agent = [{"name": "lo", "ip-addresses": [{"ip-address-type": "ipv4", "ip-address": "127.0.0.1"}]},
             {"name": "ens18", "ip-addresses": [{"ip-address-type": "ipv6", "ip-address": "fe80::1"},
                                               {"ip-address-type": "ipv4", "ip-address": "10.0.0.9"}]}]
    assert proxmox._first_ipv4(agent) == "10.0.0.9"


def test_truenas_parse():
    d = truenas.parse(demo.TN_INFO, demo.TN_POOLS, demo.TN_DATASETS, demo.TN_ALERTS,
                      demo.TN_APPS, demo.TN_REPL, "nas.lan")
    tank = d["pools"][0]
    assert tank["name"] == "tank" and tank["healthy"]
    assert 48 < tank["pct"] < 49  # usable space from root dataset, not raw vdev size
    assert tank["scan_end"] is not None
    assert len(d["alerts"]) == 1 and d["alerts"][0]["level"] == "WARNING"  # INFO filtered
    plex = next(a for a in d["apps"] if a["name"] == "plex")
    assert plex["url"] == "http://nas.lan:32400/web" and plex["update"]
    assert d["replications"][0]["state"] == "SUCCESS"


def test_truenas_pool_without_dataset_falls_back_to_raw():
    d = truenas.parse({}, [{"name": "p", "size": 100, "allocated": 25, "healthy": True}], [], [], [], [], None)
    assert d["pools"][0]["pct"] == 25.0


def test_catalog_match():
    assert catalog.match("jellyfin")[0] == "jellyfin"
    assert catalog.match("lxc-Jellyseerr-01")[0] == "jellyseerr"
    assert catalog.match("Home-Assistant")[0] == "homeassistant"
    assert catalog.match("nginx-proxy-manager")[0] == "nginxproxymanager"
    assert catalog.match("win11-lab") is None


def test_services_discovery_and_merge():
    pve = proxmox.parse(demo.PVE_RESOURCES)
    discovered = services.from_proxmox(pve, demo.PVE_IPS)
    jf = next(s for s in discovered if s["name"] == "jellyfin")
    assert jf["url"] == "http://192.168.10.22:8096" and jf["icon"] == "jellyfin"
    pihole = next(s for s in discovered if s["name"] == "pihole")
    assert pihole["url"] == "http://192.168.10.21/admin"
    assert next(s for s in discovered if s["name"] == "win11-lab")["url"] is None

    configured = services.from_config({"services": [{"group": "Media", "items": [
        {"name": "Jellyfin", "url": "https://jf.home.arpa"}]}]})
    merged = services.merge(configured, discovered)
    assert sum(1 for s in merged if s["name"].lower() == "jellyfin") == 1
    assert merged[0]["source"] == "config"
