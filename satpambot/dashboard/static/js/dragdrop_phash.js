
(function(){
  const API_UPLOAD = "/dashboard/api/phash/upload";
  const API_LIST   = "/api/phish/phash"; // GET only

  function $(sel){ return document.querySelector(sel); }

  function ensureLogBox(anchor){
    let box = document.getElementById("upload-log");
    if (!box){
      box = document.createElement("div");
      box.id = "upload-log";
      box.style.marginTop = "8px";
      box.style.fontSize = "12px";
      box.style.opacity = "0.95";
      box.style.lineHeight = "1.3";
      (anchor.parentElement || document.body).appendChild(box);
    }
    return box;
  }

  function pushLog(ok, msg){
    const box = ensureLogBox($('#dropZone') || document.querySelector('[data-dropzone]') || document.querySelector('.dropzone') || document.body);
    const row = document.createElement("div");
    row.textContent = (ok?"✓ ":"✗ ") + msg;
    row.style.color = ok ? "#16a34a" : "#f59e0b";
    box.prepend(row);
    while (box.childElementCount > 6) box.lastChild.remove();
  }

  async function refreshList(){
    try {
      const r = await fetch(API_LIST, {method:"GET"});
      if (!r.ok) return;
      const j = await r.json();
      const n = Array.isArray(j) ? j.length : (j && j.phash && j.phash.length) || 0;
      pushLog(true, "List updated ("+n+")");
    } catch(e){}
  }

  async function uploadFile(file){
    const fd = new FormData();
    fd.append("file", file, file.name || "image");
    const r = await fetch(API_UPLOAD, { method:"POST", body: fd });
    if (!r.ok) throw new Error("upload failed ("+r.status+")");
    await r.json().catch(()=>({}));
    pushLog(true, "Uploaded "+(file.name||"image"));
    await refreshList();
  }

  async function uploadUrl(url){
    const r = await fetch(API_UPLOAD, {
      method:"POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({url})
    });
    if (!r.ok) throw new Error("upload url failed ("+r.status+")");
    await r.json().catch(()=>({}));
    pushLog(true, "Uploaded URL");
    await refreshList();
  }

  function bindDrop(){
    const dz = $('#dropZone') || document.querySelector('[data-dropzone]') || document.querySelector('.dropzone');
    if (!dz) return;

    ensureLogBox(dz);

    ["dragenter","dragover"].forEach(ev=>dz.addEventListener(ev, e=>{
      e.preventDefault(); e.stopPropagation();
      dz.classList.add("dragging");
    }));
    ["dragleave","drop"].forEach(ev=>dz.addEventListener(ev, e=>{
      e.preventDefault(); e.stopPropagation();
      dz.classList.remove("dragging");
    }));

    dz.addEventListener("drop", async (e)=>{
      const files = e.dataTransfer && e.dataTransfer.files;
      const text  = (e.dataTransfer && (e.dataTransfer.getData("text") || e.dataTransfer.getData("text/plain"))) || "";
      const tasks = [];
      if (files && files.length){
        for (const f of files){
          if (f.type && !f.type.startsWith("image")) { pushLog(false, "Skip non-image "+(f.name||"file")); continue; }
          tasks.push(uploadFile(f));
        }
      }
      if (text && /^https?:\/\//i.test(text)){
        tasks.push(uploadUrl(text.trim()));
      }
      try{ await Promise.all(tasks); }catch(err){ pushLog(false, String(err)); }
    });

    // Paste support
    window.addEventListener("paste", async (e)=>{
      const items = e.clipboardData && e.clipboardData.items;
      if (!items) return;
      const tasks = [];
      for (const it of items){
        if (it.kind === "file"){
          const f = it.getAsFile();
          if (f) tasks.push(uploadFile(f));
        } else if (it.kind === "string"){
          it.getAsString(s=>{ if(/^https?:\/\//i.test(s.trim())) uploadUrl(s.trim()); });
        }
      }
      try{ await Promise.all(tasks); }catch(err){ pushLog(false, String(err)); }
    });
  }

  document.addEventListener("DOMContentLoaded", bindDrop);
})();
