
(async function(){
  const $ = sel => document.querySelector(sel);
  const api = async (url, opt={}) => (await fetch(url, opt)).json();
  try {
    const t = await api('/api/themes');
    const sel = $('#theme'); sel.innerHTML='';
    (t.themes || []).forEach(name => {
      const o = document.createElement('option'); o.textContent = name; o.value = name;
      sel.appendChild(o);
    });
  } catch(e){ console.warn('themes load failed', e); }

  let cfg = await api('/api/ui-config').catch(()=>({}));
  $('#theme').value = cfg.theme || 'Dark';
  $('#accent').value = cfg.accent || '#2563eb';
  $('#bg_mode').value = cfg.bg_mode || 'None';
  $('#bg_url').value = cfg.bg_url || '';
  $('#logo_url').value = cfg.logo_url || '';
  $('#apply_login').checked = !!cfg.apply_login;

  const postCfg = async (patch) => {
    const body = Object.assign({}, cfg, patch);
    const res = await api('/api/ui-config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    cfg = res.config || body;
    return res;
  };

  $('#set_bg_url').onclick = () => postCfg({bg_url: $('#bg_url').value});
  $('#set_logo_url').onclick = () => postCfg({logo_url: $('#logo_url').value});

  $('#upload_bg').onclick = async () => {
    const f = $('#bg_file').files[0]; if(!f) return;
    const fd = new FormData(); fd.append('file', f);
    const j = await (await fetch('/api/upload/background?apply=1', {method:'POST', body:fd})).json();
    if(j.path){ $('#bg_url').value = j.path; await postCfg({bg_url:j.path}); }
  };
  $('#upload_logo').onclick = async () => {
    const f = $('#logo_file').files[0]; if(!f) return;
    const fd = new FormData(); fd.append('file', f);
    const j = await (await fetch('/api/upload/logo', {method:'POST', body:fd})).json();
    if(j.path){ $('#logo_url').value = j.path; await postCfg({logo_url:j.path}); }
  };

  $('#save').onclick = () => postCfg({
    theme: $('#theme').value,
    accent: $('#accent').value,
    bg_mode: $('#bg_mode').value,
    bg_url: $('#bg_url').value,
    logo_url: $('#logo_url').value,
    apply_login: $('#apply_login').checked
  });

  $('#preview').onclick = () => window.open('/login','_blank');
})();
