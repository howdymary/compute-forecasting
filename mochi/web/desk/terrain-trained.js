import {createCurriculumStage} from './curriculum-stage.js';
const $=q=>document.querySelector(q),folder='terrain-training/';
let manifest,stages,scenario,version,episodes,playing=true,time=0,last=performance.now(),loading=false,requestId=0;
const cache=new Map();
function setPlayback(value){playing=value;$('#play').textContent=value?'Ⅱ':'▶'}
function outcomeLabel(value){return ({invalid_fixture_contact:'Stopped: unintended contact',inference_token_limit:'Stopped: inference limit'})[value]||String(value).replaceAll('_',' ')}
async function json(path){const r=await fetch(path);if(!r.ok)throw Error('Missing completed recording');return r.json()}
async function episode(file){if(!cache.has(file))cache.set(file,(async()=>{const r=await fetch(folder+file);if(!r.ok)throw Error('Missing measured trajectory');const bytes=new Uint8Array(await r.arrayBuffer());return bytes[0]===31&&bytes[1]===139?new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json():JSON.parse(new TextDecoder().decode(bytes))})());return cache.get(file)}
async function load(){
 const id=++requestId,wanted=scenario.versions[+$('#checkpoint').value],selectedScenario=scenario;loading=true;setPlayback(false);
 try{
  const loaded=await Promise.all([episode(selectedScenario.parent_file),episode(wanted.file)]);if(id!==requestId)return;
  version=wanted;episodes=loaded;
  episodes.forEach((e,i)=>stages[i].setEpisode(e));time=0;$('#scrub').max=Math.max(...episodes.map(e=>e.duration));
  const before=manifest.recordings[scenario.parent_file],after=manifest.recordings[version.file];
  $('#left-id').textContent=before.checkpoint_id.slice(0,12);$('#right-id').textContent=after.checkpoint_id.slice(0,12);
  $('#right-title').textContent=`${version.update} NEW OPTIMIZER UPDATE${version.update===1?'':'S'}`;
  $('#checkpoint-label').textContent=`Update ${version.update} · ${after.cumulative_updates} cumulative`;
  $('#scope').textContent=(scenario.partition==='held_out'?'Final unseen scenario. Intermediate checkpoints were not selected using these results. ':'Development scenario used for checkpoint selection. ')+manifest.display_note;
  setPlayback(true);
  for(const key of cache.keys()){if(cache.size<=4)break;if(key!==scenario.parent_file&&key!==version.file)cache.delete(key)}
 }finally{if(id===requestId)loading=false}
}
async function selectScenario(id){
 scenario=manifest.scenarios.find(s=>s.id===id);$('#checkpoint').max=scenario.versions.length-1;$('#checkpoint').disabled=scenario.versions.length===1;
 const selected=scenario.versions.findIndex(v=>v.update===manifest.selected_update);$('#checkpoint').value=selected<0?0:selected;await load();
}
function tick(now){
 const dt=Math.min(.07,(now-last)/1000);last=now;
 if(episodes&&!loading){
  if(playing){time=Math.min(+$('#scrub').max,time+dt*+$('#speed').value);if(time>=+$('#scrub').max)setPlayback(false)}
  for(let i=0;i<2;i++){
   const e=episodes[i],f=stages[i].frame(Math.min(time,e.duration)),m=e.balance_measurements.findLast(x=>x.t<=time)||e.balance_measurements[0];
   const meta=manifest.recordings[i?version.file:scenario.parent_file];
   const phase=time>=e.duration?(meta.complete?'All tasks verified':outcomeLabel(meta.failure||'Incomplete')):(f?.task||f?.phase||'walking');
   $('#'+(i?'right':'left')+'-metrics').textContent=`${phase} · roll ${(m.roll_rad*180/Math.PI).toFixed(1)}° · ${Math.min(time,e.duration).toFixed(1)} s`;
  }
  $('#time').textContent=time.toFixed(1)+' / '+(+$('#scrub').max).toFixed(1)+' s';$('#scrub').value=time;
 }
 requestAnimationFrame(tick);
}
async function init(){
 manifest=await json(folder+'manifest.json');stages=[createCurriculumStage($('#left'),{scene:manifest.scene,fullBody:true}),createCurriculumStage($('#right'),{scene:manifest.scene,fullBody:true})];await Promise.all(stages.map(s=>s.ready));
 for(const s of manifest.scenarios){const option=document.createElement('option');option.value=s.id;option.textContent=s.label;$('#scenario').append(option)}
 $('#scenario').onchange=e=>selectScenario(e.target.value);$('#checkpoint').oninput=()=>load();
 const query=new URLSearchParams(globalThis.location?.search||'');
 const initialScenario=manifest.scenarios.some(s=>s.id===query.get('scenario'))?query.get('scenario'):manifest.default_scenario;
 $('#scenario').value=initialScenario;
 $('#campaign-summary').textContent=manifest.selection_finalized?`${manifest.optimizer_updates_completed} new optimizer updates. Selected update: ${manifest.selected_update}. The same model selects walking settings, contact profiles and arm recovery.`:`DEVELOPMENT PREVIEW · ${manifest.optimizer_updates_completed} optimizer updates completed. Showing update ${manifest.selected_update}; checkpoint selection and final testing are pending.`;
 for(const c of manifest.checkpoints){const p=document.createElement('p');p.textContent=`Update ${c.update}: ${c.development.complete_successes}/${c.development.n} complete · ${c.development.smooth_complete_successes}/${c.development.n} within smoothness limits`;$('#checkpoint-table').append(p)}
 if(!manifest.held_out){const p=document.createElement('p');p.textContent='Final testing is pending. The recordings and counts above are development results.';$('#test-table').append(p)}
 else for(const name of ['parent','selected','fixed']){const s=manifest.held_out[name],p=document.createElement('p');p.textContent=`${name}: ${s.complete_successes}/${s.n} complete · ${s.smooth_complete_successes}/${s.n} within smoothness limits`;$('#test-table').append(p)}
 for(const [id,stage]of [['left',stages[0]],['right',stages[1]]]){$('#'+id+'-follow').onclick=()=>stage.view(false);$('#'+id+'-wide').onclick=()=>stage.view(true);$('#'+id+'-feet').onclick=()=>stage.inspect('feet')}
 $('#play').onclick=()=>{if(!playing&&time>=+$('#scrub').max)time=0;setPlayback(!playing)};$('#restart').onclick=()=>{time=0;setPlayback(true)};$('#scrub').oninput=e=>{time=+e.target.value;setPlayback(false)};
 await selectScenario(initialScenario);const requestedTime=Number(query.get('t'));if(Number.isFinite(requestedTime)&&requestedTime>0){time=Math.min(requestedTime,+$('#scrub').max);setPlayback(false)}requestAnimationFrame(tick);
}
init().catch(e=>{$('#scope').textContent=e.message;console.error(e)});
