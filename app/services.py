"""Build the service tile list from config plus auto-discovery."""
import re

from . import catalog


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def from_config(cfg: dict) -> list[dict]:
    out = []
    for group in cfg.get("services", []) or []:
        for s in group.get("items", []) or []:
            out.append({
                "id": f"cfg-{_slug(s['name'])}",
                "name": s["name"],
                "url": s.get("url"),
                "check_url": s.get("check_url"),
                "check": s.get("check", True),
                "icon": s.get("icon") or catalog.icon_for(s["name"]),
                "group": group.get("group", "Services"),
                "description": s.get("description"),
                "source": "config",
            })
    return out


def from_truenas(tn: dict | None) -> list[dict]:
    if not tn:
        return []
    out = []
    for a in tn.get("apps", []):
        out.append({
            "id": f"tn-{_slug(a['name'])}",
            "name": a["title"],
            "url": a["url"],
            "icon": catalog.icon_for(a["name"]) or a.get("icon"),
            "group": "TrueNAS apps",
            "source": "truenas",
            "state": "running" if a["state"] == "RUNNING" else a["state"].lower(),
            "update": a["update"],
        })
    return out


def from_proxmox(pve: dict | None, ips: dict) -> list[dict]:
    if not pve:
        return []
    out = []
    for g in pve.get("guests", []):
        m = catalog.match(g["name"])
        ip = ips.get(g["id"])
        url = None
        if m and ip and m[1][0]:
            port, scheme, path, _ = m[1]
            default = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
            url = f"{scheme}://{ip}{'' if default else f':{port}'}{path}"
        out.append({
            "id": f"pve-{g['id']}",
            "name": g["name"],
            "url": url,
            "icon": m[1][3] if m else None,
            "group": "Proxmox guests",
            "source": "proxmox",
            "state": g["status"],
            "description": f"{g['kind']} {g['id']} on {g['node']}" + (f" · {ip}" if ip else ""),
        })
    return out


def merge(configured, discovered) -> list[dict]:
    """Configured tiles win; drop discovered tiles that point at the same thing."""
    names = {_slug(s["name"]) for s in configured}
    hosts = {s["url"].split("//", 1)[-1].rstrip("/") for s in configured if s.get("url")}
    out = list(configured)
    for s in discovered:
        host = (s.get("url") or "").split("//", 1)[-1].rstrip("/")
        if _slug(s["name"]) in names or (host and host in hosts):
            continue
        out.append(s)
    return out
