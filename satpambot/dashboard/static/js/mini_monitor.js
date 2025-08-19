(function(){
function spark(canvas,arr){const ctx=canvas.getContext('2d');const w=canvas.width=canvas.offsetWidth;const h=canvas.height=40;ctx.clearRect(0,0,w,h);if(!arr.length)return;const max=Math.max(...arr),min=Math.min(...arr);ctx.beginPath();arr.forEach((v,i)=>{const x=i/(arr.length-1)*w;const y=h-((v-min)/(max-min||1))*h; i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.lineWidth=2;ctx.stroke();}
const s=[[],[],[],[]];
async function pull(){
  try{
    const r=await fetch('/api/metrics'); const m=await r.json();
    const d=await fetch('/api/discord/stats'); const x=await d.json();
    document.getElementById('onlineCount').textContent=x.online_count??'--';
    document.getElementById('memberCount').textContent=x.member_count??'--';
    document.getElementById('channelCount').textContent=x.channels_total??'--';
    document.getElementById('threadCount').textContent=x.threads_total??'--';
    s[0].push(x.online_count||0); s[1].push(x.member_count||0); s[2].push(x.channels_total||0); s[3].push(x.threads_total||0);
    s.forEach(a=>{if(a.length>30)a.shift();});
    ['sp1','sp2','sp3','sp4'].forEach((id,i)=>spark(document.getElementById(id), s[i]));
    const tbody=document.querySelector('#srvTable tbody'); tbody.innerHTML='';
    (m.servers||[]).forEach(row=>{const tr=document.createElement('tr'); tr.innerHTML=`<td>${row.name}</td><td>${row.status}</td><td>${row.ping_ms}ms</td>`; tbody.appendChild(tr); });
  }catch(e){}
}
setInterval(pull,5000); pull();
})();