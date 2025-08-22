
(function(){
  const sel = (q)=>document.querySelector(q);
  const m = (k)=>sel('#m_'+k);
  const canvas = document.getElementById('activityChart');
  const ctx = canvas ? canvas.getContext('2d') : null;

  async function pull(){
    try{
      const r = await fetch('/api/live/stats',{cache:'no-store'});
      if(!r.ok) throw new Error('http '+r.status);
      const j = await r.json();
      const map = {
        guilds: 'guilds', members:'members', online:'online',
        channels:'channels', threads:'threads', latency_ms:'latency'
      };
      for(const [src, id] of Object.entries(map)){
        const el = m(id); if(el) el.textContent = j[src] ?? 0;
      }
      const lu = document.getElementById('last_update');
      if(lu) lu.textContent = new Date().toLocaleTimeString();
    }catch(e){ /* ignore */ }
  }
  setInterval(pull, 1000); pull();

  if(ctx){
    let t=0;
    function draw(){
      const w=canvas.width, h=canvas.height;
      ctx.clearRect(0,0,w,h);
      // smooth neon line
      ctx.strokeStyle = '#7aa2ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for(let x=0; x<w; x+=4){
        const y = h*0.6 + Math.sin((x+t)/40)*20 + Math.cos((x+t)/23)*10;
        x===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      }
      ctx.stroke();
      t+=2;
      requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
  }

  // Dropzone
  const dz = sel('#dropzone');
  if(dz){
    dz.addEventListener('click', ()=>{
      const i = document.createElement('input');
      i.type='file'; i.accept='image/*';
      i.onchange=()=>{ if(i.files && i.files[0]) upload(i.files[0]); };
      i.click();
    });
    dz.addEventListener('dragover', ev=>{ ev.preventDefault(); dz.classList.add('hover') });
    dz.addEventListener('dragleave', ()=>dz.classList.remove('hover'));
    dz.addEventListener('drop', ev=>{
      ev.preventDefault(); dz.classList.remove('hover');
      const f = ev.dataTransfer.files[0];
      if(f) upload(f);
    });
  }
  async function upload(file){
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/dashboard/security/upload',{method:'POST',body:fd});
    if(r.ok){ dz.textContent='Uploaded: '+file.name; } else { dz.textContent='Upload failed'; }
  }
})();
