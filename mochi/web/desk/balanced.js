import {createCurriculumStage} from './curriculum-stage.js';
const $=q=>document.querySelector(q);
let manifest,left,right,base,attempt,episodes={},time=0,playing=true,last=performance.now(),loading=false;
async function refreshTraining(){try{const r=await fetch('api/balance-training');if(!r.ok)return;const p=await r.json();if(p.phase)$('#training-progress').textContent=`Live pipeline: ${p.phase} · ${p.optimizer_updates_completed||0} new optimizer updates. The visible recordings are engineering references.`}catch{}}
const fetchJSON=async p=>{const r=await fetch(p);if(!r.ok)throw Error('Missing recording: '+p);return r.json()};
async function load(entry){
 if(loading)return;loading=true;playing=false;
 try{
  episodes[entry.id]??=await fetchJSON('balanced-v11/'+entry.file);
  right.setEpisode(episodes[entry.id]);attempt=entry;time=0;
  $('#scrub').max=Math.max(episodes[base.id].duration,episodes[entry.id].duration);
  $('#right-title').textContent=entry.label.toUpperCase();$('#record').href='balanced-v11/'+entry.file;
  $('#scope').textContent='Same initial physical state, desk and playback speed. Controller revisions differ. Each side shows its complete recorded attempt, including a stall, timeout or failure. '+manifest.scope;
  $('#milestones').replaceChildren();
  for(const e of episodes[entry.id].events){
   if(!['arrival','recover'].includes(e.phase)&&!e.task)continue;
   const b=document.createElement('button');b.className='milestone';
   b.textContent=(e.label||e.task||e.phase)+' · '+e.t.toFixed(1)+' s';
   b.onclick=()=>{time=e.t;playing=false};$('#milestones').append(b);
  }
  playing=true;
 }finally{loading=false}
}
function readings(id,entry,episode,t,f){
 const row=episode.balance_measurements.findLast(r=>r.t<=t)||episode.balance_measurements[0];
 const ended=t>=episode.duration;
 $(id+'-state').textContent=ended?(entry.failure|| (entry.full_sequence_success?'Complete':'Recording ended')):(f?.task||f?.phase||'walk');
 $(id+'-metrics').textContent=row?`Roll ${(row.roll_rad*180/Math.PI).toFixed(1)}° · L ${(row.loads_n.left).toFixed(2)} N / R ${(row.loads_n.right).toFixed(2)} N · ${Math.min(t,episode.duration).toFixed(1)} s`:'No measurement';
}
function tick(now){
 const dt=Math.min(.07,(now-last)/1000);last=now;
 if(attempt&&!loading){
  const end=+$('#scrub').max;if(playing)time=Math.min(end,time+dt*+$('#speed').value);
  const a=episodes[base.id],b=episodes[attempt.id];
  readings('#left',base,a,time,left.frame(Math.min(time,a.duration)));
  readings('#right',attempt,b,time,right.frame(Math.min(time,b.duration)));
  $('#time').textContent=time.toFixed(1)+' / '+end.toFixed(1)+' s';$('#scrub').value=time;
 }
 requestAnimationFrame(tick);
}
async function init(){
 manifest=await fetchJSON('balanced-v11/manifest.json');
 left=createCurriculumStage($('#left'),{scene:manifest.scene,fullBody:true});right=createCurriculumStage($('#right'),{scene:manifest.scene,fullBody:true});
 await Promise.all([left.ready,right.ready]);base=manifest.attempts[0];episodes[base.id]=await fetchJSON('balanced-v11/'+base.file);left.setEpisode(episodes[base.id]);
 for(const e of manifest.attempts.slice(1)){const option=document.createElement('option');option.value=e.id;option.textContent=e.label;$('#candidate').append(option)}
 $('#candidate').onchange=event=>load(manifest.attempts.find(e=>e.id===event.target.value));$('#candidate').value=manifest.default_attempt;
 for(const [id,stage] of [['left',left],['right',right]]){$('#'+id+'-follow').onclick=()=>stage.view(false);$('#'+id+'-wide').onclick=()=>stage.view(true)}
 $('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'Ⅱ':'▶'};$('#restart').onclick=()=>{time=0;playing=true};$('#scrub').oninput=e=>{time=+e.target.value;playing=false};
 await load(manifest.attempts.find(e=>e.id===manifest.default_attempt));requestAnimationFrame(tick);refreshTraining();setInterval(refreshTraining,15000);
}
init().catch(e=>{$('#scope').textContent=e.message;console.error(e)});
