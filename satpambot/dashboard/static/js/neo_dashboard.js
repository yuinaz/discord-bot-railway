
(function(){
  const set = (id,v)=>{ const el=document.getElementById(id); if(el) el.textContent = (v ?? '--'); };
  function apply(data){
    try{
      set('stat-guilds', data.guilds);
      set('stat-members', data.members);
      set('stat-online', data.online);
      set('stat-channels', data.channels);
      set('stat-threads', data.threads);
      set('stat-latency', (data.latency_ms!=null? (Math.round(data.latency_ms)+'ms') : '--'));
      const dot = document.getElementById('live-indicator');
      if(dot){ dot.style.color = '#22c55e'; dot.title = 'live'; }
    }catch(e){}
  }

  function poll(){
    fetch('/api/discord/stats').then(r=>r.json()).then(apply).catch(()=>{});
  }

  try{
    const es = new EventSource('/api/discord/stream');
    es.onmessage = (ev)=>{ try{apply(JSON.parse(ev.data));}catch(e){} };
    es.onerror = ()=>{ es.close(); setInterval(poll, 5000); };
  }catch(e){
    setInterval(poll, 5000);
  }
  poll();
})();
