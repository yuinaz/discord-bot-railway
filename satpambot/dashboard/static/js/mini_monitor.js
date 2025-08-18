async function refreshMM(){
  try {
    const [m, u] = await Promise.all([
      fetch('/metrics').then(r=>r.json()),
      fetch('/uptime').then(r=>r.json())
    ]);
    if(m && typeof m.cpu !== 'undefined'){
      document.getElementById('mm-cpu').textContent = `CPU: ${m.cpu}%`;
      document.getElementById('mm-ram').textContent = `RAM: ${m.ram_mb} / ${m.ram_total_mb} MB`;
    }
    if(u && typeof u.uptime_seconds !== 'undefined'){
      const sec = u.uptime_seconds;
      const h = Math.floor(sec/3600);
      const m2 = Math.floor((sec%3600)/60);
      const s = sec%60;
      document.getElementById('mm-uptime').textContent = `Uptime: ${h}h ${m2}m ${s}s`;
    }
  } catch(e){
  }
}
setInterval(refreshMM, 3000);
refreshMM();
