/* 60fps lightweight chart + live stats hook */
(function(){
  const el = document.getElementById('activityChart');
  if (!el) return;
  const ctx = el.getContext('2d');
  const data = new Array(240).fill(0);
  let last = performance.now();
  function loop(t){
    const dt = Math.min(100, t - last); last = t;
    const v = (Math.sin(t/420)+Math.sin(t/1330)*.6 + Math.random()*0.2 + 1.8) * 18;
    data.push(v); data.shift();
    // Render
    const w = el.clientWidth, h = el.clientHeight;
    if (el.width !== w) el.width = w;
    if (el.height !== h) el.height = h;
    ctx.clearRect(0,0,w,h);
    ctx.lineWidth = 2;
    ctx.beginPath();
    const step = w / (data.length-1);
    ctx.moveTo(0, h - data[0]);
    for (let i=1;i<data.length;i++){
      const x = i*step, y = h - data[i];
      ctx.lineTo(x,y);
    }
    ctx.strokeStyle = 'rgba(180,210,255,.9)';
    ctx.stroke();
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
})();

// Live stats fill
(function(){
  function fill(s){
    const set = (id,val)=>{ var el=document.getElementById(id); if(el) el.textContent = val; }
    set('k_channels', s.channels||0);
    set('k_guilds', s.guilds||0);
    set('k_latency', s.latency_ms||0);
    set('k_members', s.members||0);
    set('k_online', s.online||0);
    set('k_threads', s.threads||0);
    var upd=document.getElementById('last_update');
    if (upd) upd.textContent = s.updated ? new Date(s.updated*1000).toLocaleTimeString() : '-';
  }
  async function poll(){
    try{
      const r = await fetch('/api/live/stats');
      if (r.ok){ fill(await r.json()); }
    }catch(e){}
    setTimeout(poll, 2000);
  }
  poll();
})();
