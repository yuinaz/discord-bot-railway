
import { bindCounter, setCounter } from './anim_counters.js';
import { SparklineCanvas } from './sparkline_60fps.js';
import { BarsCanvas } from './bars_60fps.js';

// Bind counters to stat cards
['stat-guilds','stat-members','stat-online','stat-channels','stat-threads'].forEach(id=>bindCounter(id, 0));

// Sparklines
const spCPU = SparklineCanvas(document.getElementById('spark-cpu'));
const spRAM = SparklineCanvas(document.getElementById('spark-ram'));
const spPing = SparklineCanvas(document.getElementById('spark-ping'));

// Activity bars
const bars = BarsCanvas(document.getElementById('recent-activity'), 16);

function applyStats(d){
  if(!d) return;
  if(d.guilds!=null) setCounter('stat-guilds', d.guilds);
  if(d.members!=null) setCounter('stat-members', d.members);
  if(d.online!=null) setCounter('stat-online', d.online);
  if(d.channels!=null) setCounter('stat-channels', d.channels);
  if(d.threads!=null) setCounter('stat-threads', d.threads);
  if(Array.isArray(d.activity)) bars.set(d.activity);
  if(d.latency_ms!=null) spPing.push(Math.max(0, d.latency_ms));
}

async function pollLoop(){
  try{
    // metrics has CPU/RAM and nested discord summary
    const m = await fetch('/api/metrics').then(r=>r.json());
    if(m && m.process){
      spCPU.push((m.process.cpu_percent||0));
      spRAM.push((m.process.mem_rss||0)/1048576); // MB
    }
    if(m && m.discord) applyStats(m.discord);
  }catch(e){}
  try{
    const s = await fetch('/api/discord/stats').then(r=>r.json());
    if(s) applyStats(s);
  }catch(e){}
}

function start(){
  // SSE live stream if available
  let es;
  try{
    es = new EventSource('/api/discord/stream');
    es.onmessage = (ev)=>{
      try{ applyStats(JSON.parse(ev.data||'{}')); }catch(e){}
    };
    es.onerror = ()=>{ es.close(); setInterval(pollLoop, 2000); };
  }catch(e){
    setInterval(pollLoop, 2000);
  }
  pollLoop();
}

start();
