(function(){
  try{
    // mark page as login for CSS hooks
    document.body.classList.add('login-page');

    // wrap content to a centered shell & card if not present
    var root = document.querySelector('.login-center') || document.querySelector('.login-shell');
    if(!root){
      root = document.createElement('div');
      root.className = 'login-center';
      // move existing form into card
      var form = document.querySelector('form') || document.querySelector('form#login') || document.querySelector('form[name="login"]');
      if(form){
        var card = document.createElement('div'); card.className = 'card login-card';
        var title = document.createElement('div'); title.className = 'login-title'; title.textContent = 'Masuk';
        var sub = document.createElement('div'); sub.className = 'login-sub'; sub.textContent = 'Gunakan kredensial admin yang valid.';
        card.appendChild(title); card.appendChild(sub); form.classList.add('login-form'); card.appendChild(form);
        root.appendChild(card);
        document.body.innerHTML = ""; document.body.appendChild(root);
      }
    }

    // autofocus
    var u=document.querySelector('input[name="username"],input[type="email"],input[type="text"]');
    if(u && !u.value) u.focus();
  }catch(e){}
  console.log('[login_apply_theme] layout centered');
})();
