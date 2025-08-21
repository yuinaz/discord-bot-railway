(function(){
  async function getPhash(){
    try{
      const r = await fetch('/api/phish/phash', {cache:'no-store'});
      if(!r.ok) return;
      const d = await r.json();
      const arr = Array.isArray(d.phash) ? d.phash : [];
      document.getElementById('phashCount').textContent = arr.length;
      document.getElementById('phashPreview').textContent = JSON.stringify(arr.slice(0,100), null, 2);
    }catch(e){}
  }
  async function exportPhash(){
    const r = await fetch('/api/phish/phash', {cache:'no-store'});
    if(!r.ok) return;
    const blob = new Blob([await r.text()], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'phash_export.json';
    a.click(); URL.revokeObjectURL(a.href);
  }
  async function upload(file){
    const log = document.getElementById('uploadLog');
    const fd = new FormData(); fd.append('file', file, file.name);
    try{
      const r = await fetch('/dashboard/security/upload', {method:'POST', body: fd});
      const j = await r.json();
      if(r.ok && j.ok){ log.innerHTML += `✅ ${file.name} -> ${j.saved}<br>`; }
      else{ log.innerHTML += `❌ ${file.name} gagal (${j.error||r.status})<br>`; }
    }catch(e){ log.innerHTML += `❌ ${file.name} error<br>`; }
  }
  function wireDrop(){
    const drop = document.getElementById('dropZone');
    const pick = document.getElementById('fileInput');
    drop.addEventListener('click', ()=>pick.click());
    pick.addEventListener('change', e=>{
      for(const f of e.target.files) upload(f);
      pick.value = '';
    });
    ['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev, e=>{
      e.preventDefault(); e.stopPropagation(); drop.classList.add('dragover');
    }));
    ['dragleave','drop'].forEach(ev=>drop.addEventListener(ev, e=>{
      e.preventDefault(); e.stopPropagation(); drop.classList.remove('dragover');
    }));
    drop.addEventListener('drop', e=>{
      const files = e.dataTransfer?.files || [];
      for(const f of files) upload(f);
    });
  }
  window.addEventListener('DOMContentLoaded', ()=>{
    document.getElementById('btnRefresh')?.addEventListener('click', getPhash);
    document.getElementById('btnExport')?.addEventListener('click', exportPhash);
    wireDrop(); getPhash();
  });
})();
