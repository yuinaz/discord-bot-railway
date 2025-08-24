// satpambot/dashboard/static/js/dragdrop_phash.js
// Robust drag & drop + paste + click-to-upload for dashboard.
// Tries /dashboard/api/phash/upload (auth) then /api/phish/phash (public).
// Also refreshes bans + metrics after upload.
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
          fd.append("file", file, file.name || "upload.bin");
          const r = await fetch(ep, { method:"POST", body: fd });
          const j = await r.json().catch(()=>({ok:false}));
          if (!r.ok || j.ok===false) throw new Error(j.error||r.status);
          return j;
        }else if (url){
          const fd = new FormData();
          fd.append("url", url);
          const r = await fetch(ep, { method:"POST", body: fd });
          const j = await r.json().catch(()=>({ok:false}));
          if (!r.ok || j.ok===false) throw new Error(j.error||r.status);
          return j;
        }
      } catch(e){ /* try next ep */ }
    }
    throw new Error("No phash endpoint available.");
  }

  async function refreshBans(){
    try {
      const r = await fetch(API_BANS);
      const j = await r.json();
      const t = $("#banTableBody"); if (!t) return;
      t.innerHTML = "";
      if (!j || !Array.isArray(j.items) || j.items.length===0){
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="3" class="muted">Belum ada data ban.</td>`;
        t.appendChild(tr);
        return;
      }
      for (const row of j.items){
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${row.time||"-"}</td><td>${row.user_id||"-"}</td><td>${row.reason||"-"}</td>`;
        t.appendChild(tr);
      }
    }catch(e){ /* noop */ }
  }

  async function tickMetrics(){
    try{
      const r = await fetch(API_METRICS);
      const j = await r.json();
      const idset = [
        ["mm_cpu","cpu_percent"],
        ["mm_ram","ram_mb"],
        ["mm_online","online"],
        ["mm_members","members"],
        ["mm_channels","channels"],
        ["mm_threads","threads"],
        ["mm_latency","latency_ms"],
      ];
      idset.forEach(([id,k])=>{
        const el = document.getElementById(id);
        if (el && j && k in j) el.textContent = (k==="latency_ms") ? (j[k]+" ms") : j[k];
      });
    }catch(e){ /* noop */ }
  }

  function handleFiles(files){
    const tasks = [];
    for (const f of files) tasks.push(postFileOrUrl(f, null));
    Promise.allSettled(tasks).then(()=>{ refreshBans(); });
  }

  function bindDropzones(){
    const zones = $all("#dropZone, [data-dropzone], .dropzone, .drop");
    zones.forEach(z => {
      // visual
      z.addEventListener("dragover", e => { e.preventDefault(); z.classList.add("dragging"); });
      z.addEventListener("dragleave", () => z.classList.remove("dragging"));
      z.addEventListener("drop", e => {
        e.preventDefault(); z.classList.remove("dragging");
        const dt = e.dataTransfer;
        const tasks = [];
        // files
        if (dt && dt.files && dt.files.length){
          handleFiles(dt.files);
          return;
        }
        // url/text
        for (const item of (dt?.items||[])){
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

      // click to open hidden input
      const fileInput = $("#dashDrop") || $("#fileInput") || $("#dzFile");
      if (fileInput){
        z.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", (e)=>{
          const files = e.target.files || [];
          if (files.length) handleFiles(files);
          e.target.value = "";
        });
      }
    });

    // global prevent default so browser doesn't navigate away when dropping outside zone
    document.addEventListener("dragover", e => e.preventDefault());
    document.addEventListener("drop", e => e.preventDefault());

    // paste support (images/urls)
    document.addEventListener("paste", e => {
      const dt = e.clipboardData;
      if (!dt) return;
      const files = Array.from(dt.files||[]);
      if (files.length){ handleFiles(files); return; }
      const s = dt.getData("text/plain") || "";
      if (s){ postFileOrUrl(null, s).then(()=>refreshBans()).catch(()=>{}); }
    });
  }

  function boot(){
    bindDropzones();
    refreshBans();
    tickMetrics();
    setInterval(refreshBans, 10000);
    setInterval(tickMetrics, 5000);
  }

  if (document.readyState==="loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
