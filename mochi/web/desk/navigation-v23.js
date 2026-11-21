import {createNavigationStage} from './navigation-v23-stage.js';
import {stepCountAt} from './efficient-evidence.mjs';
const $=q=>document.querySelector(q),folder='navigation-v23/';
let manifest,report,selected,stages=[],episodes=[],rows=[],time=0,playing=false,loading=true,last=performance.now(),serial=0;
const cache=new Map();
async function json(file){const r=await fetch(folder+file);if(!r.ok)throw Error('Study artifact unavailable: '+file);return r.json()}
async function clip(file){if(!cache.has(file))cache.set(file,(async()=>{const r=await fetch(folder+file);if(!r.ok)throw Error('Measured trajectory unavailable: '+file);const b=new Uint8Array(await r.arrayBuffer());return b[0]===31&&b[1]===139?new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).json():JSON.parse(new TextDecoder().decode(b))})());return cache.get(file)}
const fmt=(n,d=1)=>n==null?'unavailable':Number(n).toFixed(d);
const label=r=>r.qualified?'Qualified arrival':r.complete?'Arrived; physical quality limit exceeded':'Stopped: '+(r.failure||'verification failed').replaceAll('-',' ');
function play(value){playing=value;last=performance.now();$('#play').textContent=value?'Ⅱ':'▶'}
function view(value){for(const s of stages)value==='overhead'?s.topDown():value==='feet'?s.inspect('feet'):s.view(value==='wide')}
async function select(){
 const request=++serial;loading=true;play(false);$('#scope').textContent='Loading the same layout into both physical replays…';
 selected=manifest.cases.find(c=>c.id===$('#scenario').value);for(const option of $('#candidate').options)option.disabled=!selected.runs[option.value];if(!selected.runs[$('#candidate').value])$('#candidate').value=selected.runs.selected?'selected':Object.keys(selected.runs).find(k=>k!=='parent');const candidate=$('#candidate').value;
 const memoryComparison=candidate==='selected_memory_enabled',left=selected.runs[memoryComparison?'selected':'parent'],right=selected.runs[candidate];if(!right)throw Error('This comparison was not physically evaluated.');
 const next=await Promise.all([clip(left.file),clip(right.file)]);if(request!==serial)return;
 stages.forEach(s=>s.dispose());rows=[left.row,right.row];episodes=next;
 stages=[createNavigationStage($('#left'),episodes[0],rows[0]),createNavigationStage($('#right'),episodes[1],rows[1])];
 await Promise.all(stages.map(s=>s.ready));if(request!==serial)return;
 stages.forEach(s=>s.overlays($('#overlays').checked));view('follow');time=0;$('#scrub').max=Math.max(...episodes.map(e=>e.duration));
 $('#left-title').textContent=memoryComparison?'SELECTED · MEMORY DISABLED':'PARENT · UPDATE 0';$('#right-title').textContent=manifest.comparisons.find(c=>c.id===candidate).label+(right.row.selection?.optimizer_updates!=null?' · UPDATE '+right.row.selection.optimizer_updates:'');
 rows.forEach((r,i)=>{const side=i?'right':'left';$('#'+side+'-proof').textContent=(r.selection?.checkpoint_id||r.public_recording.sha256).slice(0,12);$('#'+side+'-outcome').textContent=`${label(r)} · ${r.action} · ${r.steps.attempts} steps · ${fmt(r.physical_seconds)} s`;$('#'+side+'-outcome').dataset.status=r.qualified?'pass':'fail'});
 $('#scope').textContent=(report.preview?'DEVELOPMENT PREVIEW · FINAL LAYOUTS UNOPENED · ':'')+`${selected.label}. Identical layout ${rows[0].layout_sha256.slice(0,12)}, seed ${rows[0].seed}, initial state ${rows[0].initial_physical_state_sha256.slice(0,12)}. Both recordings play at the same speed.`;
 if(selected.id===manifest.default_case&&manifest.highlight_reason)$('#scope').textContent+=' '+manifest.highlight_reason;
 const [a,b]=rows;
 if(a.qualified&&b.qualified){const delta=a.steps.attempts-b.steps.attempts;$('#finding-title').textContent=(delta===0?'The same number of steps.':`${Math.abs(delta)} ${delta>0?'fewer':'additional'} steps.`)+(delta>0&&b.physical_seconds>a.physical_seconds+.05?` ${fmt(b.physical_seconds-a.physical_seconds)} s slower.`:'');$('#finding-detail').textContent=`Both routes qualified. ${memoryComparison?'Memory disabled':'Parent'}: ${a.action}; comparison: ${b.action}. Measured pelvis distance ${fmt(a.executed_distance_m,2)} → ${fmt(b.executed_distance_m,2)} m. Physical time ${fmt(a.physical_seconds)} → ${fmt(b.physical_seconds)} s. This case is one part of the complete cohort shown below.`}
 else{$('#finding-title').textContent=b.qualified?'Only the comparison qualified.':a.qualified?'The comparison regressed.':'Neither attempt qualified.';$('#finding-detail').textContent='Efficiency gains require both versions to pass. Arrival, support, roll, foot clearance and collision checks remain fixed. Failed attempts stay in the evidence.'}
 loading=false;play(true);
 globalThis.__mochiNav23={manifest,report,select,view,get selected(){return selected},get rows(){return rows},get episodes(){return episodes},get stages(){return stages},get time(){return time},get loading(){return loading}};
 for(const key of cache.keys()){if(cache.size<=4)break;if(key!==left.file&&key!==right.file)cache.delete(key)}
}
function tick(now){const dt=Math.max(0,(now-last)/1000);last=now;if(episodes.length&&!loading){if(playing&&!document.hidden){time=Math.min(+$('#scrub').max,time+dt*+$('#speed').value);if(time>=+$('#scrub').max)play(false)}
 rows.forEach((r,i)=>{const t=Math.min(time,episodes[i].duration),frame=stages[i].frame(t);$('#'+(i?'right':'left')+'-metrics').textContent=`${t>=episodes[i].duration-.005?label(r):(frame?.phase||'walking').replaceAll('_',' ')} · ${stepCountAt(episodes[i],t)} steps · ${fmt(t)} s\n${r.action} route · update ${r.selection?.optimizer_updates??'fixed'} · nominal envelope clearance ${fmt(r.minimum_envelope_clearance_m*1000)} mm · forbidden contact ${r.invalid_contact?'detected':'none'}`});$('#time').textContent=`${fmt(time)} / ${fmt(+$('#scrub').max)} s`;$('#scrub').value=time;}requestAnimationFrame(tick)}
function text(tag,value,parent){const e=document.createElement(tag);e.textContent=value;parent.append(e);return e}
function trainingPlans(){
 const ns='http://www.w3.org/2000/svg',svg=(tag,attrs,parent)=>{const e=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);parent.append(e);return e},xy=p=>[(p[0]+.6)*200,(.4-p[1])*200];
 report.training_trials.forEach((trial,i)=>{const row=trial.outcomes[trial.target||'direct'],box=document.createElement('article');box.className='training-layout';const plan=svg('svg',{viewBox:'0 0 240 160',role:'img','aria-label':'Training layout '+(i+1)},box);
 svg('rect',{x:0,y:0,width:240,height:160,rx:6,fill:'#d7d6c5'},plan);
 for(const obstacle of row.obstacles){const a=xy(obstacle.minimum),b=xy(obstacle.maximum);svg('rect',{x:a[0],y:b[1],width:Math.max(.6,b[0]-a[0]),height:Math.max(.6,a[1]-b[1]),fill:'#969d8a',opacity:.7},plan)}
 const points=row.plans[trial.target||'direct']?.points||[];if(points.length)svg('polyline',{points:points.map(p=>xy(p).join(',')).join(' '),fill:'none',stroke:'#285f62','stroke-width':2},plan);
 const start=xy(row.layout.scene.initial_pose),goal=xy(row.layout.goal);svg('circle',{cx:start[0],cy:start[1],r:3,fill:'#285f62'},plan);svg('circle',{cx:goal[0],cy:goal[1],r:4,fill:'none',stroke:'#ac603d','stroke-width':2},plan);
 text('strong',String(i+1).padStart(2,'0')+' · '+(trial.target||'No qualified candidate'),box);text('span',Object.values(trial.outcomes).filter(r=>r.qualified).length+'/3 qualified candidates',box);$('#training-layouts').append(box)})
}
function evidence(){
 const chosen=report.selected_checkpoint?.update??report.preview_checkpoint;
 $('#summary').textContent=report.public_summary;
 $('#freeze-proof').textContent=report.selection_freeze?`Checkpoint selection frozen ${report.selection_freeze.at.replace('T',' ').slice(0,19)} UTC. Final layout-set fingerprint ${report.split_manifest.final_navigation.sha256.slice(0,16)}. The eight final layouts were withheld from training and selection.`:'Development recordings. Final comparison and checkpoint selection are pending.';
 for(const [value,caption]of [[String(report.optimizer_updates_completed),'completed optimizer updates'],[String(report.layout_counts.final_navigation),report.preview?'fixed development layouts':'unseen final layouts'],[String(report.actual_physical_attempts),'physical attempts, including engineering'],[String(report.services.eligibility.cross_agent_reads),'source-verified cross-role recalls']]){const box=document.createElement('div');box.className='total';text('strong',value,box);text('span',caption,box);$('#totals').append(box)}
 const table=document.createElement('table'),head=document.createElement('tr');['Method','Qualified','Falls','Steps on successes'].forEach(v=>text('th',v,head));table.append(head);
 const cohorts=report.preview?[['Parent',report.development['0'].summary],...Object.entries(report.development).filter(([u])=>u!=='0').map(([u,v])=>['Update '+u,v.summary])]:[['Parent','parent'],['Selected · '+chosen+' updates','selected'],['Collision-aware planner','planner'],['Conventional tuning','conventional'],['Strongest fixed strategy','fixed']].map(([name,key])=>[name,report.final_summaries[key]]);
 for(const [name,s]of cohorts){const tr=document.createElement('tr');[name,`${s.qualified}/${s.n}`,s.falls,fmt(s.qualified_mean_steps)].forEach(v=>text('td',String(v),tr));table.append(tr)}$('#results-table').append(table);
 if(report.preview)$('#cohort-label').textContent='FIXED DEVELOPMENT LAYOUTS · FINAL EVALUATION PENDING';
 $('#training-proof').textContent=`Tinker post-trained rank-${report.protocol.lora_rank} LoRA weights on ${report.protocol.model}. Targets came from physically executed candidates in ${report.training_trials.length} training layouts. `+(report.preview?`Update ${chosen} is the latest fully evaluated checkpoint in this preview; selection is still pending.`:`Development evaluation selected update ${chosen} before final layouts were opened.`);
 for(const cp of report.checkpoints){const div=document.createElement('div');div.className='checkpoint';text('span',`Update ${cp.update} · ${report.development[String(cp.update)]?.summary.qualified??'pending'}/16 qualified development attempts`,div);text('code',cp.checkpoint_id.slice(0,16),div);$('#checkpoints').append(div)}
 for(const search of report.services.sources){for(const source of search.sources){const div=document.createElement('div');div.className='source';const a=text('a',source.title||source.url,div);a.href=source.url;a.target='_blank';a.rel='noopener';text('p',source.excerpt,div);$('#sources').append(div)}}
 const allocation=report.services.decisions.find(d=>d.role==='designer');$('#research-use').textContent=allocation?`The design step recalled these sources through past.dev and selected ${allocation.selected.replaceAll('_',' ')} for measured training examples. Search did not design the shared controller repair; its incremental performance benefit was not isolated.`:'The complete source-to-decision record is available in the evidence.';
 $('#memory-proof').textContent=`${report.services.eligibility.writers} writing identities and ${report.services.eligibility.readers} reading identities exchanged source-verified evidence. Private audience isolation ${report.services.eligibility.isolation_passed?'passed':'was not verified'}. First attempts used training-only memory. Retry memories were isolated by layout and policy.`;
 $('#memory-result').textContent=report.memory_summary;
 $('#execution-proof').textContent=`Modal ran ${report.physics_receipts.length} primary cloud attempts with at most ${report.protocol.bounds.modal_concurrency} workers. Simulation budget accounting, including engineering and conservatively retained unused reservations: ${fmt(report.usage_actual_or_reserved.simulation_cpu_hours,2)} single-core hours. Actual per-call durations are recorded separately. Native walking-network weights were not updated.`;
 $('#phase-b').textContent=report.phase_b_status;
 trainingPlans();
}
async function init(){[manifest,report]=await Promise.all([json('manifest.json'),json('report.json')]);evidence();
 for(const c of manifest.cases){const o=document.createElement('option');o.value=c.id;o.textContent=c.label;$('#scenario').append(o)}
 for(const c of manifest.comparisons){const o=document.createElement('option');o.value=c.id;o.textContent=c.label;$('#candidate').append(o)}
 $('#candidate').value=manifest.default_comparison;$('#scenario').value=manifest.default_case;
 $('#next-layout').onclick=()=>{const partition=manifest.cases.some(c=>c.partition==='final')?'final':'development',choices=manifest.cases.filter(c=>c.partition===partition&&c.runs.parent.row.seed===report.protocol.physics_seeds[0]),current=choices.findIndex(c=>c.runs.parent.row.layout_sha256===selected.runs.parent.row.layout_sha256);$('#scenario').value=choices[(current+1)%choices.length].id;select()};
 $('#scenario').onchange=select;$('#candidate').onchange=select;$('#play').onclick=()=>{if(!playing&&time>=+$('#scrub').max)time=0;play(!playing)};$('#restart').onclick=()=>{time=0;play(true)};$('#scrub').oninput=e=>{time=+e.target.value;play(false)};
 $('#overlays').onchange=e=>stages.forEach(s=>s.overlays(e.target.checked));for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>view(b.dataset.view);
 await select();const q=new URLSearchParams(location.search);if(q.has('t')){time=Math.max(0,Math.min(+$('#scrub').max,+q.get('t')||0));play(false)}if(q.get('view'))view(q.get('view'));requestAnimationFrame(tick)
}
document.addEventListener('visibilitychange',()=>{last=performance.now()});init().catch(e=>{$('#scope').textContent=e.message;$('#scope').classList.add('error');console.error(e)});
