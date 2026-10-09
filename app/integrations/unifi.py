"""UniFi OS console (UDM Pro) via the local Network application API.

Auth: an API key (Settings > Control Plane > Integrations, Network 9.0+), or a
local-only read-only admin's username/password as a fallback.
"""
from .common import client

DEVICE_TYPES = {"udm": "Gateway", "ugw": "Gateway", "uxg": "Gateway", "usw": "Switch", "uap": "Access point"}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse(health: list[dict], devices: list[dict]) -> dict:
    sub = {h.get("subsystem"): h for h in health}
    wan, www, wlan, lan = (sub.get(k, {}) for k in ("wan", "www", "wlan", "lan"))
    gw_stats = wan.get("gw_system-stats", {})

    devs = []
    for d in devices:
        stats = d.get("system-stats", {})
        devs.append({
            "name": d.get("name") or d.get("model") or d.get("mac"),
            "model": d.get("model"),
            "type": DEVICE_TYPES.get(d.get("type"), d.get("type")),
            "ip": d.get("ip"),
            "online": d.get("state") == 1,
            "uptime": d.get("uptime"),
            "clients": d.get("num_sta", 0),
            "cpu": _num(stats.get("cpu")),
            "mem": _num(stats.get("mem")),
            "upgradable": bool(d.get("upgradable")),
        })
    devs.sort(key=lambda d: (d["online"], d["type"] or "", d["name"] or ""))

    return {
        "wan": {
            "status": wan.get("status", "unknown"),
            "ip": wan.get("wan_ip"),
            "isp": wan.get("isp_name"),
            "rx_bps": (wan.get("rx_bytes-r") or 0) * 8,
            "tx_bps": (wan.get("tx_bytes-r") or 0) * 8,
            "latency_ms": www.get("latency"),
            "speedtest_down_mbps": www.get("xput_down"),
            "speedtest_up_mbps": www.get("xput_up"),
            "speedtest_at": www.get("speedtest_lastrun"),
        },
        "gateway": {"cpu": _num(gw_stats.get("cpu")), "mem": _num(gw_stats.get("mem"))},
        "clients": {
            "wired": lan.get("num_user", 0),
            "wireless": wlan.get("num_user", 0),
            "guest": wlan.get("num_guest", 0) + lan.get("num_guest", 0),
        },
        "devices": devs,
        "devices_offline": sum(1 for d in devs if not d["online"]),
        "updates_available": sum(1 for d in devs if d["upgradable"]),
    }


async def fetch(cfg: dict) -> dict:
    base = cfg["url"].rstrip("/")
    site = cfg.get("site", "default")
    headers = {"X-API-KEY": cfg["api_key"]} if cfg.get("api_key") else {}
    async with client(cfg, headers=headers) as c:
        if not headers:
            r = await c.post(f"{base}/api/auth/login",
                             json={"username": cfg["username"], "password": cfg["password"]})
            r.raise_for_status()
        api = f"{base}/proxy/network/api/s/{site}"
        health = (await c.get(f"{api}/stat/health")).raise_for_status().json()["data"]
        devices = (await c.get(f"{api}/stat/device")).raise_for_status().json()["data"]
    return parse(health, devices)
