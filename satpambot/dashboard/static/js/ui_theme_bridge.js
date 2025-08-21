(function(){
  try{
    var l=document.createElement('link'); l.rel='stylesheet';
    l.href='/dashboard-static/themes/gtake/theme.css';
    document.head.appendChild(l);
  }catch(e){}
  console.log('[ui_theme_bridge] ready');
})();
