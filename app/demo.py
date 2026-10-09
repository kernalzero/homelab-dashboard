"""Sample raw API payloads (shaped like the real APIs) for DASHBOARD_DEMO=1 and tests."""
import time

from . import services
from .integrations import proxmox, truenas, unifi

NOW = time.time()

UNIFI_HEALTH = [
    {"subsystem": "wan", "status": "ok", "wan_ip": "203.0.113.24", "isp_name": "Spectrum",
     "rx_bytes-r": 4_850_000, "tx_bytes-r": 612_000,
     "gw_system-stats": {"cpu": "18.2", "mem": "61.0", "uptime": "1814400"}},
    {"subsystem": "www", "status": "ok", "latency": 11, "xput_down": 941.2, "xput_up": 38.7,
     "speedtest_lastrun": NOW - 5400},
    {"subsystem": "wlan", "status": "ok", "num_user": 31, "num_guest": 2, "num_ap": 4},
    {"subsystem": "lan", "status": "ok", "num_user": 22, "num_guest": 0, "num_sw": 3},
]
UNIFI_DEVICES = [
    {"name": "UDM Pro", "model": "UDMPRO", "type": "udm", "state": 1, "ip": "192.168.1.1",
     "uptime": 1814400, "num_sta": 53, "system-stats": {"cpu": "18.2", "mem": "61.0"}},
    {"name": "Core Switch", "model": "USW-Pro-24-PoE", "type": "usw", "state": 1, "ip": "192.168.1.2",
     "uptime": 1814000, "num_sta": 22, "system-stats": {"cpu": "9", "mem": "40"}},
    {"name": "Barn Switch", "model": "USW-Flex-Mini", "type": "usw", "state": 1, "ip": "192.168.1.3",
     "uptime": 604800, "num_sta": 3},
    {"name": "Office Switch", "model": "USW-Lite-8-PoE", "type": "usw", "state": 1, "ip": "192.168.1.4",
     "uptime": 1814000, "num_sta": 6},
    {"name": "House AP", "model": "U7-Pro", "type": "uap", "state": 1, "ip": "192.168.1.10",
     "uptime": 1814000, "num_sta": 19, "upgradable": True},
    {"name": "Upstairs AP", "model": "U6-Lite", "type": "uap", "state": 1, "ip": "192.168.1.11",
     "uptime": 1814000, "num_sta": 8},
    {"name": "Barn AP", "model": "U6-Mesh", "type": "uap", "state": 1, "ip": "192.168.1.12",
     "uptime": 86400, "num_sta": 4},
    {"name": "Coop AP", "model": "UAP-AC-M", "type": "uap", "state": 0, "ip": "192.168.1.13",
     "uptime": 0, "num_sta": 0},
]

GiB = 1024**3
PVE_RESOURCES = [
    {"type": "node", "node": "pve1", "status": "online", "cpu": 0.21, "maxcpu": 16,
     "mem": 41 * GiB, "maxmem": 64 * GiB, "disk": 18 * GiB, "maxdisk": 94 * GiB, "uptime": 2592000},
    {"type": "node", "node": "pve2", "status": "online", "cpu": 0.07, "maxcpu": 8,
     "mem": 11 * GiB, "maxmem": 32 * GiB, "disk": 9 * GiB, "maxdisk": 94 * GiB, "uptime": 1209600},
    {"type": "lxc", "vmid": 101, "name": "pihole", "node": "pve1", "status": "running",
     "cpu": 0.01, "mem": 180e6, "maxmem": 512e6, "uptime": 2591000, "tags": "dns;core"},
    {"type": "lxc", "vmid": 102, "name": "jellyfin", "node": "pve1", "status": "running",
     "cpu": 0.12, "mem": 2.1 * GiB, "maxmem": 4 * GiB, "uptime": 2591000, "tags": "media"},
    {"type": "lxc", "vmid": 103, "name": "nginx-proxy-manager", "node": "pve1", "status": "running",
     "cpu": 0.004, "mem": 300e6, "maxmem": 1 * GiB, "uptime": 2591000},
    {"type": "lxc", "vmid": 104, "name": "uptime-kuma", "node": "pve2", "status": "running",
     "cpu": 0.02, "mem": 200e6, "maxmem": 1 * GiB, "uptime": 1209000},
    {"type": "qemu", "vmid": 200, "name": "haos", "node": "pve1", "status": "running",
     "cpu": 0.04, "mem": 3.2 * GiB, "maxmem": 6 * GiB, "uptime": 2591000, "tags": "home"},
    {"type": "qemu", "vmid": 201, "name": "docker-host", "node": "pve2", "status": "running",
     "cpu": 0.09, "mem": 7.5 * GiB, "maxmem": 12 * GiB, "uptime": 1209000},
    {"type": "qemu", "vmid": 202, "name": "win11-lab", "node": "pve2", "status": "stopped",
     "cpu": 0, "mem": 0, "maxmem": 8 * GiB, "uptime": 0},
    {"type": "qemu", "vmid": 9000, "name": "ubuntu-template", "node": "pve1", "status": "stopped",
     "template": 1},
    {"type": "storage", "storage": "local-lvm", "node": "pve1", "status": "available",
     "disk": 310 * GiB, "maxdisk": 800 * GiB, "shared": 0},
    {"type": "storage", "storage": "local-lvm", "node": "pve2", "status": "available",
     "disk": 120 * GiB, "maxdisk": 400 * GiB, "shared": 0},
    {"type": "storage", "storage": "truenas-nfs", "node": "pve1", "status": "available",
     "disk": 2.1 * 1024 * GiB, "maxdisk": 6 * 1024 * GiB, "shared": 1},
    {"type": "storage", "storage": "truenas-nfs", "node": "pve2", "status": "available",
     "disk": 2.1 * 1024 * GiB, "maxdisk": 6 * 1024 * GiB, "shared": 1},
]
PVE_IPS = {101: "192.168.10.21", 102: "192.168.10.22", 103: "192.168.10.23",
           104: "192.168.10.24", 200: "192.168.10.30"}

TiB = 1024**4
TN_INFO = {"hostname": "truenas", "version": "TrueNAS-25.10.0", "uptime_seconds": 3456000,
           "loadavg": [0.42, 0.51, 0.48]}
TN_POOLS = [
    {"name": "tank", "status": "ONLINE", "healthy": True, "size": 44 * TiB, "allocated": 19 * TiB,
     "scan": {"function": "SCRUB", "state": "FINISHED", "end_time": {"$date": (NOW - 6 * 86400) * 1000},
              "errors": 0}},
    {"name": "fast", "status": "ONLINE", "healthy": True, "size": 1.8 * TiB, "allocated": 0.6 * TiB,
     "scan": {"function": "SCRUB", "state": "FINISHED", "end_time": {"$date": (NOW - 13 * 86400) * 1000},
              "errors": 0}},
]
TN_DATASETS = [
    {"id": "tank", "used": {"parsed": 14.2 * TiB}, "available": {"parsed": 15.1 * TiB}},
    {"id": "fast", "used": {"parsed": 0.55 * TiB}, "available": {"parsed": 1.1 * TiB}},
]
TN_ALERTS = [
    {"level": "WARNING", "formatted": "Device /dev/sdf: 8 Currently unreadable (pending) sectors.",
     "datetime": {"$date": (NOW - 7200) * 1000}, "dismissed": False},
    {"level": "INFO", "formatted": "Scrub of pool 'tank' finished.", "datetime": {"$date": NOW * 1000},
     "dismissed": False},
]
TN_APPS = [
    {"name": "plex", "state": "RUNNING", "portals": {"Web UI": "http://0.0.0.0:32400/web"},
     "metadata": {"title": "Plex"}, "upgrade_available": True},
    {"name": "immich", "state": "RUNNING", "portals": {"Web UI": "http://0.0.0.0:30041/"},
     "metadata": {"title": "Immich"}},
    {"name": "nextcloud", "state": "RUNNING", "portals": {"Web UI": "https://0.0.0.0:30027/"},
     "metadata": {"title": "Nextcloud"}},
    {"name": "sonarr", "state": "RUNNING", "portals": {"Web UI": "http://0.0.0.0:30113/"},
     "metadata": {"title": "Sonarr"}},
    {"name": "radarr", "state": "RUNNING", "portals": {"Web UI": "http://0.0.0.0:30025/"},
     "metadata": {"title": "Radarr"}},
    {"name": "prowlarr", "state": "RUNNING", "portals": {"Web UI": "http://0.0.0.0:30050/"},
     "metadata": {"title": "Prowlarr"}},
    {"name": "qbittorrent", "state": "STOPPED", "portals": {"Web UI": "http://0.0.0.0:30024/"},
     "metadata": {"title": "qBittorrent"}},
    {"name": "frigate", "state": "RUNNING", "portals": {"Web UI": "http://0.0.0.0:30058/"},
     "metadata": {"title": "Frigate"}},
]
TN_REPL = [
    {"name": "tank/photos -> offsite", "enabled": True,
     "state": {"state": "SUCCESS", "datetime": {"$date": (NOW - 3 * 3600) * 1000}}},
]


def demo_state() -> dict:
    pve = proxmox.parse(PVE_RESOURCES)
    tn = truenas.parse(TN_INFO, TN_POOLS, TN_DATASETS, TN_ALERTS, TN_APPS, TN_REPL, "192.168.1.50")
    uf = unifi.parse(UNIFI_HEALTH, UNIFI_DEVICES)
    configured = services.from_config({"services": [
        {"group": "Infrastructure", "items": [
            {"name": "UniFi Network", "url": "https://192.168.1.1", "icon": "unifi"},
            {"name": "Proxmox", "url": "https://192.168.10.5:8006"},
            {"name": "TrueNAS", "url": "https://192.168.1.50"},
        ]},
    ]})
    svc = services.merge(configured, services.from_truenas(tn) + services.from_proxmox(pve, PVE_IPS))
    checks = {}
    for i, s in enumerate(svc):
        if s.get("url"):
            down = s.get("state") not in (None, "running")
            checks[s["id"]] = {"up": not down, "code": None if down else 200,
                               "ms": None if down else 8 + (i * 7) % 60}
    t = time.time()
    return {
        "title": "Homelab (demo)",
        "integrations": {
            "unifi": {"data": uf, "error": None, "updated": t},
            "proxmox": {"data": pve, "error": None, "updated": t},
            "truenas": {"data": tn, "error": None, "updated": t},
        },
        "services": svc,
        "checks": checks,
        "updated": t,
    }
