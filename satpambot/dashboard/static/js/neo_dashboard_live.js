(function(){
  async function j(u){ try{ const r=await fetch(u); return await r.json(); } catch(e){ return null; } }
  async function t(){
    const d = await j('/api/live/stats'); if(!d) return;
    const bind = (sel, val) => { const el=document.querySelector(sel); if(el) el.textContent = val; };
    bind('[data-live="guilds"]', d.guilds||0);
    bind('[data-live="members"]', d.members||0);
    bind('[data-live="online"]', d.online||0);
    bind('[data-live="channels"]', d.channels||0);
    bind('[data-live="threads"]', d.threads||0);
    bind('[data-live="latency"]', (d.latency_ms||0)+' ms');
  }
  setInterval(t, 2500); t();
  console.log('[neo_dashboard_live] applied');
})();
