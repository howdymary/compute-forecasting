import {createCurriculumStage} from './smooth-stage.js';
import {stepCountAt,taskStatesAt,activityAt} from './efficient-evidence.mjs';

const $=s=>document.querySelector(s);
let stage,episode,annotations,metadata,time=0,last=performance.now(),playing=true;
function playingState(value){playing=value;$('#play').textContent=value?'Ⅱ':'▶'}
function draw(){
 stage.frame(Math.min(time,episode.duration));
 $('#time').textContent=time.toFixed(1)+' s';$('#scrub').value=time;
 $('#steps').textContent=String(stepCountAt(episode,time));
 $('#phase').textContent=time>=episode.duration?'All four tasks verified. '+(metadata.qualified?'All quality checks passed.':'The lateral-excursion quality limit was exceeded.'):activityAt(annotations,time).label;
 for(const state of taskStatesAt(annotations,time))$('#task-'+state.task).className='task-state '+state.status;
}
function tick(now){
 const elapsed=Math.max(0,(now-last)/1000);last=now;
 if(playing&&!document.hidden)time=Math.min(episode.duration,time+elapsed*Number($('#speed').value));
 if(time>=episode.duration)playingState(false);
 draw();requestAnimationFrame(tick);
}
async function main(){
 const meta=await (await fetch('contact-v18/preflight-manifest.json')).json();metadata=meta;
 if(meta.optimizer_updates!==0||!meta.complete)throw Error('This page requires the completed fixed-controller preflight');
 const response=await fetch('contact-v18/'+meta.filename);
 episode=JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text());
 if(episode.scenario.seed!==meta.seed||episode.maximum_applied_base_force!==0)throw Error('Recording provenance mismatch');
 // Reuse the actual fixed-control log for the shared phase-display helper.
 // The archived model-call list stays empty; this is not model inference.
 annotations={...episode,model_decisions:episode.decisions};
 stage=createCurriculumStage($('#stage'),{scene:episode.scene,fullBody:true,cameraOffset:[.35,-.48,.26]});
 await stage.ready;stage.setEpisode(episode);
 $('#scrub').max=episode.duration;
 $('#quality').textContent=meta.qualified?'Full-run result: all tasks and quality checks passed.':'Full-run quality result: all tasks completed, but lateral peak-to-peak excursion was '+(meta.quality_failures.lateral_peak_to_peak_m.observed*100).toFixed(2)+' cm, above the frozen '+(meta.quality_failures.lateral_peak_to_peak_m.limit*100).toFixed(2)+' cm limit. This run is not a qualified smooth completion.';
 $('#clearance').textContent=(meta.clearance.moving_median_peak_m*1000).toFixed(1)+' mm';
 $('#play').onclick=()=>playingState(!playing);
 $('#restart').onclick=()=>{time=0;stage.view(false);playingState(true)};
 $('#scrub').oninput=e=>{time=Math.min(episode.duration,Math.max(0,Number(e.target.value)));playingState(false);draw()};
 $('#follow').onclick=()=>stage.view(false);$('#wide').onclick=()=>stage.view(true);$('#feet').onclick=()=>stage.inspect('feet');
 $('#desk-steps').onclick=()=>{
  const exit=episode.events.find(e=>e.label==='forward-descent-exit-stance'&&e.success);
  if(!exit)return;
  const forward=episode.events.find(e=>e.phase==='walk-forward'&&e.t>=exit.t);
  time=forward?.t??exit.t;stage.inspect('feet');$('#speed').value='0.5';playingState(true);draw();
 };
 const query=new URLSearchParams(location.search);
 if(query.get('view')==='feet')stage.inspect('feet');
 if(query.get('phase')==='desk')$('#desk-steps').click();
 last=performance.now();requestAnimationFrame(tick);
}
main().catch(error=>{$('#phase').textContent='Could not load the measured recording: '+error.message;console.error(error)});
