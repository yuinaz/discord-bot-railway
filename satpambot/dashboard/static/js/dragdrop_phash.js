
// satpambot/dashboard/static/js/dragdrop_phash.js
// Robust drag&drop/paste for phishing images (files OR links) + small UI helpers.
// Also mounts a Live Banned Users card below the dashboard widgets without
// requiring template changes.

(function () {
  const API_UPLOAD = "/dashboard/api/phash/upload";
  const API_BANS   = "/dashboard/api/banned_users?limit=50";
  const API_METRICS = "/dashboard/api/metrics";

  function $(sel, root) { return (root||document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root||document).querySelectorAll(sel)); }
  function isImgUrl(s) {
    if (!s) return false;
    try { new URL(s); } catch { return false; }
    return /\.(png|jpe?g|gif|webp|bmp|tiff?)($|\?)/i.test(s);
  }

  // --- UI helpers ---
  function ensureStatusArea() {
    let el = document.getElementById("phash-status");
    if (!el) {
      el = document.createElement("div");
      el.id = "phash-status";
      el.style.fontSize = "0.9rem";
      el.style.opacity = "0.9";
      el.style.marginTop = "6px";
      const dz = guessPrimaryDropzone();
      (dz?.parentElement || document.body).appendChild(el);
    }
    return el;
  }
  function setStatus(msg) {
    const el = ensureStatusArea();
    el.textContent = msg;
  }
  function toast(msg) {
    console.log("[phish-lab]", msg);
    setStatus(msg);
  }

  // --- Dropzone discovery (tries to match existing "Drop files here..." blocks) ---
  function guessDropzones() {
    const cand = [];
    // Common conventions
    $all('[data-dropzone], .dropzone, #dropzone, #phish-dropzone, [id*="drop"]').forEach(el => {
      if (!cand.includes(el)) cand.push(el);
    });
    // Heuristic: elements whose text contains "Drop files here"
    $all("*").forEach(el => {
      if (el.childElementCount === 0) {
        const t = (el.textContent || "").trim().toLowerCase();
        if (t.includes("drop files here")) {
          const box = el.closest(".card, .box, .panel, .dashed, div");
          if (box && !cand.includes(box)) cand.push(box);
        }
      }
    });
    return cand;
  }
  function guessPrimaryDropzone() {
    return guessDropzones()[0] || document.body;
  }

  // --- Upload logic ---
  async function uploadFile(file) {
    const fd = new FormData();
    fd.append("file", file, file.name || "image");
    const res = await fetch(API_UPLOAD, { method: "POST", body: fd });
    const j = await res.json().catch(() => ({}));
    if (!res.ok || !j.ok) throw new Error(j.error || ("HTTP "+res.status));
    return j;
  }
  async function uploadUrl(url) {
    const res = await fetch(API_UPLOAD, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ url })
    });
    const j = await res.json().catch(() => ({}));
    if (!res.ok || !j.ok) throw new Error(j.error || ("HTTP "+res.status));
    return j;
  }

  async function handleDataTransfer(dt) {
    const tasks = [];
    // 1) Files
    if (dt.files && dt.files.length) {
      for (const f of dt.files) tasks.push(uploadFile(f));
    }
    // 2) Links from dragged selection
    for (const item of dt.items || []) {
      if (item.kind === "string") {
        // URI list takes priority
        if (item.type === "text/uri-list" || item.type === "text/plain") {
          tasks.push(new Promise(resolve => {
            item.getAsString(async (s) => {
              try {
                s = (s||"").trim();
                // text/plain may contain extra text; snip first URL-like token
                const m = s.match(/https?:\/\/\S+/);
                const url = m ? m[0] : s;
                if (isImgUrl(url)) {
                  const r = await uploadUrl(url);
                  resolve(r);
                } else {
                  resolve({ ok:false, skipped:true });
                }
              } catch (e) { resolve({ ok:false, error:String(e) }); }
            });
          }));
        }
      }
    }
    if (!tasks.length) throw new Error("No file or image URL detected.");
    setStatus("Uploading...");
    const results = await Promise.all(tasks);
    const okCount = results.filter(r => r && r.ok).length;
    const skip = results.filter(r => r && r.skipped).length;
    toast(`Uploaded: ${okCount}${skip?` (skipped ${skip})`:""}.`);
    refreshBans();
  }

  function bindDropzones() {
    const zones = guessDropzones();
    zones.forEach(z => {
      z.addEventListener("dragover", (e) => { e.preventDefault(); z.classList.add("dragging"); }, false);
      z.addEventListener("dragleave", () => z.classList.remove("dragging"), false);
      z.addEventListener("drop", (e) => {
        e.preventDefault();
        z.classList.remove("dragging");
        handleDataTransfer(e.dataTransfer).catch(err => toast("Upload failed: "+err.message));
      }, false);
    });
    // Also support document-level paste
    document.addEventListener("paste", (e) => {
      const dt = e.clipboardData || window.clipboardData;
      if (!dt) return;
      handleDataTransfer(dt).catch(err => toast("Upload failed: "+err.message));
    });
  }

  // --- Live Banned Users widget ---
  function mountBansCard() {
    if (document.getElementById("bans-card")) return;
    const card = document.createElement("div");
    card.id = "bans-card";
    card.className = "card";
    card.style.marginTop = "1rem";
    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center" style="margin-bottom:.5rem">
          <div style="font-weight:600">Banned Users (live)</div>
          <button id="bans-refresh" class="btn btn-sm">Refresh</button>
        </div>
        <div class="table-responsive">
          <table class="table" id="bans-table">
            <thead><tr><th>Time</th><th>User</th><th>ID</th><th>Reason</th><th>By</th></tr></thead>
            <tbody><tr><td colspan="5" style="opacity:.7">Loading...</td></tr></tbody>
          </table>
        </div>
      </div>`;
    // Insert after first dashboard metrics card if present, else append to main content
    const anchor = guessPrimaryDropzone();
    (anchor?.parentElement || document.body).appendChild(card);
    $("#bans-refresh")?.addEventListener("click", () => refreshBans(true));
  }

  async function refreshBans(manual) {
    try {
      const res = await fetch(API_BANS);
      const j = await res.json();
      const tbody = $("#bans-table tbody");
      if (!tbody) return;
      tbody.innerHTML = "";
      const rows = Array.isArray(j.rows) ? j.rows : [];
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="5" style="opacity:.7">Belum ada data ban.</td></tr>`;
      } else {
        for (const r of rows) {
          const tr = document.createElement("tr");
          const time = (r.time_human || r.ts_human || r.time || "").toString();
          tr.innerHTML = `<td>${time}</td><td>${r.username||"-"}</td><td>${r.user_id||"-"}</td><td>${r.reason||"-"}</td><td>${r.mod||r.moderator||"-"}</td>`;
          tbody.appendChild(tr);
        }
      }
      if (manual) toast("Banned users updated.");
    } catch (e) {
      console.error(e);
    }
  }

  // Optionally keep metrics alive if the page expects it
  async function tickMetrics() {
    try {
      const res = await fetch(API_METRICS);
      const j = await res.json();
      const map = {
        guilds: j.guilds ?? j.data?.guilds,
        members: j.members ?? j.data?.members,
        online: j.online ?? j.data?.online,
        channels: j.channels ?? j.data?.channels,
        threads: j.threads ?? j.data?.threads,
        latency_ms: j.latency_ms ?? j.data?.latency_ms
      };
      // Update any counters if elements exist
      const setText = (id, v) => { const el = document.getElementById(id); if (el && v != null) el.textContent = v; };
      setText("stat-guilds", map.guilds);
      setText("stat-members", map.members);
      setText("stat-online", map.online);
      setText("stat-channels", map.channels);
      setText("stat-threads", map.threads);
      setText("stat-latency", map.latency_ms ? (map.latency_ms + " ms") : "-- ms");
    } catch {}
  }

  function boot() {
    bindDropzones();
    mountBansCard();
    refreshBans();
    tickMetrics();
    // periodic refresh
    setInterval(tickMetrics, 5000);
    setInterval(refreshBans, 10000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
