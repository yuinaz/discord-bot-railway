
document.addEventListener('DOMContentLoaded', () => {
  const dz = document.getElementById('phishDrop');
  const input = document.getElementById('phishFile');
  const res = document.getElementById('phishResult');
  const urlInput = document.getElementById('phishUrl');
  const urlBtn = document.getElementById('phishUrlBtn');
  if (!dz) return;
  const setMsg = (t) => { if (res) res.textContent = t; };

  const uploadFiles = async (files) => {
    if (!files || !files.length) return;
    const fd = new FormData();
    for (const f of files) fd.append('files', f);
    setMsg('Mengunggah dan membuat signature…');
    try {
      const r = await fetch('/api/phish/images', { method: 'POST', body: fd });
      const j = await r.json().catch(()=>({}));
      if (!r.ok) throw new Error(j.error || r.statusText);
      setMsg(`OK: ditambahkan ${j.added||0} signature. threshold=${j.threshold} • autoban=${j.autoban?'ON':'OFF'}.`);
    } catch (e) {
      setMsg('Gagal: ' + (e.message || e));
    }
  };

  dz.addEventListener('click', () => input && input.click());
  input && input.addEventListener('change', (e) => {
    uploadFiles(e.target.files);
    e.target.value = '';
  });

  ['dragenter','dragover'].forEach(ev => dz.addEventListener(ev, (e)=>{ e.preventDefault(); e.stopPropagation(); dz.classList.add('hover'); }));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, (e)=>{ e.preventDefault(); e.stopPropagation(); dz.classList.remove('hover'); }));
  dz.addEventListener('drop', (e) => {
    uploadFiles(e.dataTransfer.files);
  });

  urlBtn && urlBtn.addEventListener('click', async () => {
    const val = (urlInput && urlInput.value || '').trim();
    if (!val) return;
    setMsg('Menambahkan URL…');
    try {
      const r = await fetch('/api/phish/urls', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ url: val }) });
      const j = await r.json().catch(()=>({}));
      if (!r.ok) throw new Error(j.error || r.statusText);
      setMsg(`OK: URL ditambahkan. total=${j.total||'-'}`);
      urlInput.value='';
    } catch (e) {
      setMsg('Gagal: ' + (e.message || e));
    }
  });
});
