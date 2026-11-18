import {createCurriculumStage} from './curriculum-stage.js';
const $=q=>document.querySelector(q),stages=[createCurriculumStage($('#route-before')),createCurriculumStage($('#route-after'))];
let manifest,route,rows=[],episodes=[],time=0,playing=true,overlay=true,last=performance.now(),duration=0,loading=true,request=0;
const get=async path=>{const response=await fetch(path);if(!response.ok)throw Error('Could not load '+path);return response.json()};
const fmt=(x,d=1)=>x==null?'—':Number(x).toFixed(d),taskCount=m=>Object.values(m.task_success).filter(Boolean).length;
async function loadCase(seed){const ticket=++request;loading=true;playing=false;const selected=manifest.cases.filter(r=>r.seed===Number(seed)),loaded=await Promise.all(selected.map(r=>get('planning/'+r.file)));if(ticket!==request)return;rows=selected;episodes=loaded;episodes.forEach((e,i)=>{stages[i].setEpisode(e);stages[i].setReference(i?route:oldReference(e));stages[i].topDown();stages[i].showReference(overlay)});duration=Math.max(...episodes.map(e=>e.duration));$('#route-scrub').max=duration;time=0;loading=false;playing=true;$('#route-play').textContent='Ⅱ'}
function oldReference(e){const poses=[e.trajectory.frames[0].positions[1],...route.old_route.map(r=>r.pose)];return{legs:route.old_route.map((r,i)=>({goal:r.pose,segments:[{from:poses[i].slice(0,2),to:r.pose.slice(0,2)}]}))}}
function describe(e,m,t){if(t>=e.duration)return `${m.full_sequence_success?'Four tasks verified':m.fall?'Stopped after a fall':'Episode ended'} · ${taskCount(m)}/4 tasks`;const trace=e.reference_tracking?.findLast(x=>x.t<=t);const f=e.trajectory.frames.findLast(f=>f.t<=t)||e.trajectory.frames[0];return `${f.task||'navigation'} / ${f.phase}${trace&&f.phase==='walk'?' · cross-track '+fmt(trace.cross_track_mm)+' mm':''}`}
async function init(){
 [manifest,route]=await Promise.all([get('planning/results.json'),get('planning/route.json')]);
 $('#planning-status').textContent=manifest.status_text;
 $('#route-summary').textContent=`${fmt(route.length_m,3)} m reference · version ${route.version}. Best feasible route found on the bounded graph; nominal travel estimate excludes acceleration, settling and manipulation.`;
 $('#route-diagnosis').textContent=manifest.diagnosis;
 $('#route-storage').textContent=manifest.storage_text;
 $('#route-provenance').textContent=manifest.provenance_text;
 for(const seed of [...new Set(manifest.cases.map(r=>r.seed))]){const o=document.createElement('option');o.value=seed;o.textContent='Calibration '+seed;$('#route-case').append(o)}
 for(const r of manifest.cases){const m=r.metrics,tr=document.createElement('tr');for(const value of [`${r.seed} / ${r.label}`,`${m.arrivals}/${m.required_arrivals}`,`${taskCount(m)}/4`,fmt(m.walking_duration_s)+' s',fmt(m.walking_path_m,3)+' m'+(m.navigation_success?'':' (partial/failed)'),fmt(m.arrival_position_mean_mm)+' mm',m.fall?'Yes':'No']){const td=document.createElement('td');td.textContent=value;tr.append(td)}$('#route-results').append(tr)}
 $('#route-results-note').textContent=manifest.results_note;
 for(const read of manifest.services?.reads||[]){if(!read.cross_agent_use)continue;const p=document.createElement('p');p.textContent=`Verified ${read.reader_role} recall ← ${read.record_id}`;$('#route-memory').append(p)}
 for(const search of manifest.services?.sources||[])for(const source of search.sources){if(!/^https?:\/\//.test(source.url))continue;const a=document.createElement('a');a.href=source.url;a.target='_blank';a.rel='noopener';a.textContent=source.title;$('#route-sources').append(a)}
 await Promise.all(stages.map(s=>s.ready));await loadCase(manifest.primary_calibration_seed);
}
$('#route-case').onchange=()=>loadCase($('#route-case').value).catch(fail);
$('#route-overhead').onclick=()=>stages.forEach(s=>s.topDown());$('#route-follow').onclick=()=>stages.forEach(s=>s.view(false));$('#route-side').onclick=()=>stages.forEach(s=>s.inspect('gait'));$('#route-feet').onclick=()=>stages.forEach(s=>s.inspect('feet'));
$('#route-overlay').onclick=()=>{overlay=!overlay;stages.forEach(s=>s.showReference(overlay));$('#route-overlay').textContent=overlay?'Hide path':'Show path';$('#route-overlay').setAttribute('aria-pressed',String(overlay))};
$('#route-play').onclick=()=>{playing=!playing;$('#route-play').textContent=playing?'Ⅱ':'▶'};$('#route-reset').onclick=()=>{time=0};$('#route-scrub').oninput=()=>{time=Number($('#route-scrub').value);playing=false;$('#route-play').textContent='▶'};
function animate(now){const dt=Math.min(.1,(now-last)/1000);last=now;if(!loading){if(playing)time=Math.min(duration,time+dt);stages.forEach((s,i)=>s.frame(Math.min(time,episodes[i].duration)));$('#route-time').textContent=fmt(time)+' s';$('#route-scrub').value=time;$('#route-before-state').textContent=describe(episodes[0],rows[0].metrics,time);$('#route-after-state').textContent=describe(episodes[1],rows[1].metrics,time);if(time>=duration){playing=false;$('#route-play').textContent='▶'}}requestAnimationFrame(animate)}
function fail(e){$('#planning-status').textContent=e.message;playing=false}
requestAnimationFrame(animate);init().catch(fail);
