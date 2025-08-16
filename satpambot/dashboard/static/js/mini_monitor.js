async function refreshMini(){
  try{
    const d = await (await fetch("/api/mini-monitor",{cache:"no-store"})).json(); // { uptime, cpu, ram }
    const u = document.getElementById("mm-uptime");
    const c = document.getElementById("mm-cpu");
    const r = document.getElementById("mm-ram");
    if(u) u.textContent = "Uptime: " + (d.uptime || "--");
    if(c) c.textContent = "CPU: " + (d.cpu ?? "--") + "%";
    if(r) r.textContent = "RAM: " + (d.ram ?? "--") + " MB";
  }catch(e){}
}
refreshMini(); setInterval(refreshMini, 4000);
