(function(){
  const fmt = (n)=> typeof n==="number" ? n.toLocaleString("id-ID") : n;
  function apply(data){
    for(const k in data){
      const el = document.querySelector('[data-k="'+k+'"]');
      if(el) el.textContent = fmt(data[k]);
    }
    const ts = (new Date()).toLocaleTimeString("id-ID");
    var lu = document.getElementById("lastUpdated"); if(lu) lu.textContent = ts;
  }
  async function poll(){
    try{
      const r = await fetch("/api/live/stats", {cache:"no-store"});
      if(r.ok){ apply(await r.json()); }
    }catch(e){}
  }
  window.addEventListener("DOMContentLoaded", function(){
    poll(); setInterval(poll, 5000);
  });
})();
