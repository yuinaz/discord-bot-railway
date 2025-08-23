// satpambot/dashboard/static/js/dragdrop_phash.js
// Non-breaking enhancer: accept FILE or URL; upload to /dashboard/api/phash/upload;
// fallback to /api/phish/phash if available; refresh banned users + metrics.
(function(){
  const TRY_ENDPOINTS = ["/dashboard/api/phash/upload", "/api/phish/phash"];
  const API_BANS = "/dashboard/api/banned_users";
  const API_METRICS = "/dashboard/api/metrics";

  function $(s, r){ return (r||document).querySelector(s); }
  function $all(s, r){ return Array.from((r||document).querySelectorAll(s)); }

  async function postFileOrUrl(file, url){
    for (const ep of TRY_ENDPOINTS) {
      try {
        if (file){
          const fd = new FormData();
          fd.append("file", file, file.name||"image");
          const r = await fetch(ep, {method:"POST", body:fd}); const j=await r.json();
          if (!r.ok || j.ok===false) throw new Error(j.error||r.status);
          return j;
        } else if (url){
          const r = await fetch(ep, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({url})});
          const j = await r.json(); if (!r.ok || j.ok===false) throw new Error(j.error||r.status);
          return j;
        }
      } catch(e){ /* try next */ }
    }
    throw new Error("No phash endpoint available.");
  }

  function bindDropzones(){
    const zones = $all("#dropZone, [data-dropzone], .dropzone, .drop");
    zones.forEach(z => {
      z.addEventListener("dragover", e => { e.preventDefault(); z.classList.add("dragging"); });
      z.addEventListener("dragleave", () => z.classList.remove("dragging"));
      z.addEventListener("drop", e => {
        e.preventDefault(); z.classList.remove("dragging");
        const dt = e.dataTransfer;
        const tasks = [];
        if (dt.files && dt.files.length) {
          for (const f of dt.files) tasks.push(postFileOrUrl(f,null));
        }
        for (const item of dt.items||[]) {
          if (item.kind==="string" && (item.type==="text/uri-list"||item.type==="text/plain")){
            tasks.push(new Promise(resolve=>{
              item.getAsString(async s => {
                const m=(s||"").match(/https?:\/\/\S+/); const u=m?m[0]:s;
                try{ resolve(await postFileOrUrl(null, u)); }catch(e){ resolve({ok:false,error:String(e)}) }
              });
            }));
          }
        }
        Promise.all(tasks).then(()=>{ refreshBans(); });
      });
    });
    document.addEventListener("paste", e => {
      const dt = e.clipboardData || window.clipboardData; if (!dt) return;
      if (dt.files && dt.files.length) { postFileOrUrl(dt.files[0], null).then(refreshBans); return; }
      const s = dt.getData("text"); if (s) { postFileOrUrl(null, s).then(refreshBans); }
    });
  }

  function mountBansCard(){
    if ($("#bans-card")) return;
    const card = document.createElement("div");
    card.id="bans-card"; card.className="card"; card.style.marginTop="1rem";
    card.innerHTML = `<div class="card-body">
      <div class="d-flex justify-content-between align-items-center" style="margin-bottom:.5rem">
        <div style="font-weight:600">Banned Users (live)</div>
        <button id="bans-refresh" class="btn btn-sm">Refresh</button>
      </div>
      <div class="table-responsive">
        <table class="table"><thead><tr><th>Time</th><th>User</th><th>ID</th><th>Reason</th><th>By</th></tr></thead><tbody id="bans-tbody"><tr><td colspan="5">Loading...</td></tr></tbody></table>
      </div></div>`;
    const anchor = document.querySelector(".card, #dropZone") || document.body;
    anchor.parentElement?.appendChild(card);
    $("#bans-refresh")?.addEventListener("click", ()=>refreshBans(true));
  }

  async function refreshBans(){
    try{
      const r = await fetch(API_BANS); const j = await r.json();
      const tb = $("#bans-tbody"); if (!tb) return;
      tb.innerHTML = "";
      (j.rows||[]).forEach(rw => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${rw.time_human||rw.time||""}</td><td>${rw.username||"-"}</td><td>${rw.user_id||"-"}</td><td>${rw.reason||"-"}</td><td>${rw.mod||"-"}</td>`;
        tb.appendChild(tr);
      });
      if (!j.rows?.length) tb.innerHTML = `<tr><td colspan="5" style="opacity:.7">Belum ada data ban.</td></tr>`;
    }catch(e){}
  }

  async function tickMetrics(){
    try{
      const r = await fetch(API_METRICS); const j = await r.json();
      const idset = [["stat-guilds","guilds"],["stat-members","members"],["stat-online","online"],["stat-channels","channels"],["stat-threads","threads"],["stat-latency","latency_ms"]];
      idset.forEach(([id,k])=>{ const el = document.getElementById(id); if (el && k in j) el.textContent = k==="latency_ms" ? (j[k]+" ms") : j[k]; });
    }catch(e){}
  }

  function boot(){
    bindDropzones();
    mountBansCard();
    refreshBans();
    tickMetrics();
    setInterval(refreshBans, 10000);
    setInterval(tickMetrics, 5000);
  }
  if (document.readyState==="loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
