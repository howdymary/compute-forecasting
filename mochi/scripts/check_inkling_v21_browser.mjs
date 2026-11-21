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
async function screenshot(name){const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync('mochi/.cache/inkling-v21-browser-'+name+'.png',Buffer.from(shot.data,'base64'))}
const url=process.argv[2]||'http://127.0.0.1:4120/inkling-v21.html';
await call('Page.enable');await call('Runtime.enable');await call('Network.enable');await call('Network.setCacheDisabled',{cacheDisabled:true});await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1200,deviceScaleFactor:1,mobile:false});await call('Page.navigate',{url});await call('Emulation.setFocusEmulationEnabled',{enabled:true});await call('Page.bringToFront');
await until(`document.querySelector('#right-id')?.textContent.length===12&&document.querySelectorAll('canvas').length===2`);
const manifest=await evaluate(`fetch('inkling-v21/manifest.json').then(r=>r.json())`);assert.equal(manifest.optimizer_updates_completed,0);
await evaluate(`(()=>{document.querySelector('#restart').click();document.querySelector('#speed').value='4'})()`);await screenshot('start');
const frames=[],start=Date.now();
while(Date.now()-start<120000){await new Promise(r=>setTimeout(r,2000));const x=await evaluate(`({time:+document.querySelector('#scrub').value,max:+document.querySelector('#scrub').max,steps:[+document.querySelector('#left-steps').textContent,+document.querySelector('#right-steps').textContent]})`);frames.push(x);if(x.time>=x.max-.02)break}
assert(frames.at(-1).time>=frames.at(-1).max-.02);const scenario=manifest.scenarios.find(s=>s.id===manifest.default_scenario);assert.deepEqual(frames.at(-1).steps,[manifest.recordings[scenario.parent_file].steps.attempts,manifest.recordings[scenario.versions.at(-1).file].steps.attempts]);await screenshot('end');
const inspected=[];for(const s of manifest.scenarios){await evaluate(`(()=>{const n=document.querySelector('#scenario');n.value=${JSON.stringify(s.id)};n.dispatchEvent(new Event('change',{bubbles:true}))})()`);await until(`document.querySelector('#scope').textContent.startsWith(${JSON.stringify(s.label+'. ')})`);await evaluate(`(()=>{const n=document.querySelector('#scrub');n.value=n.max;n.dispatchEvent(new Event('input',{bubbles:true}))})()`);const before=manifest.recordings[s.parent_file],after=manifest.recordings[s.versions.at(-1).file];await until(`+document.querySelector('#left-steps').textContent===${before.steps.attempts}&&+document.querySelector('#right-steps').textContent===${after.steps.attempts}`);const state=await evaluate(`({left:document.querySelector('#left-metrics').textContent,right:document.querySelector('#right-metrics').textContent,detail:document.querySelector('#pair-detail').textContent})`);if(after.qualified_complete)assert.match(state.right,/All tasks verified/);else assert(!/All tasks verified/.test(state.right));assert.match(state.detail,/globe_clearance_y_m = 0.055/);inspected.push({id:s.id,state});}
assert.equal(exceptions.length,0,exceptions.join('\n'));assert.equal(consoleErrors.length,0,consoleErrors.join('\n'));fs.writeFileSync('mochi/.cache/inkling-v21-browser-qa.json',JSON.stringify({url,study:manifest.study,recordings_verified:Object.keys(manifest.recordings).length,new_optimizer_updates:manifest.optimizer_updates_completed,continuous_playback:true,frames,inspected,exceptions,consoleErrors},null,2)+'\n');console.log(JSON.stringify({verified:inspected.length,exceptions,consoleErrors}));ws.close();
