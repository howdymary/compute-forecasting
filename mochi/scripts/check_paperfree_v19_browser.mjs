import fs from 'node:fs';
import assert from 'node:assert/strict';

const list=await (await fetch(`http://127.0.0.1:${process.env.MOCHI_QA_PORT||9342}/json/list`)).json();
const target=list.find(t=>t.type==='page');
assert(target,'The dedicated QA browser must be running');
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
let serial=0;const pending=new Map(),exceptions=[],consoleErrors=[];
ws.addEventListener('message',event=>{
 const item=JSON.parse(event.data);
 if(item.id){const task=pending.get(item.id);if(!task)return;pending.delete(item.id);clearTimeout(task.timer);item.error?task.reject(Error(JSON.stringify(item.error))):task.resolve(item.result)}
 else if(item.method==='Runtime.exceptionThrown')exceptions.push(item.params.exceptionDetails.exception?.description||item.params.exceptionDetails.text);
 else if(item.method==='Runtime.consoleAPICalled'&&item.params.type==='error')consoleErrors.push(item.params.args.map(a=>a.value||a.description).join(' '));
});
function call(method,params={}){const id=++serial;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout: '+method))},45000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
async function until(expression){for(let i=0;i<180;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,250))}throw Error('Readiness timeout: '+expression)}
async function screenshot(name){const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync('mochi/.cache/paperfree-v19-browser-'+name+'.png',Buffer.from(shot.data,'base64'))}
const url=process.argv[2]||'http://127.0.0.1:4120/paperfree-v19.html';
await call('Page.enable');await call('Runtime.enable');await call('Network.enable');await call('Network.setCacheDisabled',{cacheDisabled:true});
await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1200,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url});await call('Emulation.setFocusEmulationEnabled',{enabled:true});await call('Page.bringToFront');
await until(`document.visibilityState==='visible'`);
await until(`document.querySelector('#right-id')?.textContent.length===12&&document.querySelectorAll('canvas').length===2`);
const manifest=await evaluate(`fetch('paperfree-v19/manifest.json').then(r=>r.json())`);
assert.equal(manifest.optimizer_updates_completed,8);assert.equal(manifest.selection_finalized,true);assert.equal(manifest.selected_update,1);
assert.equal(Object.keys(manifest.recordings).length,manifest.evaluation_status==='completed'?20:12);
const s=manifest.scenarios.find(s=>s.id===manifest.default_scenario),v=s.versions.find(v=>v.update===1),left=manifest.recordings[s.parent_file],right=manifest.recordings[v.file];
assert(v);await evaluate(`(()=>{document.querySelector('#restart').click();document.querySelector('#speed').value='4'})()`);
await screenshot('progression-start');const frames=[],wallStart=Date.now();
while(Date.now()-wallStart<120000){await new Promise(r=>setTimeout(r,2000));const f=await evaluate(`({time:+document.querySelector('#scrub').value,max:+document.querySelector('#scrub').max,steps:[+document.querySelector('#left-steps').textContent,+document.querySelector('#right-steps').textContent]})`);frames.push(f);if(f.time>=f.max-.02)break}
const end=frames.at(-1);assert(end.time>=end.max-.02);assert.deepEqual(end.steps,[left.steps.attempts,right.steps.attempts]);
await evaluate(`document.querySelector('.step-breakdown').open=true`);await screenshot('progression-end');
const inspected=[],inspectedFiles=new Set();
for(const scenario of manifest.scenarios){
 await evaluate(`(()=>{const n=document.querySelector('#scenario');n.value=${JSON.stringify(scenario.id)};n.dispatchEvent(new Event('change',{bubbles:true}))})()`);
 await until(`document.querySelector('#scope').textContent.startsWith(${JSON.stringify(scenario.label+'. ')})`);
 for(let index=0;index<scenario.versions.length;index++){
  const version=scenario.versions[index],before=manifest.recordings[scenario.parent_file],after=manifest.recordings[version.file];
  await evaluate(`(()=>{const n=document.querySelector('#checkpoint');n.value=${index};n.dispatchEvent(new Event('input',{bubbles:true}))})()`);
  await until(`document.querySelector('#scope').textContent.startsWith(${JSON.stringify(scenario.label+'. ')})&&document.querySelector('#right-id').textContent===${JSON.stringify(after.checkpoint_id.slice(0,12))}`);
  await evaluate(`(()=>{const n=document.querySelector('#scrub');n.value=n.max;n.dispatchEvent(new Event('input',{bubbles:true}))})()`);
  await until(`+document.querySelector('#left-steps').textContent===${before.steps.attempts}&&+document.querySelector('#right-steps').textContent===${after.steps.attempts}`);
  const state=await evaluate(`({left:document.querySelector('#left-metrics').textContent,right:document.querySelector('#right-metrics').textContent,detail:document.querySelector('#pair-detail').textContent,breakdown:[...document.querySelectorAll('#step-breakdown tr')].map(r=>[...r.cells].map(c=>c.textContent)),tasks:[...document.querySelectorAll('.task-state')].map(e=>({id:e.id,text:e.textContent,status:e.className}))})`);
  assert.deepEqual(state.breakdown.at(-1),['Total attempts',String(before.steps.attempts),String(after.steps.attempts)]);
  if(after.qualified_complete)assert.match(state.right,/All tasks verified/);else if(after.complete)assert.match(state.right,/quality limits exceeded/);else assert(!/All tasks verified/.test(state.right));
  for(const [side,meta]of [['left',before],['right',after]])for(const [task,passed]of Object.entries(meta.task_outcomes)){if(!passed)continue;assert(state.tasks.find(t=>t.id===side+'-task-'+task)?.status.includes('passed'))}
  inspectedFiles.add(scenario.parent_file);inspectedFiles.add(version.file);
  inspected.push({scenario:scenario.id,update:version.update,expected_steps:[before.steps.attempts,after.steps.attempts],state});
  if(version.update===4&&scenario.id==='development-212000')await screenshot('rejected-checkpoint-4');
 }
}
await evaluate(`(()=>{const n=document.querySelector('#scenario');n.value='development-212002';n.dispatchEvent(new Event('change',{bubbles:true}))})()`);
await until(`document.querySelector('#scope').textContent.startsWith('Development scenario 212002. ')&&!document.querySelector('#after-descent').disabled`);
await evaluate(`document.querySelector('#after-descent').click()`);await new Promise(r=>setTimeout(r,2000));await screenshot('progression-feet');
assert.equal(exceptions.length,0,exceptions.join('\n'));assert.equal(consoleErrors.length,0,consoleErrors.join('\n'));
const result={url,status:manifest.evaluation_status,continuous_playback:true,steps:end.steps,frames,comparisons_inspected:inspected.length,unique_recordings_inspected:inspectedFiles.size,inspected_files:[...inspectedFiles],inspected,exceptions,consoleErrors};
fs.writeFileSync('mochi/.cache/paperfree-v19-final-browser-qa.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({verified:manifest.evaluation_status,steps:end.steps,comparisons_inspected:inspected.length,unique_recordings_inspected:inspectedFiles.size,exceptions,consoleErrors}));ws.close();
