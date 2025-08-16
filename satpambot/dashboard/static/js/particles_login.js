(() => {
  const canvas = document.getElementById("particle-canvas");
  if(!canvas) return;
  const ctx = canvas.getContext("2d");
  let DPR = Math.min(window.devicePixelRatio || 1, 2);

  const P = [];
  const cfg = { count: 110, maxSpeed: 0.6, linkDist: 120, radius: 2.2 };

  function resize(){
    canvas.width  = Math.floor(canvas.clientWidth  * DPR);
    canvas.height = Math.floor(canvas.clientHeight * DPR);
  }
  addEventListener("resize", resize, { passive:true });
  resize();

  function rnd(a,b){ return a + Math.random()*(b-a); }

  function spawn(){
    P.length = 0;
    for(let i=0;i<cfg.count;i++){
      P.push({
        x: Math.random()*canvas.width,
        y: Math.random()*canvas.height,
        vx: rnd(-cfg.maxSpeed, cfg.maxSpeed),
        vy: rnd(-cfg.maxSpeed, cfg.maxSpeed)
      });
    }
  }
  spawn();

  let mouse = { x: -9999, y: -9999 };
  canvas.addEventListener("mousemove", e=>{
    const rect = canvas.getBoundingClientRect();
    mouse.x = (e.clientX - rect.left) * DPR;
    mouse.y = (e.clientY - rect.top) * DPR;
  });
  canvas.addEventListener("mouseleave", ()=>{ mouse.x = mouse.y = -9999; });

  function step(){
    ctx.clearRect(0,0,canvas.width,canvas.height);

    for(const p of P){
      p.x += p.vx; p.y += p.vy;
      if(p.x < 0 || p.x > canvas.width)  p.vx *= -1;
      if(p.y < 0 || p.y > canvas.height) p.vy *= -1;
    }

    ctx.lineWidth = 1 * DPR;
    for(let i=0;i<P.length;i++){
      for(let j=i+1;j<P.length;j++){
        const a=P[i], b=P[j];
        const dx=a.x-b.x, dy=a.y-b.y;
        const d = Math.hypot(dx,dy);
        if(d < cfg.linkDist * DPR){
          const alpha = 1 - d/(cfg.linkDist*DPR);
          ctx.strokeStyle = `rgba(173,216,255,${alpha*0.5})`;
          ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
        }
      }
    }

    for(const p of P){
      const dx = p.x - mouse.x, dy = p.y - mouse.y, d = Math.hypot(dx,dy);
      if(d < 90*DPR){
        p.vx += (dx/d) * 0.02; p.vy += (dy/d) * 0.02;
      }
      ctx.fillStyle = "rgba(200,220,255,.9)";
      ctx.beginPath(); ctx.arc(p.x,p.y, cfg.radius*DPR, 0, Math.PI*2); ctx.fill();
    }
    requestAnimationFrame(step);
  }
  step();
})();
