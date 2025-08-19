
(function(){
  function spark(el, arr){
    const c = el.getContext('2d');
    const w = el.width = el.clientWidth;
    const h = el.height = el.clientHeight;
    c.clearRect(0,0,w,h);
    if(!arr || !arr.length) return;
    const max = Math.max.apply(null, arr), min = Math.min.apply(null, arr);
    const pad = 6; const dx = (w-2*pad)/Math.max(arr.length-1,1);
    c.beginPath();
    arr.forEach((v,i)=>{
      const x = pad + i*dx;
      const y = h - pad - ( (v-min) / Math.max(max-min, 1) * (h-2*pad) );
      if(i===0) c.moveTo(x,y); else c.lineTo(x,y);
    });
    c.lineWidth = 2;
    c.strokeStyle = '#6ea8fe';
    c.stroke();
  }

  async function load(){
    try{
      const r = await fetch('/api/metrics');
      const j = await r.json();
      document.getElementById('kpi-up').textContent = j.uptime ? (Math.floor(j.uptime/60)+'m') : '--';
      document.getElementById('kpi-lat').textContent = j.latency_ms || '--';
      document.getElementById('kpi-total').textContent = j.total_msgs || '--';
      document.getElementById('kpi-g').textContent = j.guilds || '--';
      const tb = document.querySelector('#tbl-servers tbody');
      tb.innerHTML = '';
      (j.servers||[]).forEach(s=>{
        const tr = document.createElement('tr');
        const b = `<span class="badge ${s.status==='UP'?'up':'down'}">${s.status}</span>`;
        tr.innerHTML = `<td>${s.name}</td><td>${b}</td><td>${s.ping_ms||'--'}ms</td>`;
        tb.appendChild(tr);
      });
      document.querySelectorAll('canvas[data-spark]').forEach(cv=>{
        const key = cv.dataset.spark;
        spark(cv, (j.series||{})[key] || []);
      });
    }catch(e){ console.log(e); }
  }
  load(); setInterval(load, 5000);
})();
