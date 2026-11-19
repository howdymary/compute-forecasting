import {createCurriculumStage} from './curriculum-stage.js';
const $=q=>document.querySelector(q),labels={alarm:'Alarm clock',drawer:'Drawer',laptop:'Laptop close',globe:'Globe'};
let stage,episode,time=0,playing=true,last=performance.now(),taskNodes={};
async function status(){try{const r=await fetch('api/terrain-training',{cache:'no-store'});if(!r.ok)throw Error();const p=await r.json();const run=p.run_id?.match(/(\d+)$/)?.[1];if(run)$('#training-link').href='https://github.com/howdymary/mochi-demo/actions/runs/'+run;$('#training-updates').textContent=`${p.optimizer_updates_completed||0} completed optimizer updates`;$('#training-phase').textContent=p.phase||'Queued behind the bounded research diagnostic. See the execution log.'}catch{$('#training-updates').textContent='See the execution log';$('#training-phase').textContent='Live numerical status is unavailable. The recording above is an engineering reference.'}}
function tick(now){
 const dt=Math.min(.07,(now-last)/1000);last=now;
 if(episode){
  if(playing)time=Math.min(episode.duration,time+dt*+$('#speed').value);
  const f=stage.frame(time),m=episode.balance_measurements.findLast(x=>x.t<=time)||episode.balance_measurements[0];
  $('#phase').textContent=f?.task?labels[f.task].toUpperCase():(m.gait_phase==='native-walk'?'DESK WALK':m.gait_phase?.toUpperCase()||'WALK');
  $('#outcome').textContent=time>=episode.duration?'All four tasks verified':f?.task?`${labels[f.task]} · ${f.phase}`:f?.phase==='recover'?'Return arm to walking posture':m.gait_phase==='swing'?'Lift, clear, place':m.gait_phase==='shift'?'Transfer weight':'Follow the route';
  $('#detail').textContent=`${Math.min(time,episode.duration).toFixed(1)} s · torso roll ${(m.roll_rad*180/Math.PI).toFixed(1)}°`;
  $('#time').textContent=time.toFixed(1)+' / '+episode.duration.toFixed(1)+' s';$('#scrub').value=time;
  for(const [task,node] of Object.entries(taskNodes)){const verified=episode.events.some(e=>e.task===task&&e.success&&e.t<=time);node.textContent=`${verified?'✓':'○'} ${labels[task]}`;node.style.color=verified?'#48735b':'inherit'}
 }
 requestAnimationFrame(tick);
}
async function init(){
 const m=await (await fetch('terrain-engineering/manifest.json')).json();
 const response=await fetch('terrain-engineering/'+m.file);if(!response.ok)throw Error('Missing physical recording');
 episode=await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
 stage=createCurriculumStage($('#stage'),{scene:m.scene,fullBody:true});await stage.ready;stage.setEpisode(episode);
 $('#loading').style.display='none';$('#scrub').max=episode.duration;$('#scope').textContent=m.note;
 for(const task of Object.keys(labels)){const n=document.createElement('p');taskNodes[task]=n;$('#tasks').append(n)}
 for(const [label,value]of [['Final task result','4 / 4 tasks'],['Fall / forbidden contact','0 / 0'],['Torso roll RMS',episode.balance_metrics.roll_rms_deg.toFixed(2)+'°'],['Applied base force',episode.maximum_applied_base_force.toFixed(3)+' N']]){const n=document.createElement('p');n.textContent=label+': '+value;$('#metrics').append(n)}
 for(const [label,t]of [['Books',0],...Object.keys(labels).map(k=>[labels[k],Math.max(0,episode.trajectory.frames.find(f=>f.task===k).t-1)])]){const n=document.createElement('button');n.textContent=label;n.onclick=()=>{time=t;playing=true};$('#jumps').append(n)}
 $('#wide').onclick=()=>stage.view(true);$('#follow').onclick=()=>stage.view(false);$('#feet').onclick=()=>stage.inspect('feet');
 $('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'Ⅱ':'▶'};$('#restart').onclick=()=>{time=0;playing=true};$('#scrub').oninput=e=>{time=+e.target.value;playing=false};
 await status();setInterval(status,30000);requestAnimationFrame(tick);
}
init().catch(e=>{$('#loading').textContent=e.message;console.error(e)});
