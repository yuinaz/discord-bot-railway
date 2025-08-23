(function () {
  const dz = document.getElementById("dropzone");
  const out = document.getElementById("dz-result");
  if (!dz || !out) return;

  function show(msg){ out.insertAdjacentHTML("afterbegin", `<div class="dz-item">${msg}</div>`); }

  function handleFiles(files){
    if(!files || !files.length){ return; }
    const fd = new FormData();
    Array.from(files).forEach((f, i) => fd.append("files[]", f, f.name || `file_${i}.png`));

    fetch("/dashboard/api/phash/upload", { method: "POST", body: fd })
      .then(r => r.json())
      .then(d => {
        if (d.error){ show(`<span style="color:#ef4444">${d.error}</span>`); return; }
        (d.added || []).forEach(it => {
          const meta = it.filename ? ` <span class="muted">(${it.filename})</span>` : "";
          show(`✔️ <span class="hash">${it.hash}</span>${meta}`);
        });
        if (d.skipped && d.skipped.length){
          d.skipped.forEach(h => show(`⚠️ skipped (duplicate) <span class="hash">${h}</span>`));
        }
        if (typeof d.total === "number"){ show(`<em>Total hashes: ${d.total}</em>`); }
      })
      .catch(err => show(`<span style="color:#ef4444">Upload failed: ${String(err)}</span>`));
  }

  dz.addEventListener("dragover", e => { e.preventDefault(); dz.classList.add("hover"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("hover"));
  dz.addEventListener("drop", e => { e.preventDefault(); dz.classList.remove("hover"); handleFiles(e.dataTransfer.files); });
  dz.addEventListener("keydown", e => {
    if (e.key === "Enter"){
      const picker = document.createElement("input");
      picker.type = "file"; picker.accept = "image/*"; picker.multiple = true;
      picker.onchange = () => handleFiles(picker.files);
      picker.click();
    }
  });
})();
