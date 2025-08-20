
// Persisted sidebar collapse
(function(){
  const key = "neo.sidebar.collapsed";
  const root = document.documentElement;
  function apply(){
    const collapsed = localStorage.getItem(key)==="1";
    document.querySelector('.sidebar')?.classList.toggle('collapsed', collapsed);
  }
  window.addEventListener('DOMContentLoaded', ()=>{
    apply();
    const t = document.getElementById('sidebar-toggle');
    if(t){ t.addEventListener('click', ()=>{
      const cur = localStorage.getItem(key)==="1";
      localStorage.setItem(key, cur ? "0":"1");
      apply();
    });}
  });
})();
