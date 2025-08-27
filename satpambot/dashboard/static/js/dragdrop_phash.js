(function () {
  const zone = document.querySelector('[data-dropzone], .dropzone, #dropzone, #drop-zone');
  if (!zone) return;

  let log = document.getElementById('upload-log');
  if (!log) {
    log = document.createElement('div');
    log.id = 'upload-log';
    log.style.marginTop = '10px';
    log.style.fontFamily = 'system-ui, Segoe UI, Roboto, sans-serif';
    zone.insertAdjacentElement('afterend', log);
  }
  const pushLog = (html, cls) => {
    const item = document.createElement('div');
    item.innerHTML = html;
    item.style.padding = '4px 8px';
    item.style.borderRadius = '6px';
    item.style.margin = '4px 0';
    if (cls === 'ok') { item.style.background = 'rgba(16,185,129,.12)'; item.style.color = '#10b981'; }
    else if (cls === 'warn') { item.style.background = 'rgba(245,158,11,.12)'; item.style.color = '#f59e0b'; }
    else { item.style.background = 'rgba(239,68,68,.12)'; item.style.color = '#ef4444'; }
    log.prepend(item);
    while (log.children.length > 6) log.removeChild(log.lastChild);
  };

  const apiUpload = '/dashboard/api/phash/upload';
  const apiList   = '/api/phish/phash';

  const prevent = (e) => { e.preventDefault(); e.stopPropagation(); };
  ['dragenter','dragover','dragleave','drop'].forEach(ev => zone.addEventListener(ev, prevent, false));

  const handleFiles = async (files) => {
    for (const f of files) {
      if (!f.type || !f.type.startsWith('image/')) { pushLog('⚠️ Bukan gambar, dilewati: ' + (f.name || 'unknown'), 'warn'); continue; }
      const fd = new FormData(); fd.append('file', f, f.name || 'image');
      try {
        const r = await fetch(apiUpload, {method: 'POST', body: fd});
        if (!r.ok) throw new Error('HTTP ' + r.status);
        pushLog('✓ Uploaded <b>' + (f.name || 'image') + '</b>', 'ok');
        fetch(apiList).catch(()=>{});
      } catch (err) { pushLog('✗ Gagal upload ' + (f.name || 'image') + ': ' + err, 'err'); }
    }
  };

  zone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length) {
      handleFiles(dt.files);
    } else if (dt && dt.getData) {
      const url = dt.getData('text/uri-list') || dt.getData('text/plain');
      if (url && /^https?:\/\//i.test(url)) {
        const body = JSON.stringify({url});
        fetch(apiUpload, {method:'POST', headers:{'Content-Type':'application/json'}, body})
          .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); pushLog('✓ URL diunggah', 'ok'); fetch(apiList).catch(()=>{}); })
          .catch(err => pushLog('✗ Gagal unggah URL: ' + err, 'err'));
      }
    }
  });

  document.addEventListener('paste', (e) => {
    const items = (e.clipboardData || window.clipboardData).items;
    if (!items) return;
    const files = [];
    for (const it of items) {
      if (it.kind === 'file') { const file = it.getAsFile(); if (file) files.push(file); }
      else if (it.kind === 'string') {
        it.getAsString((s) => {
          if (/^https?:\/\//i.test(s)) {
            const body = JSON.stringify({url: s.trim()});
            fetch(apiUpload, {method:'POST', headers:{'Content-Type':'application/json'}, body})
              .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); pushLog('✓ URL ditempel', 'ok'); fetch(apiList).catch(()=>{}); })
              .catch(err => pushLog('✗ Gagal unggah URL: ' + err, 'err'));
          }
        });
      }
    }
    if (files.length) handleFiles(files);
  });

  zone.addEventListener('dragover', () => zone.style.outline = '2px dashed #10b981');
  zone.addEventListener('dragleave', () => zone.style.outline = '');
  zone.addEventListener('drop', () => zone.style.outline = '');
})();
