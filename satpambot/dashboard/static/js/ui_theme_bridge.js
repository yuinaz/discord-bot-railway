
(async function(){
  try{
    const res = await fetch('/api/ui-config', {credentials:'include'});
    if(!res.ok) return;
    const cfg = await res.json();
    const root = document.documentElement;
    const theme = (cfg.theme||'').toLowerCase();
    ['theme-light','ocean','nord','dracula','forest'].forEach(c=>root.classList.remove(c));
    if(theme==='light') root.classList.add('theme-light');
    if(theme==='ocean') root.classList.add('ocean');
    if(theme==='nord') root.classList.add('nord');
    if(theme==='dracula') root.classList.add('dracula');
    if(theme==='forest') root.style.setProperty('--bg1','#5A7F58'), root.style.setProperty('--bg2','#3E5C76');

    // Accent color
    if(cfg.accent_color){
      root.style.setProperty('--accent', cfg.accent_color);
    }

    // Background mode
    const mode = (cfg.background_mode||'').toLowerCase();
    const url = cfg.background_url;
    if(mode==='image' && url){
      document.body.style.background = `url('${url}') center/cover fixed no-repeat`;
    }else if(mode==='video' && url){
      const v = document.createElement('video');
      v.src = url; v.autoplay = true; v.loop = true; v.muted = true;
      v.style.cssText = 'position:fixed;inset:0;min-width:100%;min-height:100%;object-fit:cover;z-index:-1;';
      document.body.appendChild(v);
    } // particles mode handled by separate script if present
  }catch(e){}
})();
