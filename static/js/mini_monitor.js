
(function(){
  async function tick(){
    try{
      const res = await fetch('/api/live_stats', {cache:'no-store'});
      if(!res.ok){ return; }
      const j = await res.json();
      if(j && j.uptime){
        document.getElementById('mm-uptime').textContent = 'Uptime: ' + j.uptime;
        document.getElementById('mm-cpu').textContent = 'CPU: ' + j.cpu + '%';
        document.getElementById('mm-ram').textContent = 'RAM: ' + j.ram + ' MB';
      }
    }catch(e){ /* silent */ }
  }
  tick();
  setInterval(tick, 3000);
})();
