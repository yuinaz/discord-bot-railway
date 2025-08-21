(function(){
  function setText(id, val){ var el = document.getElementById(id); if(el) el.textContent = val; }
  async function tick(){
    try{
      const res = await fetch('/api/live/stats', { cache: 'no-store' });
      const data = await res.json();
      const m = Object.assign({guilds:0,members:0,channels:0,threads:0,online:0,latency_ms:0, ts: Date.now()/1000}, data||{});
      setText('stat-guilds', m.guilds);
      setText('stat-members', m.members);
      setText('stat-channels', m.channels);
      setText('stat-threads', m.threads);
      setText('stat-online', m.online);
      setText('stat-latency_ms', m.latency_ms);
      var t = document.getElementById('stat-updated');
      if (t){
        const d = new Date((m.ts||Date.now()/1000)*1000);
        t.textContent = d.toLocaleTimeString();
      }
    }catch(e){
      console.warn('[live] failed', e);
    }
  }
  setInterval(tick, 3000);
  tick();
  console.log('[neo_dashboard_live] ready');
})();
