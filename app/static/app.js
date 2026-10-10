"use strict";

const ICON_CDN = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/";
const REFRESH_MS = 15000;
const $ = (id) => document.getElementById(id);
let last = null;

// ---------- formatting ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function bytes(n) {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB", "PB"]; let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n >= 100 || i === 0 ? 0 : 1)} ${u[i]}`;
}
function bps(n) {
  const u = ["bps", "Kbps", "Mbps", "Gbps"]; let i = 0;
  while (n >= 1000 && i < u.length - 1) { n /= 1000; i++; }
  return [n.toFixed(n >= 100 ? 0 : 1), u[i]];
}
function dur(s) {
  if (!s) return "—";
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`;
}
const ago = (ts, now) => (ts ? `${dur(now - ts)} ago` : "never");
const level = (p, warn = 75, bad = 90) => (p >= bad ? "bad" : p >= warn ? "warn" : "");

function meter(label, pct, valText, cls = "") {
  const p = Math.max(0, Math.min(100, pct || 0));
  return `<div class="meter ${cls}"><span class="label" title="${esc(label)}">${esc(label)}</span>
    <div class="track"><div class="fill ${level(p)}" style="width:${p}%"></div></div>
    <span class="val">${esc(valText ?? Math.round(p) + "%")}</span></div>`;
}

function icon(name, slug) {
  const ch = esc((name || "?").trim()[0]?.toUpperCase() || "?");
  if (!slug) return `<div class="letter">${ch}</div>`;
  const src = /^https?:/.test(slug) ? slug : ICON_CDN + encodeURIComponent(slug) + ".svg";
  return `<img class="icon" src="${esc(src)}" alt="" loading="lazy" data-letter="${ch}">`;
}

// Swap broken service icons (offline, unknown slug) for a letter avatar.
document.addEventListener("error", (e) => {
  const img = e.target;
  if (img.tagName !== "IMG" || !img.classList.contains("icon")) return;
  const div = document.createElement("div");
  div.className = "letter";
  div.textContent = img.dataset.letter || "?";
  img.replaceWith(div);
}, true);

function integ(state, key) {
  const i = state.integrations[key];
  return { data: i?.data, error: i?.error, updated: i?.updated, configured: !!i };
}

// ---------- header ----------
function renderPills(state) {
  const names = { unifi: "UniFi", proxmox: "Proxmox", truenas: "TrueNAS" };
  $("pills").innerHTML = Object.entries(names)
    .filter(([k]) => state.integrations[k])
    .map(([k, label]) => {
      const { data, error } = integ(state, k);
      const cls = error ? (data ? "warn" : "bad") : data ? "ok" : "";
      const title = error || (data ? "Connected" : "Waiting for first poll");
      return `<span class="pill" title="${esc(title)}"><span class="dot ${cls}"></span>${label}</span>`;
    }).join("");
}

// Server's TZ (from the app's environment) when the browser recognises it, else the device's.
function tz(extra = {}) {
  const timeZone = last?.tz;
  if (timeZone) {
    try { new Intl.DateTimeFormat([], { timeZone }); return { ...extra, timeZone }; } catch {}
  }
  return extra;
}

function tickClock() {
  const d = new Date();
  $("time").textContent = d.toLocaleTimeString([], tz({ hour: "2-digit", minute: "2-digit" }));
  $("date").textContent = d.toLocaleDateString([], tz({ weekday: "long", month: "short", day: "numeric" }));
}

// ---------- widgets ----------
function widget(title, iconSlug, body, err) {
  return `<div class="card widget"><div class="widget-head"><div class="widget-title">
    ${iconSlug ? `<img src="${ICON_CDN}${iconSlug}.svg" alt="" onerror="this.remove()">` : ""}<h2>${esc(title)}</h2></div></div>
    ${err ? `<div class="err">${esc(err)}</div>` : ""}${body}</div>`;
}

function renderWidgets(state) {
  const out = [];
  const now = state.now;
  const uf = integ(state, "unifi");
  if (uf.configured) {
    const d = uf.data;
    if (d) {
      const [down, du] = bps(d.wan.rx_bps), [up, uu] = bps(d.wan.tx_bps);
      out.push(widget("Internet", "unifi", `
        <div style="display:flex;gap:24px;align-items:baseline">
          <div class="big">↓ ${down}<small>${du}</small></div><div class="big">↑ ${up}<small>${uu}</small></div>
        </div>
        <div class="kv">
          <div><span>Status</span><span><span class="dot ${d.wan.status === "ok" ? "ok" : "bad"}" style="display:inline-block"></span> ${esc(d.wan.status)}</span></div>
          <div><span>Latency</span><span>${d.wan.latency_ms ?? "—"} ms</span></div>
          <div><span>ISP</span><span>${esc(d.wan.isp || "—")}</span></div>
        </div>
        <div class="muted" style="font-size:12px">Speedtest ${d.wan.speedtest_down_mbps ? `${Math.round(d.wan.speedtest_down_mbps)} / ${Math.round(d.wan.speedtest_up_mbps)} Mbps · ${ago(d.wan.speedtest_at, now)}` : "not run"} · WAN ${esc(d.wan.ip || "")}</div>`, uf.error));
      const total = d.clients.wired + d.clients.wireless;
      out.push(widget("Network", null, `
        <div class="big">${total}<small>clients</small></div>
        <div class="kv">
          <div><span>Wi-Fi</span><span>${d.clients.wireless}</span></div>
          <div><span>Wired</span><span>${d.clients.wired}</span></div>
          <div><span>Guest</span><span>${d.clients.guest}</span></div>
        </div>
        <div class="kv">
          <div><span>Devices</span><span>${d.devices.length}</span></div>
          <div><span>Offline</span><span style="color:${d.devices_offline ? "var(--bad)" : "inherit"}">${d.devices_offline}</span></div>
          <div><span>Updates</span><span style="color:${d.updates_available ? "var(--warn)" : "inherit"}">${d.updates_available}</span></div>
        </div>
        ${d.gateway.cpu != null ? meter("Gateway CPU", d.gateway.cpu) + meter("Gateway RAM", d.gateway.mem) : ""}`, uf.error));
    } else out.push(widget("UniFi", "unifi", `<div class="muted">Connecting…</div>`, uf.error));
  }

  const pve = integ(state, "proxmox");
  if (pve.configured) {
    const d = pve.data;
    out.push(widget("Proxmox", "proxmox", d ? `
      <div class="big">${d.running}<small>running</small> <span class="muted" style="font-size:15px;font-weight:500">· ${d.stopped} stopped</span></div>
      ${d.nodes.map((n) => `
        <div style="display:grid;gap:4px">
          <div style="display:flex;justify-content:space-between;font-size:12px"><span><span class="dot ${n.online ? "ok" : "bad"}" style="display:inline-block;margin-right:6px"></span><b>${esc(n.name)}</b></span><span class="muted">${n.cores} cores · up ${dur(n.uptime)}</span></div>
          ${meter("CPU", n.cpu)}${meter("RAM", n.mem_pct, `${Math.round(n.mem_pct)}%`)}
        </div>`).join("")}` : `<div class="muted">Connecting…</div>`, pve.error));
  }

  const tn = integ(state, "truenas");
  if (tn.configured) {
    const d = tn.data;
    out.push(widget("TrueNAS", "truenas-scale", d ? `
      <div style="display:flex;justify-content:space-between;font-size:12px" class="muted"><span>${esc(d.version || "")}</span><span>up ${dur(d.uptime)}</span></div>
      ${d.pools.map((p) => `
        <div style="display:grid;gap:4px">
          <div style="display:flex;justify-content:space-between;font-size:12px">
            <span><span class="dot ${p.healthy ? "ok" : "bad"}" style="display:inline-block;margin-right:6px"></span><b>${esc(p.name)}</b> <span class="muted">${esc(p.status)}</span></span>
            <span class="muted">${bytes(p.used)} / ${bytes(p.total)}</span></div>
          ${meter("Used", p.pct)}
          <div class="muted" style="font-size:11px">Last ${esc((p.scan || "scan").toLowerCase())}: ${p.scan_end ? ago(p.scan_end, now) : "—"}${p.scan_errors ? ` · <span style="color:var(--bad)">${p.scan_errors} errors</span>` : ""}</div>
        </div>`).join("")}
      ${d.alerts.length ? `<div style="font-size:12px;color:var(--warn)">⚠ ${d.alerts.length} active alert${d.alerts.length > 1 ? "s" : ""}</div>` : `<div style="font-size:12px;color:var(--ok)">No active alerts</div>`}`
      : `<div class="muted">Connecting…</div>`, tn.error));
  }

  if (!out.length) {
    out.push(`<div class="card widget"><h2>Nothing configured</h2><div class="muted">Copy <code>config/config.example.yaml</code> to <code>config/config.yaml</code> and add your UniFi, Proxmox and TrueNAS credentials.</div></div>`);
  }
  $("widgets").innerHTML = out.join("");
}

// ---------- services ----------
function serviceStatus(s) {
  if (s.health) return s.health.up ? "ok" : "bad";
  if (s.state) return s.state === "running" ? "ok" : s.state === "stopped" ? "" : "warn";
  return "";
}

function renderServices(state) {
  const q = $("search").value.trim().toLowerCase();
  const list = state.services.filter((s) => !q || `${s.name} ${s.group} ${s.description || ""}`.toLowerCase().includes(q));
  const groups = new Map();
  for (const s of list) { if (!groups.has(s.group)) groups.set(s.group, []); groups.get(s.group).push(s); }

  const up = state.services.filter((s) => s.health?.up).length;
  const checked = state.services.filter((s) => s.health).length;
  $("svc-summary").textContent = checked ? `${up}/${checked} responding` : "";

  $("services").innerHTML = [...groups].map(([g, items]) => `
    <div class="group"><h3>${esc(g)}</h3><div class="tiles">
      ${items.map((s) => {
        const st = serviceStatus(s);
        const dim = s.state && s.state !== "running";
        const sub = s.health?.ms != null ? `${s.health.ms} ms` : s.health && !s.health.up ? (s.health.error || (s.health.code ? `HTTP ${s.health.code}` : "unreachable")) : s.description || (s.state ?? "");
        const tag = s.url ? "a" : "div";
        const attrs = s.url ? ` href="${esc(s.url)}" target="_blank" rel="noopener"` : "";
        return `<${tag} class="card tile${dim ? " dim" : ""}"${attrs} title="${esc(s.description || s.url || "")}">
          ${icon(s.name, s.icon)}
          <div class="meta"><span class="name">${esc(s.name)}${s.update ? '<span class="badge">update</span>' : ""}</span><span class="sub">${esc(sub)}</span></div>
          <span class="dot ${st}"></span></${tag}>`;
      }).join("")}
    </div></div>`).join("") || `<div class="muted">No services match “${esc(q)}”.</div>`;
}

// ---------- detail panels ----------
function renderPanels(state) {
  const now = state.now;
  const pve = integ(state, "proxmox").data;
  $("panel-guests").className = pve ? "card panel" : "";
  $("panel-guests").innerHTML = pve ? `<h2>Virtual machines & containers</h2>
    <table><thead><tr><th>Name</th><th>Type</th><th>Node</th><th class="num">CPU</th><th class="num">RAM</th><th class="num">Uptime</th></tr></thead><tbody>
    ${pve.guests.map((g) => `<tr><td><span class="dot ${g.status === "running" ? "ok" : ""}"></span>${esc(g.name)} <span class="muted">${g.id}</span></td>
      <td>${g.kind}</td><td>${esc(g.node)}</td><td class="num">${g.status === "running" ? g.cpu + "%" : "—"}</td>
      <td class="num">${g.status === "running" ? Math.round(g.mem_pct) + "%" : "—"}</td><td class="num">${g.status === "running" ? dur(g.uptime) : esc(g.status)}</td></tr>`).join("")}
    </tbody></table>` : "";

  const uf = integ(state, "unifi").data;
  $("panel-network").className = uf ? "card panel" : "";
  $("panel-network").innerHTML = uf ? `<h2>UniFi devices</h2>
    <table><thead><tr><th>Device</th><th>Type</th><th>IP</th><th class="num">Clients</th><th class="num">Uptime</th></tr></thead><tbody>
    ${uf.devices.map((d) => `<tr><td><span class="dot ${d.online ? "ok" : "bad"}"></span>${esc(d.name)}${d.upgradable ? '<span class="badge">update</span>' : ""}<div class="muted" style="font-size:11px;margin-left:14px">${esc(d.model || "")}</div></td>
      <td>${esc(d.type || "")}</td><td>${esc(d.ip || "")}</td><td class="num">${d.online ? d.clients : "—"}</td><td class="num">${d.online ? dur(d.uptime) : "offline"}</td></tr>`).join("")}
    </tbody></table>` : "";

  const tn = integ(state, "truenas").data;
  const storage = (pve?.storage || []);
  const show = tn || storage.length;
  $("panel-storage").className = show ? "card panel" : "";
  $("panel-storage").innerHTML = show ? `<h2>Storage</h2>
    ${storage.length ? `<div class="sub-h muted" style="font-size:12px">Proxmox storage</div>${storage.map((s) => meter(s.shared ? s.name : `${s.name} (${s.node})`, s.pct, `${Math.round(s.pct)}%`, "wide")).join("")}` : ""}
    ${tn?.alerts?.length ? `<div class="sub-h muted" style="font-size:12px">TrueNAS alerts</div>${tn.alerts.map((a) => `<div class="alert ${esc(a.level)}"><b>${esc(a.level)}</b><span>${esc(a.text)}</span></div>`).join("")}` : ""}
    ${tn?.replications?.length ? `<div class="sub-h muted" style="font-size:12px">Replication</div>
      <table><tbody>${tn.replications.map((r) => `<tr><td><span class="dot ${r.state === "SUCCESS" ? "ok" : r.state === "RUNNING" ? "warn" : r.state ? "bad" : ""}"></span>${esc(r.name)}</td><td>${esc(r.state || "never run")}</td><td class="num">${ago(r.at, now)}</td></tr>`).join("")}</tbody></table>` : ""}
    ` : "";
}

// ---------- main loop ----------
function render(state) {
  last = state;
  document.title = state.title;
  $("title").textContent = state.title;
  renderPills(state); renderWidgets(state); renderServices(state); renderPanels(state);
  tickClock();
  $("footer").textContent = state.updated ? `Updated ${new Date(state.updated * 1000).toLocaleTimeString([], tz())}` : "Waiting for first poll…";
}

async function refresh() {
  try {
    const r = await fetch("/api/state", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    render(await r.json());
  } catch (e) {
    $("footer").textContent = `Dashboard backend unreachable (${e.message}) — retrying`;
  }
}

$("search").addEventListener("input", () => last && renderServices(last));
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== $("search")) { e.preventDefault(); $("search").focus(); }
  if (e.key === "Escape") { $("search").value = ""; last && renderServices(last); $("search").blur(); }
});
tickClock(); setInterval(tickClock, 1000);
refresh(); setInterval(refresh, REFRESH_MS);
