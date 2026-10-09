"""FastAPI app: polls integrations in the background and serves a cached snapshot."""
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import health, services
from .config import load_config
from .integrations import proxmox, truenas, unifi

log = logging.getLogger("dashboard")
STATIC = Path(__file__).parent / "static"
DEMO = os.environ.get("DASHBOARD_DEMO") == "1"

state: dict = {"integrations": {}, "services": [], "checks": {}, "updated": None}


def _as_list(v):
    return v if isinstance(v, list) else ([v] if v else [])


async def _poll_proxmox(cfgs):
    merged = {"nodes": [], "guests": [], "storage": [], "running": 0, "stopped": 0}
    ips = {}
    for cfg in cfgs:
        data = await proxmox.fetch(cfg)
        for k in ("nodes", "guests", "storage"):
            merged[k] += data[k]
        merged["running"] += data["running"]
        merged["stopped"] += data["stopped"]
        if cfg.get("discover_ips", True):
            ips |= await proxmox.guest_ips(cfg, data["guests"])
    merged["_ips"] = ips
    return merged


async def _run(name, coro_fn, interval):
    while True:
        entry = state["integrations"].setdefault(name, {})
        try:
            entry["data"] = await coro_fn()
            entry["error"] = None
            entry["updated"] = time.time()
        except Exception as e:  # keep last good data, surface the error
            log.warning("%s poll failed: %s", name, e)
            entry["error"] = f"{type(e).__name__}: {e}"
        await asyncio.sleep(interval)


async def _services_loop(cfg, interval):
    while True:
        integ = state["integrations"]
        pve = (integ.get("proxmox") or {}).get("data")
        tn = (integ.get("truenas") or {}).get("data")
        disc = cfg.get("discovery", {})
        discovered = []
        if disc.get("truenas_apps", True):
            discovered += services.from_truenas(tn)
        if disc.get("proxmox_guests", True):
            discovered += services.from_proxmox(pve, (pve or {}).get("_ips", {}))
        svc = services.merge(services.from_config(cfg), discovered)
        try:
            state["checks"] = await health.check_all(svc, timeout=cfg.get("check_timeout", 5))
        except Exception as e:
            log.warning("health checks failed: %s", e)
        state["services"] = svc
        state["updated"] = time.time()
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    if DEMO:
        from .demo import demo_state
        state.update(demo_state())
    else:
        cfg = load_config()
        poll = cfg.get("poll_seconds", 30)
        if cfg.get("unifi"):
            tasks.append(_run("unifi", lambda: unifi.fetch(cfg["unifi"]), poll))
        if pve := _as_list(cfg.get("proxmox")):
            tasks.append(_run("proxmox", lambda: _poll_proxmox(pve), poll))
        if cfg.get("truenas"):
            tasks.append(_run("truenas", lambda: truenas.fetch(cfg["truenas"]), max(poll, 60)))
        tasks.append(_services_loop(cfg, cfg.get("check_seconds", 60)))
        state["title"] = cfg.get("title", "Homelab")
    running = [asyncio.create_task(t) for t in tasks]
    yield
    for t in running:
        t.cancel()


app = FastAPI(title="Homelab Dashboard", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/state")
async def api_state():
    integ = {
        k: {kk: vv for kk, vv in v.items() if kk != "data"} | {
            "data": {dk: dv for dk, dv in (v.get("data") or {}).items() if not dk.startswith("_")} or None
        }
        for k, v in state["integrations"].items()
    }
    return {
        "title": state.get("title", "Homelab"),
        "integrations": integ,
        "services": [s | {"health": state["checks"].get(s["id"])} for s in state["services"]],
        "updated": state["updated"],
        "now": time.time(),
    }


@app.get("/healthz")
async def healthz():
    return {"ok": True}
