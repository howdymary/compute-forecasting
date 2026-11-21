import {createCurriculumStage as originalStage} from './smooth-stage.js';
import {createCurriculumStage as revisedStage} from './visual-v22-stage.js';
import {stepCountAt,taskStatesAt,taskNames} from './efficient-evidence.mjs';

const $=q=>document.querySelector(q),mode=new URLSearchParams(location.search).get('mode')==='motion'?'motion':'appearance';
const folder='visual-motion-v22/';let data,report,stages,selected,episodes,time=0,playing=true,loading=true,last=performance.now(),serial=0;
const cache=new Map();
async function json(url){const r=await fetch(url);if(!r.ok)throw Error('Unavailable study artifact: '+url);return r.json()}
async function clip(file){if(!cache.has(file))cache.set(file,(async()=>{const r=await fetch(folder+file);if(!r.ok)throw Error('Unavailable measured recording: '+file);const b=new Uint8Array(await r.arrayBuffer());return b[0]===31&&b[1]===139?new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).json():JSON.parse(new TextDecoder().decode(b))})());return cache.get(file)}
function play(value){playing=value;last=performance.now();$('#play').textContent=value?'Ⅱ':'▶'}
function status(meta){if(meta.success)return meta.component?'Component passed':'All four tasks verified';if(meta.complete){if(meta.quality_failures?.includes('forward_facing_fraction'))return `All tasks completed; forward-facing travel ${(meta.forward_facing_fraction*100).toFixed(3)}% (90% required)`;return 'All tasks completed; quality limit: '+(meta.quality_failures?.join(', ')||'exceeded').replaceAll('_',' ')}return 'Stopped: '+(meta.failure||'quality constraints exceeded').replaceAll('_',' ')}
async function select(id){const request=++serial;loading=true;play(false);selected=data.scenarios.find(s=>s.id===id);$('#scope').textContent='Loading '+selected.label+'…';
 episodes=await Promise.all([clip(selected.before),clip(selected.after)]);if(request!==serial)return;
 stages.forEach((stage,i)=>stage.setEpisode(episodes[i]));time=0;$('#scrub').max=Math.max(...episodes.map(e=>e.duration));
 if(mode==='motion')stages.forEach(stage=>selected.id==='recovery-component'?stage.inspect('hands'):stage.view(false));
 $('#left-title').textContent=selected.before_label;$('#right-title').textContent=selected.after_label;
 for(const side of ['left','right']){const meta=selected[side==='left'?'before_meta':'after_meta'];$('#'+side+'-proof').textContent=meta.sha256.slice(0,12);$('#'+side+'-outcome').textContent=mode==='motion'?`${status(meta)} · ${meta.duration.toFixed(2)} s · ${meta.steps} steps`+(meta.component&&meta.arm_jerk_rms!=null?` · measured arm jerk ${meta.arm_jerk_rms.toFixed(2)} rad/s³`:''):'';}
 $('#scope').textContent=selected.scope;
 $('#finding-title').textContent=selected.finding_title;$('#finding-detail').textContent=selected.finding_detail;
 $('#jumps').replaceChildren();if(!selected.before_meta.component){const label=document.createElement('span');label.textContent='Reference timeline:';$('#jumps').append(label);for(const [domain,title]of [['alarm','Clock'],['drawer','Drawer'],['laptop','Laptop'],['globe','Globe'],['recovery','Laptop arm return']]){const d=episodes[0].model_decisions?.find(d=>d.observation?.domain===domain&&(domain!=='recovery'||d.observation.task==='laptop'));if(!d)continue;const b=document.createElement('button');b.textContent=title;b.onclick=()=>{time=d.t;play(false);if(domain==='recovery'&&mode==='motion')stages.forEach(s=>s.inspect('hands'))};$('#jumps').append(b)}}
 loading=false;play(true);globalThis.__mochiV22={mode,data,report,stages,get selected(){return selected},get episodes(){return episodes},get time(){return time}};
 for(const key of cache.keys()){if(cache.size<=4)break;if(key!==selected.before&&key!==selected.after)cache.delete(key)}
}
function tick(now){const dt=Math.max(0,(now-last)/1000);last=now;if(episodes&&!loading){if(playing&&!document.hidden){time=Math.min(+$('#scrub').max,time+dt*+$('#speed').value);if(time>=+$('#scrub').max)play(false)}
 for(let i=0;i<2;i++){const e=episodes[i],t=Math.min(time,e.duration),frame=stages[i].frame(t),meta=selected[i?'after_meta':'before_meta'];const steps=stepCountAt(e,t),m=e.balance_measurements?.findLast(v=>v.t<=t);const tasks=taskStatesAt(e,t).filter(v=>v.status==='passed').map(v=>taskNames[v.task]);const phase=t>=e.duration-.005?status(meta):(frame?.phase||'Measured simulation').replaceAll('_',' ');$('#'+(i?'right':'left')+'-metrics').textContent=`${phase} · ${steps} measured steps · ${t.toFixed(1)} s`+(m?` · roll ${(m.roll_rad*180/Math.PI).toFixed(1)}°`:'')+(meta.component?'':`\nVerified tasks: ${tasks.join(', ')||'none yet'}`);}
 $('#time').textContent=`${time.toFixed(1)} / ${(+$('#scrub').max).toFixed(1)} s`;$('#scrub').value=time;}
 requestAnimationFrame(tick);}
async function init(){
 const active=$('#'+mode+'-tab');active.classList.add('active');
 [data,report]=await Promise.all([json(folder+mode+'-manifest.json'),json(folder+'report.json')]);
 $('#summary').textContent=data.summary;$('#asset-proof').textContent=report.asset_summary;$('#motion-proof').textContent=report.motion_summary;
 if(!data.scenarios.length){$('#scope').textContent='No candidate has completed physical evaluation yet.';$('#finding-title').textContent='Motion testing in progress';$('#finding-detail').textContent=data.summary;return;}
 stages=[(mode==='appearance'?originalStage:revisedStage)($('#left'),{scene:data.scene,fullBody:true,cameraOffset:[.35,-.46,.27]}),revisedStage($('#right'),{scene:data.scene,fullBody:true,cameraOffset:[.35,-.46,.27]})];await Promise.all(stages.map(s=>s.ready));
 for(const s of data.scenarios){const option=document.createElement('option');option.value=s.id;option.textContent=s.label;$('#scenario').append(option)}
 $('#scenario').onchange=e=>select(e.target.value);$('#play').onclick=()=>{if(!playing&&time>=+$('#scrub').max)time=0;play(!playing)};$('#restart').onclick=()=>{time=0;play(true)};$('#scrub').oninput=e=>{time=+e.target.value;play(false)};
 for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>stages.forEach(s=>['feet','hands'].includes(b.dataset.view)?s.inspect(b.dataset.view):s.view(b.dataset.view==='wide'));
 const params=new URLSearchParams(location.search),requested=params.get('scenario'),first=data.scenarios.find(s=>s.id===requested)||data.scenarios.find(s=>s.id===data.default_scenario)||data.scenarios[0];$('#scenario').value=first.id;await select(first.id);if(params.has('t')){time=Math.max(0,Math.min(+$('#scrub').max,+params.get('t')||0));play(false)}if(mode==='motion'&&params.get('view')==='hands')stages.forEach(s=>s.inspect('hands'));requestAnimationFrame(tick);
}
document.addEventListener('visibilitychange',()=>{last=performance.now()});init().catch(error=>{$('#scope').textContent=error.message;console.error(error)});
