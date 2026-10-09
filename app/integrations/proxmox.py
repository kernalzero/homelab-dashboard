"""Proxmox VE via /cluster/resources (one call covers nodes, guests and storage).

Auth: an API token with the PVEAuditor role, e.g. dashboard@pve!homelab.
"""
from .common import client, pct


def parse(resources: list[dict]) -> dict:
    nodes, guests, storage = [], [], []
    for r in resources:
        t = r.get("type")
        if t == "node":
            nodes.append({
                "name": r.get("node"),
                "online": r.get("status") == "online",
                "cpu": round(100 * (r.get("cpu") or 0), 1),
                "cores": r.get("maxcpu"),
                "mem_used": r.get("mem", 0),
                "mem_total": r.get("maxmem", 0),
                "mem_pct": pct(r.get("mem", 0), r.get("maxmem", 0)),
                "disk_pct": pct(r.get("disk", 0), r.get("maxdisk", 0)),
                "uptime": r.get("uptime"),
            })
        elif t in ("qemu", "lxc") and not r.get("template"):
            guests.append({
                "id": r.get("vmid"),
                "name": r.get("name") or f"{t}-{r.get('vmid')}",
                "kind": "VM" if t == "qemu" else "LXC",
                "node": r.get("node"),
                "status": r.get("status"),
                "cpu": round(100 * (r.get("cpu") or 0), 1),
                "mem_pct": pct(r.get("mem", 0), r.get("maxmem", 0)),
                "uptime": r.get("uptime"),
                "tags": [x for x in (r.get("tags") or "").replace(",", ";").split(";") if x],
            })
        elif t == "storage" and r.get("status") == "available":
            storage.append({
                "name": r.get("storage"),
                "node": r.get("node"),
                "shared": bool(r.get("shared")),
                "used": r.get("disk", 0),
                "total": r.get("maxdisk", 0),
                "pct": pct(r.get("disk", 0), r.get("maxdisk", 0)),
            })

    # Shared storage shows up once per node; keep one row.
    seen, uniq = set(), []
    for s in storage:
        key = s["name"] if s["shared"] else (s["name"], s["node"])
        if key not in seen:
            seen.add(key)
            uniq.append(s)

    guests.sort(key=lambda g: (g["status"] != "running", g["id"] or 0))
    return {
        "nodes": sorted(nodes, key=lambda n: n["name"] or ""),
        "guests": guests,
        "storage": sorted(uniq, key=lambda s: -s["pct"]),
        "running": sum(1 for g in guests if g["status"] == "running"),
        "stopped": sum(1 for g in guests if g["status"] != "running"),
    }


async def fetch(cfg: dict) -> dict:
    headers = {"Authorization": f"PVEAPIToken={cfg['token_id']}={cfg['token_secret']}"}
    async with client(cfg, headers=headers) as c:
        r = await c.get(f"{cfg['url'].rstrip('/')}/api2/json/cluster/resources")
        r.raise_for_status()
    return parse(r.json()["data"])


def _first_ipv4(ifaces: list[dict]) -> str | None:
    """Pick the first non-loopback IPv4 from either the LXC or guest-agent interface format."""
    for i in ifaces:
        if i.get("name") == "lo":
            continue
        if i.get("inet"):  # LXC: "192.168.1.20/24"
            return i["inet"].split("/")[0]
        for a in i.get("ip-addresses") or []:  # QEMU guest agent
            if a.get("ip-address-type") == "ipv4" and not a["ip-address"].startswith("127."):
                return a["ip-address"]
    return None


async def guest_ips(cfg: dict, guests: list[dict]) -> dict:
    """Best-effort IP lookup for running guests. VMs need the QEMU guest agent and
    the VM.GuestAgent.Audit (PVE 9) or VM.Monitor (PVE 8) privilege; failures are skipped."""
    headers = {"Authorization": f"PVEAPIToken={cfg['token_id']}={cfg['token_secret']}"}
    base = f"{cfg['url'].rstrip('/')}/api2/json/nodes"
    ips = {}
    async with client(cfg, headers=headers) as c:
        for g in guests:
            if g["status"] != "running":
                continue
            if g["kind"] == "LXC":
                path = f"{base}/{g['node']}/lxc/{g['id']}/interfaces"
            else:
                path = f"{base}/{g['node']}/qemu/{g['id']}/agent/network-get-interfaces"
            try:
                r = await c.get(path)
                if r.status_code != 200:
                    continue
                data = r.json().get("data")
                ifaces = data.get("result", []) if isinstance(data, dict) else (data or [])
                ip = _first_ipv4(ifaces)
                if ip:
                    ips[g["id"]] = ip
            except Exception:
                continue
    return ips
