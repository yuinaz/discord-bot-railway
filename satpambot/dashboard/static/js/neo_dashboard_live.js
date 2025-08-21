(function(){
  async function j(u){ try{ const r=await fetch(u); return await r.json(); }catch(e){ return null; } }
  async function t(){
    const d = await j('/api/live/stats'); if(!d) return;
    let el;
    el=document.querySelector('[data-live="guilds"]');   if(el) el.textContent = d.guilds||0;
    el=document.querySelector('[data-live="members"]');  if(el) el.textContent = d.members||0;
    el=document.querySelector('[data-live="online"]');   if(el) el.textContent = d.online||0;
    el=document.querySelector('[data-live="latency"]');  if(el) el.textContent = (d.latency_ms||0)+' ms';
  }
  setInterval(t, 3000); t();
  console.log('[neo_dashboard_live] running');
})();
