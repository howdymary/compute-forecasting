import {createCurriculumStage} from './curriculum-stage.js';
const $=q=>document.querySelector(q);
let manifest,stage,episode,time=0,playing=true,last=performance.now(),active=null,loading=false;
const frames=new Map();
async function load(attempt){
 if(loading)return;loading=true;playing=false;
 try{
  if(!frames.has(attempt.file))frames.set(attempt.file,fetch('richdesk/'+attempt.file).then(r=>{if(!r.ok)throw Error('Missing recorded attempt');return r.json()}));
  episode=await frames.get(attempt.file);await stage.ready;stage.setEpisode(episode);stage.view(true);active=attempt;time=0;playing=true;$('#scrub').max=episode.duration;
  $('#record').href='richdesk/'+attempt.file;$('#scope').textContent=attempt.scope||manifest.scope;
  document.querySelectorAll('[data-attempt]').forEach(b=>b.classList.toggle('active',b.dataset.attempt===attempt.id));
  const m=episode.locomotion_metrics||{};$('#metrics').replaceChildren();
  for(const [label,value]of [['Book-top support',attempt.verified?'Passed':attempt.status||'Not established'],['Torso sway RMS',m.torso_tilt_rms_deg?.toFixed(2)+'°'],['Contact-travel estimate',(m.slip_m*100).toFixed(1)+' cm'],['Non-foot terrain contacts',m.nonfoot_terrain_contacts??'—'],['Applied base force',episode.maximum_applied_base_force?.toFixed(5)+' N']]){let r=document.createElement('div');r.className='metric';const s=document.createElement('span'),v=document.createElement('b');s.textContent=label;v.textContent=value;r.append(s,v);$('#metrics').append(r)}
  $('#loading').style.display='none';$('#play').textContent='Ⅱ';
 }catch(e){$('#loading').textContent=e.message;console.error(e)}finally{loading=false}
}
function tick(now){
 const dt=Math.min((now-last)/1000,.07);last=now;
 if(episode&&!loading){
  if(playing)time=Math.min(episode.duration,time+dt*+$('#speed').value);
  const f=stage.frame(time);$('#time').textContent=time.toFixed(1)+' / '+episode.duration.toFixed(1)+' s';$('#scrub').value=time;
  $('#phase').textContent=f?.task?f.task.toUpperCase():f?.support_phase?.toUpperCase()||'DESK WALK';
  $('#outcome').textContent=time>=episode.duration-.03?(episode.fall?'Stopped at validity limit':active.verified?'Book-top support verified':active.status||'Recorded attempt ended'):(f?.support_phase==='swing'?'Lift, clear, place':f?.support_phase==='shift'?'Transfer weight':f?.support_phase==='land'?'Confirm foot contact':'Move across the desk');
  $('#detail').textContent=f?'Body tilt '+f.base_tilt_degrees.toFixed(1)+'° · physical time':'Recorded simulation';
 }
 requestAnimationFrame(tick);
}
async function init(){
 const r=await fetch('richdesk/manifest.json',{cache:'no-store'});if(!r.ok)throw Error('Scene recordings are not published yet');manifest=await r.json();stage=createCurriculumStage($('#stage'),{scene:manifest.scene});stage.setTerrainReference(manifest.route);
 const chosen=manifest.route.candidates.find(c=>c.id===manifest.route.selected_candidate);$('#route-summary').textContent=chosen?`${chosen.distance_m.toFixed(2)} m, ${(chosen.turning_rad*180/Math.PI).toFixed(0)}° of planned turning. Zero flagged rest-pose collision samples. Footstep execution and balance still require physical validation.`:'No geometrically valid candidate selected.';
 for(const a of manifest.attempts){let b=document.createElement('button');b.dataset.attempt=a.id;b.textContent=a.label;b.onclick=()=>load(a);$('#attempts').append(b)}
 $('#wide').onclick=()=>stage.view(true);$('#follow').onclick=()=>stage.view(false);$('#feet').onclick=()=>stage.inspect('feet');
 let routeVisible=true;$('#route').onclick=()=>{routeVisible=!routeVisible;stage.showTerrainReference(routeVisible);$('#route').textContent=routeVisible?'Hide plan':'Show plan'};
 $('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'Ⅱ':'▶'};$('#restart').onclick=()=>{time=0;playing=true};$('#scrub').oninput=e=>{time=+e.target.value;playing=false};
 await load(manifest.attempts.find(x=>x.id===manifest.default_attempt)||manifest.attempts[0]);requestAnimationFrame(tick);
}
init().catch(e=>{$('#loading').textContent=e.message;console.error(e)});
