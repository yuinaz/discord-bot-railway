
// Robust Theme Bridge: fetch UI config -> apply; also reflects form fields if present
(async function(){
  function applyTheme(cfg){
    const html = document.documentElement;
    const theme = (cfg.theme || 'dark').toLowerCase();
    html.setAttribute('data-theme', theme);
    const acc = cfg.accent || cfg.accent_color || '#2563eb';
    document.documentElement.style.setProperty('--acc', acc);
  }

  async function fetchCfg(){
    try{
      const r = await fetch('/api/ui-config', {cache:'no-store'});
      if(r.ok) return await r.json();
    }catch(e){}
    // fallback localStorage (if backend belum ready)
    try{
      return JSON.parse(localStorage.getItem('neo.ui')||'{}');
    }catch(e){ return {}; }
  }

  const cfg = await fetchCfg();
  applyTheme(cfg);

  // mirror ke form bila ada
  const selTheme = document.querySelector('[data-ui="theme"]');
  const inpAccent = document.querySelector('[data-ui="accent"]');
  const selBgMode = document.querySelector('[data-ui="bgmode"]');
  const inpBgUrl  = document.querySelector('[data-ui="bgurl"]');
  const chkLogin  = document.querySelector('[data-ui="applylogin"]');
  if(selTheme) selTheme.value = (cfg.theme||'dark');
  if(inpAccent) inpAccent.value = (cfg.accent||cfg.accent_color||'#2563eb');
  if(selBgMode) selBgMode.value = (cfg.bg_mode||'None');
  if(inpBgUrl)  inpBgUrl.value  = (cfg.bg_url||'');
  if(chkLogin)  chkLogin.checked = !!cfg.apply_login;
})();
