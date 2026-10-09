"""TrueNAS SCALE / Community Edition.

Default transport is the JSON-RPC 2.0 websocket API (wss://host/api/current),
which replaced the REST API in 25.04. Set `api: rest` for 24.x systems.
Auth: an API key belonging to a user with the read-only admin role.
"""
import itertools
import json
import ssl
from urllib.parse import urlparse

import websockets

from .common import client, pct

ALERT_LEVELS = ["INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY"]


def _ts(v):
    """TrueNAS dates arrive as {"$date": ms}; return epoch seconds."""
    if isinstance(v, dict) and "$date" in v:
        return v["$date"] / 1000
    return v


def _parsed(v):
    return v.get("parsed") if isinstance(v, dict) else v


def parse(info, pools, datasets, alerts, apps, replications, host):
    usage = {d.get("id") or d.get("name"): d for d in datasets}
    out_pools = []
    for p in pools:
        ds = usage.get(p["name"])
        if ds:
            used, avail = _parsed(ds.get("used")) or 0, _parsed(ds.get("available")) or 0
            total = used + avail
        else:
            used, total = p.get("allocated") or 0, p.get("size") or 0
        scan = p.get("scan") or {}
        out_pools.append({
            "name": p["name"],
            "status": p.get("status"),
            "healthy": bool(p.get("healthy")),
            "used": used,
            "total": total,
            "pct": pct(used, total),
            "scan": scan.get("function"),
            "scan_state": scan.get("state"),
            "scan_end": _ts(scan.get("end_time")),
            "scan_errors": scan.get("errors") or 0,
        })

    min_level = ALERT_LEVELS.index("WARNING")
    out_alerts = [
        {"level": a.get("level"), "text": a.get("formatted") or a.get("text"), "at": _ts(a.get("datetime"))}
        for a in alerts
        if not a.get("dismissed")
        and a.get("level") in ALERT_LEVELS
        and ALERT_LEVELS.index(a["level"]) >= min_level
    ]

    out_apps = []
    for a in apps:
        portals = a.get("portals") or {}
        url = next(iter(portals.values()), None)
        if url and host:
            # Portals are reported against 0.0.0.0; point them at the NAS.
            url = url.replace("0.0.0.0", host)
        meta = a.get("metadata") or {}
        out_apps.append({
            "name": a.get("name"),
            "title": meta.get("title") or a.get("name"),
            "state": (a.get("state") or "").upper(),
            "url": url,
            "icon": meta.get("icon"),
            "update": bool(a.get("upgrade_available")),
        })

    out_repl = []
    for r in replications:
        state = r.get("state") or {}
        out_repl.append({
            "name": r.get("name"),
            "enabled": r.get("enabled", True),
            "state": state.get("state"),
            "at": _ts(state.get("datetime")),
        })

    return {
        "hostname": info.get("hostname"),
        "version": info.get("version"),
        "uptime": info.get("uptime_seconds"),
        "loadavg": info.get("loadavg"),
        "pools": out_pools,
        "alerts": out_alerts,
        "apps": sorted(out_apps, key=lambda a: a["title"].lower()),
        "replications": out_repl,
    }


class _RPC:
    def __init__(self, ws):
        self.ws, self.ids = ws, itertools.count(1)

    async def call(self, method, *params):
        msg_id = next(self.ids)
        await self.ws.send(json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": list(params)}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") != msg_id:
                continue  # skip notifications
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error'].get('message', msg['error'])}")
            return msg["result"]


async def _fetch_ws(cfg):
    u = urlparse(cfg["url"])
    scheme = "wss" if u.scheme == "https" else "ws"
    ctx = None
    if scheme == "wss":
        ctx = ssl.create_default_context()
        if not cfg.get("verify_ssl", False):
            ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    async with websockets.connect(f"{scheme}://{u.netloc}/api/current", ssl=ctx,
                                  open_timeout=cfg.get("timeout", 8), max_size=2**24) as ws:
        rpc = _RPC(ws)
        if not await rpc.call("auth.login_with_api_key", cfg["api_key"]):
            raise RuntimeError("TrueNAS rejected the API key")
        info = await rpc.call("system.info")
        pools = await rpc.call("pool.query")
        names = [p["name"] for p in pools]
        datasets = await rpc.call("pool.dataset.query", [["id", "in", names]],
                                  {"extra": {"retrieve_children": False}})
        alerts = await rpc.call("alert.list")
        apps = await _optional(rpc.call("app.query"))
        repl = await _optional(rpc.call("replication.query"))
    return info, pools, datasets, alerts, apps, repl


async def _fetch_rest(cfg):
    base = cfg["url"].rstrip("/") + "/api/v2.0"
    async with client(cfg, headers={"Authorization": f"Bearer {cfg['api_key']}"}) as c:
        async def get(path, default=None):
            r = await c.get(f"{base}/{path}")
            if default is not None and r.status_code == 404:
                return default
            return r.raise_for_status().json()
        info = await get("system/info")
        pools = await get("pool")
        datasets = [d for d in await get("pool/dataset?extra.retrieve_children=false")
                    if "/" not in d.get("id", "")]
        alerts = await get("alert/list")
        apps = await get("app", default=[])
        repl = await get("replication", default=[])
    return info, pools, datasets, alerts, apps, repl


async def _optional(coro):
    try:
        return await coro
    except RuntimeError:
        return []


async def fetch(cfg: dict) -> dict:
    loader = _fetch_rest if cfg.get("api") == "rest" else _fetch_ws
    info, pools, datasets, alerts, apps, repl = await loader(cfg)
    return parse(info, pools, datasets, alerts, apps, repl, urlparse(cfg["url"]).hostname)
