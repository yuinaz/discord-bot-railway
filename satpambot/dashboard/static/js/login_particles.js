(function(){
  if(!window.ENABLE_PARTICLES) return;
  const c = document.getElementById('particles');
  if(!c) return;
  const ctx = c.getContext('2d');
  let w,h, dots=[];
  function rnd(a,b){ return Math.random()*(b-a)+a; }
  function reset(){
    w = c.width = window.innerWidth;
    h = c.height = window.innerHeight;
    const count = Math.min(120, Math.floor(w*h/12000));
    dots = [];
    for(let i=0;i<count;i++){
      dots.push({x:rnd(0,w), y:rnd(0,h), vx:rnd(-.4,.4), vy:rnd(-.4,.4), r:rnd(1,2.2), o:rnd(.2,.8)});
    }
  }
  function step(){
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle = '#fff';
    for(const d of dots){
      d.x+=d.vx; d.y+=d.vy;
      if(d.x<0||d.x>w) d.vx*=-1;
      if(d.y<0||d.y>h) d.vy*=-1;
      ctx.globalAlpha = d.o;
      ctx.beginPath(); ctx.arc(d.x,d.y,d.r,0,Math.PI*2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(step);
  }
  window.addEventListener('resize', reset);
  reset(); step();
})();