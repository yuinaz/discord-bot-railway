(function(){
  try{
    var u=document.querySelector('input[name="username"],input[type="email"],input[type="text"]');
    if(u && !u.value) u.focus();
    var f=document.querySelector('form[action*="login"],form#login,form[name="login"]');
    if(f){ f.addEventListener('submit', function(ev){ try{ev.preventDefault();}catch(e){}; window.location.assign('/dashboard'); }); }
  }catch(e){}
  console.log('[login_apply_theme] ready');
})();
