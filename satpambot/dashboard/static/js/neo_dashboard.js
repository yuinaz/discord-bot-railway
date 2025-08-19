
(function(){
  const $ = (q)=>document.querySelector(q);
  const serversTbody = $("#serversTbl tbody");
  const changesTbody = $("#changesTbl tbody");
  const KV = {online:0,members:0,channels:0,threads:0};
  const sp = [$("#sp1"),$("#sp2"),$("#sp3"),$("#sp4")].map(c=>({el:c, data:[]}));
  function drawSpark(canvas, arr){
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.clientWidth;
    const h = canvas.height = canvas.clientHeight;
    ctx.clearRect(0,0,w,h);
    const max = Math.max(1, ...arr);
    ctx.beginPath();
    arr.forEach((v,i)=>{
      const x = (i/(arr.length-1||1))*w;
      const y = h - (v/max)*h;
      i?ctx.lineTo(x,y):ctx.moveTo(x,y);
    });
    ctx.strokeStyle = '#7aa8ff';
    ctx.lineWidth = 2;
    ctx.stroke();
  }
  function updateKPI(js){
    const {member_count, online_count, channels_total, threads_total} = js;
    KV.online = online_count; KV.members = member_count; KV.channels = channels_total; KV.threads = threads_total;
    $("#kpi-online").textContent = online_count;
    $("#kpi-members").textContent = member_count;
    $("#kpi-online-big").textContent = online_count;
    $("#kpi-members-big").textContent = member_count;
    $("#kpi-channels").textContent = channels_total;
    $("#kpi-threads").textContent = threads_total;
    sp[0].data.push(online_count); sp[1].data.push(member_count); sp[2].data.push(channels_total); sp[3].data.push(threads_total);
    sp.forEach(s=>{ s.data = s.data.slice(-50); drawSpark(s.el, s.data); });
  }
  async function fetchOnce(){
    try{
      const a = await fetch('/api/discord/stats'); const js = await a.json();
      updateKPI(js);
      const b = await fetch('/api/metrics'); const m = await b.json();
      serversTbody.innerHTML = (m.servers||[]).map(s=>`<tr><td>${s.name}</td><td>${s.status}</td><td>${s.ping_ms}ms</td></tr>`).join('');
      $("#apiPing").textContent = (m.servers && m.servers[1]) ? (m.servers[1].ping_ms+'ms') : '--';
    }catch(e){}
  }
  fetchOnce();
  // SSE
  try{
    const ev = new EventSource('/api/discord/stream');
    ev.onmessage = (e)=>{ try{ updateKPI(JSON.parse(e.data)); }catch(_){} };
  }catch(_){}
  // dummy recent chart
  const rc = $("#recentChart").getContext('2d');
  function drawRecent(){ const w=rc.canvas.width=rc.canvas.clientWidth, h=rc.canvas.height=rc.canvas.clientHeight;
    rc.clearRect(0,0,w,h); rc.fillStyle='#15305f'; for(let i=0;i<12;i++){ const v=(Math.sin(Date.now()/900+i)+1)/2; const bar=h*(0.2+0.7*v);
      rc.fillRect(i*(w/12)+8, h-bar, (w/12)-16, bar); } }
  setInterval(drawRecent, 900);
  // Changes demo rows (can be wired to your audit source)
  function pushChange(n, by){ const tr=document.createElement('tr'); tr.innerHTML=`<td>${n}</td><td>${by||'system'}</td><td>${new Date().toLocaleDateString()}</td>`; changesTbody.prepend(tr); while(changesTbody.children.length>6) changesTbody.removeChild(changesTbody.lastChild); }
  pushChange(1,'boot'); setInterval(()=>pushChange(Math.floor(Math.random()*99),'auto'), 8000);
  // quick upload preview
  const up=$("#quickUpload"); if(up){ up.addEventListener('change', async ()=>{ const f=up.files[0]; if(!f) return; const fd=new FormData(); fd.append('file',f); const r=await fetch('/api/upload/background',{method:'POST',body:fd}); const js=await r.json(); const h=document.getElementById('uploadHint'); if(js.ok){ h.textContent='Uploaded: '+js.url; } else { h.textContent='Upload gagal'; } });}
})();
