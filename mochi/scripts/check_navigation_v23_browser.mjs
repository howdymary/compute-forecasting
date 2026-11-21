import fs from 'node:fs';
import assert from 'node:assert/strict';
const url=process.argv[2]||'http://127.0.0.1:4123/navigation-v23.html',port=process.env.MOCHI_QA_PORT||9345;
const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json(),tab=tabs.find(t=>t.type==='page');
const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let serial=0;const pending=new Map(),exceptions=[],errors=[];
ws.addEventListener('message',event=>{const d=JSON.parse(event.data);if(d.id){const p=pending.get(d.id);if(p){pending.delete(d.id);clearTimeout(p.timer);d.error?p.reject(Error(JSON.stringify(d.error))):p.resolve(d.result)}}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params.exceptionDetails.exception?.description||d.params.exceptionDetails.text);else if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')errors.push(d.params.args.map(x=>x.value||x.description).join(' '))});
function call(method,params={}){const id=++serial;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error(method+' timeout')),60000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})}
async function run(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
async function until(expression){for(let i=0;i<360;i++){if(await run(expression))return;await new Promise(r=>setTimeout(r,250))}throw Error('Viewer readiness timeout')}
await call('Page.enable');await call('Runtime.enable');await call('Network.enable');await call('Emulation.setDeviceMetricsOverride',{width:1700,height:1450,deviceScaleFactor:1,mobile:false});await call('Page.navigate',{url});await until('!!window.__mochiNav23&&!__mochiNav23.loading');
const cases=await run('__mochiNav23.manifest.cases.map(c=>({id:c.id,partition:c.partition,comparisons:Object.keys(c.runs).filter(k=>k!=="parent")}))'),checks=[];
const preview=await run('!!__mochiNav23.report.preview');assert.equal(cases.length,preview?16:32);
for(const scenario of process.argv.includes('--all')?cases:[cases[0],cases[2],cases[Math.floor(cases.length/2)],cases[Math.floor(cases.length/2)+2]]){
 await run(`(async()=>{document.querySelector('#scenario').value=${JSON.stringify(scenario.id)};await __mochiNav23.select()})()`);
 const candidates=scenario.comparisons;
 for(const candidate of process.argv.includes('--all')?candidates:[candidates[0]]){
  await run(`(async()=>{document.querySelector('#candidate').value=${JSON.stringify(candidate)};await __mochiNav23.select();const s=document.querySelector('#scrub');s.value=+s.max*.7;s.dispatchEvent(new Event('input',{bubbles:true}))})()`);
  await new Promise(r=>setTimeout(r,100));
  const result=await run(`(()=>{const d=__mochiNav23,errors=[];for(let side=0;side<2;side++){const e=d.episodes[side],t=Math.min(d.time,e.duration),frames=e.trajectory.frames;let i=0;while(i+1<frames.length&&frames[i+1].t<=t)i++;const a=frames[i],b=frames[Math.min(i+1,frames.length-1)],u=Math.min(1,Math.max(0,(t-a.t)/Math.max(.0001,b.t-a.t)));let error=0,count=0;for(let k=0;k<e.trajectory.body_names.length;k++){const o=d.stages[side].bindings[e.trajectory.body_names[k]];if(!o)continue;o.updateWorldMatrix(true,false);for(let j=0;j<3;j++)error=Math.max(error,Math.abs(o.matrixWorld.elements[12+j]-(a.positions[k][j]+u*(b.positions[k][j]-a.positions[k][j]))));count++}errors.push({bodies:count,error_m:error,frames:frames.length})}return {id:d.selected.id,layout:d.rows[0].layout_sha256,same_scene:JSON.stringify(d.rows[0].layout.scene)===JSON.stringify(d.rows[1].layout.scene),same_initial_state:d.rows[0].initial_physical_state_sha256===d.rows[1].initial_physical_state_sha256,checks:errors,canvases:document.querySelectorAll('.stage canvas').length}})()`);
  assert(result.same_scene&&result.same_initial_state);assert.equal(result.canvases,2);result.checks.forEach(c=>{assert(c.bodies>=44);assert(c.error_m<1e-6);assert(c.frames>=1)});checks.push({...result,candidate});
 }
}
await run(`(()=>{document.querySelector('#scenario').value=__mochiNav23.manifest.default_case;document.querySelector('#candidate').value=__mochiNav23.manifest.default_comparison;return __mochiNav23.select()})()`);
await run(`(()=>{const s=document.querySelector('#scrub');s.value=+s.max*.55;s.dispatchEvent(new Event('input',{bubbles:true}))})()`);await new Promise(r=>setTimeout(r,500));
const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.mkdirSync('mochi/evidence/navigation-v23',{recursive:true});fs.writeFileSync('mochi/evidence/navigation-v23/comparison'+(preview?'-preview':'')+'.png',Buffer.from(shot.data,'base64'));
const state=await run(`({updates:__mochiNav23.report.optimizer_updates_completed,selected_update:__mochiNav23.report.selected_checkpoint?.update,preview_checkpoint:__mochiNav23.report.preview_checkpoint,final_summaries:__mochiNav23.report.final_summaries,scene_hashes:[...new Set(__mochiNav23.manifest.cases.map(c=>c.runs.parent.row.layout_sha256))]})`);
assert(state.updates>0);assert.equal(state.scene_hashes.length,preview?8:16);assert.equal(exceptions.length,0,exceptions.join('\n'));assert.equal(errors.length,0,errors.join('\n'));
fs.writeFileSync('mochi/evidence/navigation-v23/browser-qa'+(preview?'-preview':'')+'.json',JSON.stringify({url,preview,...state,checks,exceptions,errors},null,2)+'\n');console.log(JSON.stringify({verified:true,preview,comparisons:checks.length,layouts:state.scene_hashes.length}));ws.close();
