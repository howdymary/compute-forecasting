import {createCurriculumStage} from './smooth-stage.js';
import {stepCountAt,taskStatesAt,comparisonEvidence,taskNames,activityAt} from './efficient-evidence.mjs';
const $=q=>document.querySelector(q),folder='contact-v18/';
let manifest,stages,scenario,version,episodes,playing=true,time=0,last=performance.now(),loading=false,requestId=0;
const cache=new Map();
function setPlayback(value){playing=value;last=performance.now();$('#play').textContent=value?'Ⅱ':'▶'}
function outcomeLabel(value){return ({fall:'Stopped: fall',invalid_fixture_contact:'Stopped: unintended contact',inference_token_limit:'Stopped: inference limit'})[value]||String(value).replaceAll('_',' ')}
async function json(path){const r=await fetch(path);if(!r.ok)throw Error('Missing completed recording');return r.json()}
async function episode(file){if(!cache.has(file))cache.set(file,(async()=>{const r=await fetch(folder+file);if(!r.ok)throw Error('Missing measured trajectory');const bytes=new Uint8Array(await r.arrayBuffer());return bytes[0]===31&&bytes[1]===139?new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json():JSON.parse(new TextDecoder().decode(bytes))})());return cache.get(file)}
async function load(){
 const id=++requestId,wanted=scenario.versions[+$('#checkpoint').value],selectedScenario=scenario;loading=true;setPlayback(false);
 $('#scope').textContent=`Loading ${selectedScenario.label}, update ${wanted.update}…`;
 try{
  const loaded=await Promise.all([episode(selectedScenario.parent_file),episode(wanted.file)]);if(id!==requestId)return;
  version=wanted;episodes=loaded;
  episodes.forEach((e,i)=>stages[i].setEpisode(e));time=0;$('#scrub').max=Math.max(...episodes.map(e=>e.duration));
  const before=manifest.recordings[scenario.parent_file],after=manifest.recordings[version.file];
  $('#left-id').textContent=before.checkpoint_id.slice(0,12);$('#right-id').textContent=after.checkpoint_id.slice(0,12);
  $('#right-title').textContent=`${version.update} NEW OPTIMIZER UPDATE${version.update===1?'':'S'}`;
  $('#checkpoint-label').textContent=`Update ${version.update} · ${after.cumulative_updates} cumulative`;
  const a=before.after_descent_clearance,b=after.after_descent_clearance;$('#after-descent').disabled=!(a?.completed_leg&&b?.completed_leg&&Math.min(a.end_t,b.end_t)>Math.max(a.start_t,b.start_t));
  episodes.forEach((e,i)=>{const c=e.flat_foot_clearance,d=[before,after][i].after_descent_clearance;const first=d?.median_peak_m==null?'Post-descent desk leg: no measured completed swings.':`Post-descent desk leg: ${(d.median_peak_m*1000).toFixed(1)} mm median sole clearance${d.completed_leg?'':' (leg incomplete)'}. `;$('#'+(i?'right':'left')+'-clearance').textContent=first+(c?.moving_median_peak_m==null?'No completed moving swings in this recording.':`Full-attempt moving-swing median: ${(c.moving_median_peak_m*1000).toFixed(1)} mm · ${c.moving_swings_measured} measured swings. Station alignment is reported separately.`)});
  $('#scope').textContent=scenario.label+'. '+(scenario.partition.startsWith('held_out')?'Final test scenario. The checkpoint was frozen before this test. '+(scenario.partition==='held_out_pending'?'The full cohort is still in progress. ':''):'Development scenario used for checkpoint selection. ')+manifest.display_note;
  const comparison=before.checkpoint_id===after.checkpoint_id?{status:'mixed',headline:scenario.parent_file===version.file?'Same checkpoint and recording':'Same checkpoint, repeated physical attempts',detail:scenario.parent_file===version.file?'Both panes replay the same parent recording.':'Both panes use the same saved model weights. Differences between these repetitions do not establish a training gain.'}:comparisonEvidence(before,after);$('#pair-result').className='pair-result '+comparison.status;$('#pair-headline').textContent=comparison.headline;
  const comparable=before.qualified_complete&&after.qualified_complete;
  $('#pair-detail').textContent=comparison.detail+` ${before.complete&&after.complete?'Complete-attempt':'Partial-attempt'} recovery totals: ${before.recovery_arm_joint_travel_rad.toFixed(2)} and ${after.recovery_arm_joint_travel_rad.toFixed(2)} rad.`+(comparable?'':' These totals do not establish an efficiency gain.');
  if(manifest.evaluation_status!=='completed'&&!manifest.selection_finalized)$('#campaign-summary').textContent=`DEVELOPMENT PREVIEW · ${manifest.optimizer_updates_completed} optimizer updates completed. Showing update ${version.update}; checkpoint selection is pending. Final testing is pending.`;
  setPlayback(true);
  for(const key of cache.keys()){if(cache.size<=4)break;if(key!==scenario.parent_file&&key!==version.file)cache.delete(key)}
 }finally{if(id===requestId)loading=false}
}
async function selectScenario(id,preferredUpdate){
 scenario=manifest.scenarios.find(s=>s.id===id);$('#checkpoint').max=scenario.versions.length-1;$('#checkpoint').disabled=scenario.versions.length===1;
 let selected=scenario.versions.findIndex(v=>v.update===preferredUpdate);if(selected<0)selected=scenario.versions.findIndex(v=>v.update===manifest.selected_update);$('#checkpoint').value=selected<0?0:selected;await load();
}
function tick(now){
 const dt=Math.max(0,(now-last)/1000);last=Math.max(last,now);
 if(episodes&&!loading){
  if(playing&&!document.hidden){time=Math.min(+$('#scrub').max,time+dt*+$('#speed').value);if(time>=+$('#scrub').max)setPlayback(false)}
  for(let i=0;i<2;i++){
   const e=episodes[i],f=stages[i].frame(Math.min(time,e.duration)),m=e.balance_measurements.findLast(x=>x.t<=time)||e.balance_measurements[0];
   const meta=manifest.recordings[i?version.file:scenario.parent_file];
   const stepCount=stepCountAt(e,time);
   const side=i?'right':'left';
   const recovered=e.events.filter(x=>x.phase==='recover'&&x.t<=time);
   $('#'+side+'-arms').textContent=recovered.reduce((sum,x)=>sum+(x.arm_joint_travel_rad||0),0).toFixed(2);
   const paper=e.postit_crossings.some(x=>x.physical_paper_contact&&x.load_n>=.08&&x.t<=time),turn=e.events.some(x=>x.label==='book-top-turnaround'&&x.t<=time),descent=e.events.some(x=>x.label==='book-forward-descent'&&x.t<=time);
   const turnStatus=turn?(meta.book_turnaround_verified?'verified':'unverified'):'pending',descentStatus=descent?(meta.forward_descent_verified?'verified':'unverified'):'pending';
   $('#'+side+'-route').textContent=`Book turn: ${turnStatus} · Forward descent: ${descentStatus} · Post-it: ${paper?'loaded contact':'pending'}`;$('#'+side+'-steps').textContent=String(stepCount);$('#'+side+'-elapsed').textContent=Math.min(time,e.duration).toFixed(1);
   for(const state of taskStatesAt(e,Math.min(time,e.duration))){const node=$('#'+side+'-task-'+state.task);node.className='task-state '+state.status;node.textContent=taskNames[state.task]+(state.status==='passed'?' ✓':state.status==='failed'?' ×':state.status==='active'?' …':'')}
   const motionLabel=({book_turnaround:'Supported book turnaround',book_descent:'Forward-facing book descent',postit_crossing:'Post-it crossing',turning:'Turning toward travel'})[m.step_category];
   const phase=time>=e.duration?(meta.complete?(meta.qualified_complete?'All tasks verified':'Tasks verified; quality limits exceeded'):outcomeLabel(meta.failure||'Incomplete')):motionLabel||activityAt(e,time).label;
   $('#'+(i?'right':'left')+'-metrics').textContent=`${phase} · ${stepCount} steps · roll ${(m.roll_rad*180/Math.PI).toFixed(1)}° · ${Math.min(time,e.duration).toFixed(1)} s`;
  }
  $('#time').textContent=time.toFixed(1)+' / '+(+$('#scrub').max).toFixed(1)+' s';$('#scrub').value=time;
 }
 requestAnimationFrame(tick);
}
async function init(){
 manifest=await json(folder+'manifest.json');stages=[createCurriculumStage($('#left'),{scene:manifest.scene,fullBody:true,cameraOffset:[.45,-.52,.30]}),createCurriculumStage($('#right'),{scene:manifest.scene,fullBody:true,cameraOffset:[.45,-.52,.30]})];await Promise.all(stages.map(s=>s.ready));
 for(const s of manifest.scenarios){const option=document.createElement('option');option.value=s.id;option.textContent=s.label;$('#scenario').append(option)}
 $('#scenario').onchange=e=>selectScenario(e.target.value);$('#checkpoint').oninput=()=>load();
 const query=new URLSearchParams(globalThis.location?.search||'');
 const initialScenario=manifest.scenarios.some(s=>s.id===query.get('scenario'))?query.get('scenario'):manifest.default_scenario;
 $('#scenario').value=initialScenario;
 if(manifest.evaluation_status==='completed'){
  const p=manifest.held_out.parent,s=manifest.held_out.selected;
  $('#campaign-summary').textContent=`${manifest.optimizer_updates_completed} real Tinker optimizer updates; development selected update ${manifest.selected_update}. Fresh scenarios: selected ${s.complete_successes}/${s.n} complete (${s.qualified_complete_successes}/${s.n} within all quality limits); parent ${p.complete_successes}/${p.n} complete (${p.qualified_complete_successes}/${p.n} qualified). Selected: ${s.clear_stepping_successes??0}/${s.n} qualified runs met the moving-foot-clearance target. ${manifest.improvement_goal_met?'The declared completion, clearance, step and recovery targets were met.':'The full joint improvement target was not met; the measurements below retain the tradeoffs and failures.'}`;
 }else $('#campaign-summary').textContent=`DEVELOPMENT PREVIEW · ${manifest.optimizer_updates_completed} optimizer updates completed. ${manifest.selection_finalized?'Update '+manifest.selected_update+' selected on development data':'Showing update '+manifest.selected_update+'; checkpoint selection is pending'}. Final testing is pending.`;
 if(manifest.selection_finalized&&manifest.selected_update===0)$('#campaign-summary').textContent+=' No newly trained checkpoint was promoted.';
 for(const c of manifest.checkpoints){const p=document.createElement('p'),s=c.development;p.textContent=s?`Update ${c.update}: ${s.complete_successes}/${s.n} complete · ${s.qualified_complete_successes}/${s.n} qualified · ${s.clear_stepping_successes??0}/${s.n} clear stepping · ${s.successful_mean_steps?.toFixed(0)??'unavailable'} steps · ${s.successful_mean_recovery_arm_joint_travel_rad?.toFixed(2)??'unavailable'} rad/recovery · ${s.successful_mean_seconds?.toFixed(1)??'unavailable'} s on qualified cases`:(manifest.pending_evaluation_updates?.includes(c.update)?`Update ${c.update}: checkpoint saved and probed; physical development evaluation is pending.`:`Update ${c.update}: checkpoint saved and probed; no physical development evaluation within this campaign's budget.`);$('#checkpoint-table').append(p)}
 if(!manifest.held_out){const p=document.createElement('p');p.textContent=`Final testing is pending. ${manifest.test_pairs_available||0} matched test case${manifest.test_pairs_available===1?'':'s'} available to inspect; the full cohort summary is pending.`;$('#test-table').append(p)}
 else for(const [name,s]of Object.entries(manifest.held_out)){const p=document.createElement('p');p.textContent=`${name}: ${s.complete_successes}/${s.n} complete · ${s.qualified_complete_successes}/${s.n} within all quality limits · ${s.successful_mean_steps?.toFixed(0)??'unavailable'} steps · ${s.successful_mean_recovery_arm_joint_travel_rad?.toFixed(2)??'unavailable'} rad/recovery · ${s.successful_mean_intertask_arm_joint_travel_rad?.toFixed(1)??'unavailable'} rad intertask arm travel · ${s.successful_mean_flat_sole_clearance_m==null?'unavailable':(s.successful_mean_flat_sole_clearance_m*1000).toFixed(1)+' mm'} moving sole clearance on qualified cases`;$('#test-table').append(p)}
 for(const [id,stage]of [['left',stages[0]],['right',stages[1]]]){$('#'+id+'-follow').onclick=()=>stage.view(false);$('#'+id+'-wide').onclick=()=>stage.view(true);$('#'+id+'-feet').onclick=()=>stage.inspect('feet')}
 $('#footfalls').onchange=e=>stages.forEach(s=>s.showFootfalls(e.target.checked));
 $('#play').onclick=()=>{if(!playing&&time>=+$('#scrub').max)time=0;setPlayback(!playing)};$('#restart').onclick=()=>{time=0;setPlayback(true)};$('#after-descent').onclick=()=>{const a=manifest.recordings[scenario.parent_file].after_descent_clearance,b=manifest.recordings[version.file].after_descent_clearance;if(!a?.completed_leg||!b?.completed_leg)return;const lo=Math.max(a.start_t,b.start_t),hi=Math.min(a.end_t,b.end_t);if(hi<=lo)return;time=lo+Math.min(1.25,(hi-lo)/3);$('#speed').value='0.5';stages.forEach(s=>s.inspect('feet'));setPlayback(true)};$('#scrub').oninput=e=>{const value=+e.target.value,maximum=+$('#scrub').max;time=maximum-value<=.021?maximum:value;setPlayback(false)};
 await selectScenario(initialScenario,query.has('checkpoint')?Number(query.get('checkpoint')):undefined);if(query.get('view')==='feet')stages.forEach(s=>s.inspect('feet'));if(query.get('phase')==='desk'&&!$('#after-descent').disabled)$('#after-descent').click();const requestedTime=Number(query.get('t'));if(Number.isFinite(requestedTime)&&requestedTime>0){time=Math.min(requestedTime,+$('#scrub').max);setPlayback(false)}requestAnimationFrame(tick);
}
document.addEventListener?.('visibilitychange',()=>{last=performance.now()});
init().catch(e=>{$('#scope').textContent=e.message;console.error(e)});
