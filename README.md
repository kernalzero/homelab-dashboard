# Homelab Dashboard

A self-hosted infrastructure dashboard in the spirit of Homarr, for a UniFi + Proxmox + TrueNAS lab.
It runs on your network, polls each system's API with read-only credentials, and serves a single
auto-refreshing page.

![Dashboard (demo data)](docs/screenshot.png)

**What it shows**

| Source | Widgets |
|---|---|
| UniFi (UDM Pro) | WAN status, live throughput, latency, last speedtest, client counts, gateway CPU/RAM, every UniFi device with online state, clients and firmware updates |
| Proxmox VE | Node CPU/RAM/uptime, every VM and LXC with status and usage, storage capacity |
| TrueNAS | Pool health and usable capacity, last scrub, active alerts (warning and above), replication tasks, installed apps |
| Services | A tile per service with an HTTP up/down check and response time, grouped and searchable (press `/`) |

**Service discovery.** You don't need to list everything by hand:

- Every installed **TrueNAS app** becomes a tile linked to its web UI.
- Every **Proxmox VM/LXC** becomes a tile. If its name matches a known app (Jellyfin, Pi-hole,
  Home Assistant, Nginx Proxy Manager and about 70 others, see `app/catalog.py`), the dashboard
  looks up the guest's IP and links to the app's default port.
- Anything else goes in `services:` in the config. Configured tiles replace discovered ones with
  the same name or URL.

Icons come from [dashboard-icons](https://github.com/homarr-labs/dashboard-icons) via jsDelivr.
When the browser can't reach the CDN, tiles fall back to letter avatars.

## Quick start

```bash
git clone <this repo> homelab-dashboard && cd homelab-dashboard
cp config/config.example.yaml config/config.yaml
cp .env.example .env && chmod 600 .env
# edit config/config.yaml (IPs) and .env (secrets), then:
docker compose up -d --build
```

Open `http://<host>:8080`. To preview without credentials, set `DASHBOARD_DEMO: "1"` in
`docker-compose.yml`.

A small Debian LXC on Proxmox (1 vCPU, 512 MB) with Docker works well. You can also run it as a
custom app on TrueNAS.

Without Docker:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
DASHBOARD_CONFIG=config/config.yaml .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Running as a TrueNAS app

Every push to `main` builds an image at `ghcr.io/kernalzero/homelab-dashboard:latest`
(amd64 and arm64) through GitHub Actions. TrueNAS pulls it like any other app.

1. **Make the image pullable.** The repo is private, so the image is private too. Do one of these:
   - **Keep it private:** create a GitHub personal access token (classic) with only the
     `read:packages` scope. In TrueNAS, go to **Apps → Configuration → Manage Container Image
     Registries → Add**, set the URI to `ghcr.io`, and enter your GitHub username and the token.
   - **Make it public:** go to GitHub → your profile → **Packages → homelab-dashboard → Package
     settings → Change visibility**. The image contains only code, never your config or secrets.
2. **Create a config dataset**, e.g. `tank/apps/homelab-dashboard`, and copy
   `config/config.example.yaml` into it as `config.yaml` with your IPs. Make sure the `apps` user
   (uid 568) can read it.
3. **Install:** go to **Apps → Discover Apps → ⋮ → Install via YAML** and paste
   [`deploy/truenas-app.yaml`](deploy/truenas-app.yaml). Fill in the three secrets, the dataset
   path and `TZ`, then save.
4. Open `http://<truenas-ip>:30080`.

**Updating:** after a new build finishes on GitHub, open the app in TrueNAS and click **Update**.
If no update button shows, stop and start the app; `pull_policy: always` makes it pull the latest
image.

The dashboard can monitor the TrueNAS host it runs on. Use the NAS's LAN IP in the `truenas:`
section, not `localhost`.

## Read-only credentials

Give the dashboard credentials that can read and nothing else.

### UniFi (UDM Pro)

**Option A: API key** (UniFi Network 9.0 or later). In the Network app, go to
**Settings → Control Plane → Integrations**, create an API key and put it in `UNIFI_API_KEY`.

**Option B: local view-only admin** (use this if the API key returns 401 on your firmware).
In **UniFi OS → Admins & Users**, add a user, choose **Restrict to local access only**, and give it
the **View Only** role for Network and **None** for other apps. Then set `username` and `password`
in the config instead of `api_key`. Accounts with MFA can't be used here.

### Proxmox VE

Run this on any node:

```bash
pveum user add dashboard@pve --comment "Homelab dashboard (read-only)"
pveum acl modify / --users dashboard@pve --roles PVEAuditor
pveum user token add dashboard@pve homelab --privsep 1
pveum acl modify / --tokens 'dashboard@pve!homelab' --roles PVEAuditor
```

Put the printed secret in `PVE_TOKEN_SECRET`. `PVEAuditor` covers nodes, guests, storage and
**LXC** IP lookup.

VM IP lookup also needs the QEMU guest agent running in the VM, plus one extra privilege. Skip it
if you don't need links for VM tiles.

```bash
# PVE 9:
pveum role add DashboardAgent --privs "VM.GuestAgent.Audit"
# PVE 8:
pveum role add DashboardAgent --privs "VM.Monitor"

pveum acl modify /vms --users dashboard@pve --roles DashboardAgent
pveum acl modify /vms --tokens 'dashboard@pve!homelab' --roles DashboardAgent
```

### TrueNAS

1. In **Credentials → Users**, add a user `dashboard` with no shell and no SMB access. Give it the
   **Read-only Administrator** role (the field is called *Roles* or *Privileges*, depending on
   version).
2. Sign in as that user (or as admin, using **API Keys → Add** with the user set to `dashboard`)
   and create an API key. Put it in `TRUENAS_API_KEY`.
3. TrueNAS 25.04 and later use the websocket JSON-RPC API (the default). On 24.x, set `api: rest`.

## Security notes

- The dashboard has **no login of its own** and shows your network layout. Keep it on the LAN or a
  management VLAN, or put it behind your reverse proxy with SSO (Authentik, Authelia, or Cloudflare
  Access if exposed).
- Secrets stay on the server. The browser only receives the summarized state from `/api/state`.
- `verify_ssl: false` is the default because home lab gear usually has self-signed certificates.
  Turn it on per integration if you've installed real certificates.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
DASHBOARD_DEMO=1 .venv/bin/uvicorn app.main:app --reload --port 8080
```

Layout:

- `app/integrations/`: one module per system. Each has a pure `parse()` and an async `fetch()`.
- `app/services.py`: tile discovery and merging.
- `app/static/`: the front end, plain HTML/CSS/JS with no build step.

Adding a widget means writing a `parse`/`fetch` pair, registering a poller in `app/main.py`, and
adding a render function in `app.js`.
