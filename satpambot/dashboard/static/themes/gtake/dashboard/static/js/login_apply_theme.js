
// Apply theme & animated background on login (non-destructive)
(async function(){
  document.body.classList.add('login-hydrated');

  async function getCfg(){
    try{
      const r = await fetch('/api/ui-config', {cache:'no-store'});
      if(r.ok) return await r.json();
    }catch(e){}
    try{ return JSON.parse(localStorage.getItem('neo.ui')||'{}'); }catch(e){}
    return {};
  }

  function setTheme(cfg){
    const html = document.documentElement;
    const theme = (cfg.theme||'dark').toLowerCase();
    html.setAttribute('data-theme', theme);
    const acc = cfg.accent || cfg.accent_color || '#2563eb';
    html.style.setProperty('--acc', acc);
  }

  function applyBackground(cfg){
    // remove any previous
    if(window.__loginParticles) window.__loginParticles.destroy();
    const mode = (cfg.bg_mode||cfg.background_mode||'none').toLowerCase();
    if(mode === 'image' && cfg.bg_url){
      document.body.style.background = 'url('+encodeURI(cfg.bg_url)+') center/cover fixed no-repeat, var(--login-bg)';
    }else if(mode === 'particles'){
      document.body.style.background = 'var(--login-bg)';
      if(window.__loginParticles && typeof window.__loginParticles.init === 'function'){
        window.__loginParticles.init();
      }
    }else{
      document.body.style.background = 'var(--login-bg)';
    }
  }

  const cfg = await getCfg();
  if(!cfg.apply_login){ // if not opted in, just set theme vars and exit
    setTheme(cfg); return;
  }
  setTheme(cfg);

  // attach canvas script only when opted in
  const s = document.createElement('script'); s.src = "/dashboard-static/js/particles_60fps.js"; s.async = true;
  s.onload = ()=> applyBackground(cfg);
  document.head.appendChild(s);

  // optional: gently glassify card if user added id/class #login-card
  const card = document.getElementById('login-card');
  if(card) card.classList.add('login-card-glass');
})();
