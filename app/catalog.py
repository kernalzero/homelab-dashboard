"""Well-known self-hosted apps: default port, path and icon slug.

Used to turn discovered Proxmox guests into service tiles and to pick icons.
Icon slugs follow https://github.com/homarr-labs/dashboard-icons.
"""
import re

# key: (port, scheme, path, icon)
APPS = {
    "plex": (32400, "http", "/web", "plex"),
    "jellyfin": (8096, "http", "", "jellyfin"),
    "emby": (8096, "http", "", "emby"),
    "sonarr": (8989, "http", "", "sonarr"),
    "radarr": (7878, "http", "", "radarr"),
    "lidarr": (8686, "http", "", "lidarr"),
    "readarr": (8787, "http", "", "readarr"),
    "prowlarr": (9696, "http", "", "prowlarr"),
    "bazarr": (6767, "http", "", "bazarr"),
    "overseerr": (5055, "http", "", "overseerr"),
    "jellyseerr": (5055, "http", "", "jellyseerr"),
    "tautulli": (8181, "http", "", "tautulli"),
    "qbittorrent": (8080, "http", "", "qbittorrent"),
    "sabnzbd": (8080, "http", "", "sabnzbd"),
    "nzbget": (6789, "http", "", "nzbget"),
    "transmission": (9091, "http", "", "transmission"),
    "homeassistant": (8123, "http", "", "home-assistant"),
    "haos": (8123, "http", "", "home-assistant"),
    "nodered": (1880, "http", "", "node-red"),
    "zigbee2mqtt": (8080, "http", "", "zigbee2mqtt"),
    "esphome": (6052, "http", "", "esphome"),
    "frigate": (5000, "http", "", "frigate"),
    "scrypted": (10443, "https", "", "scrypted"),
    "pihole": (80, "http", "/admin", "pi-hole"),
    "adguard": (80, "http", "", "adguard-home"),
    "technitium": (5380, "http", "", "technitium"),
    "nextcloud": (443, "https", "", "nextcloud"),
    "immich": (2283, "http", "", "immich"),
    "photoprism": (2342, "http", "", "photoprism"),
    "paperless": (8000, "http", "", "paperless-ngx"),
    "vaultwarden": (80, "http", "", "vaultwarden"),
    "portainer": (9443, "https", "", "portainer"),
    "dockge": (5001, "http", "", "dockge"),
    "grafana": (3000, "http", "", "grafana"),
    "prometheus": (9090, "http", "", "prometheus"),
    "influxdb": (8086, "http", "", "influxdb"),
    "uptimekuma": (3001, "http", "", "uptime-kuma"),
    "pbs": (8007, "https", "", "proxmox"),
    "proxmoxbackup": (8007, "https", "", "proxmox"),
    "npm": (81, "http", "", "nginx-proxy-manager"),
    "nginxproxymanager": (81, "http", "", "nginx-proxy-manager"),
    "traefik": (8080, "http", "/dashboard/", "traefik"),
    "caddy": (80, "http", "", "caddy"),
    "authentik": (9000, "http", "", "authentik"),
    "authelia": (9091, "http", "", "authelia"),
    "gitea": (3000, "http", "", "gitea"),
    "forgejo": (3000, "http", "", "forgejo"),
    "codeserver": (8443, "https", "", "code-server"),
    "syncthing": (8384, "http", "", "syncthing"),
    "homebridge": (8581, "http", "", "homebridge"),
    "mealie": (9000, "http", "", "mealie"),
    "tandoor": (8080, "http", "", "tandoor-recipes"),
    "grocy": (80, "http", "", "grocy"),
    "homebox": (7745, "http", "", "homebox"),
    "audiobookshelf": (13378, "http", "", "audiobookshelf"),
    "navidrome": (4533, "http", "", "navidrome"),
    "calibreweb": (8083, "http", "", "calibre-web"),
    "kavita": (5000, "http", "", "kavita"),
    "wgeasy": (51821, "http", "", "wireguard"),
    "minio": (9001, "http", "", "minio"),
    "stirlingpdf": (8080, "http", "", "stirling-pdf"),
    "ollama": (11434, "http", "", "ollama"),
    "openwebui": (8080, "http", "", "open-webui"),
    "n8n": (5678, "http", "", "n8n"),
    "actual": (5006, "http", "", "actual-budget"),
    "firefly": (8080, "http", "", "firefly-iii"),
    "unifi": (8443, "https", "", "unifi"),
    "omada": (8043, "https", "", "omada"),
    "netbox": (8080, "http", "", "netbox"),
    "docker": (None, None, "", "docker"),
    "truenas": (443, "https", "", "truenas-scale"),
    "proxmox": (8006, "https", "", "proxmox"),
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def match(name: str):
    """Return (key, entry) for the catalog app a guest/app name refers to, if any."""
    n = _norm(name)
    if not n:
        return None
    if n in APPS:
        return n, APPS[n]
    # Longest key first so "jellyseerr-lxc" beats "jellyfin"-style prefixes.
    for key in sorted(APPS, key=len, reverse=True):
        if len(key) >= 3 and key in n:
            return key, APPS[key]
    return None


def icon_for(name: str) -> str | None:
    m = match(name)
    return m[1][3] if m else None
