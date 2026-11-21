import fs from 'node:fs';
import assert from 'node:assert/strict';
const url=process.argv[2]||'http://127.0.0.1:4123/task-preflight-v24.html';
const tabs=await(await fetch('http://127.0.0.1:9345/json/list')).json(),tab=tabs.find(t=>t.type==='page');
const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let id=0;const pending=new Map(),errors=[];
ws.addEventListener('message',event=>{const d=JSON.parse(event.data);if(d.id){const p=pending.get(d.id);if(p){pending.delete(d.id);clearTimeout(p.timer);d.error?p.reject(Error(JSON.stringify(d.error))):p.resolve(d.result)}}else if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.exception?.description||d.params.exceptionDetails.text)});
function call(method,params={}){return new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>reject(Error(method+' timeout')),60000);pending.set(key,{resolve,reject,timer});ws.send(JSON.stringify({id:key,method,params}))})}
async function run(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
await call('Page.enable');await call('Runtime.enable');await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1250,deviceScaleFactor:1,mobile:false});await call('Page.navigate',{url});
for(let i=0;i<360;i++){if(await run('!!window.__mochiTasks24&&!__mochiTasks24.loading'))break;await new Promise(r=>setTimeout(r,250));if(i===359)throw Error('Task viewer readiness timeout')}
const cases=await run('__mochiTasks24.manifest.cases.map(r=>r.id)'),checks=[];assert.equal(cases.length,5);
for(const ident of cases){await run(`(async()=>{document.querySelector('#attempt').value=${JSON.stringify(ident)};await __mochiTasks24.select();const s=document.querySelector('#seek');s.value=+s.max*.75;s.dispatchEvent(new Event('input',{bubbles:true}))})()`);await new Promise(r=>setTimeout(r,100));
 const checked=await run(`(()=>{const d=__mochiTasks24,e=d.episode,frames=e.trajectory.frames,t=d.time;let i=0;while(i+1<frames.length&&frames[i+1].t<=t)i++;const a=frames[i],b=frames[Math.min(i+1,frames.length-1)],u=Math.min(1,Math.max(0,(t-a.t)/Math.max(.0001,b.t-a.t)));let error=0,count=0;for(let k=0;k<e.trajectory.body_names.length;k++){const o=d.stage.bindings[e.trajectory.body_names[k]];if(!o)continue;o.updateWorldMatrix(true,false);for(let j=0;j<3;j++)error=Math.max(error,Math.abs(o.matrixWorld.elements[12+j]-(a.positions[k][j]+u*(b.positions[k][j]-a.positions[k][j]))));count++}return {id:d.row.id,bodies:count,error_m:error,recorded_frames:frames.length,canvases:document.querySelectorAll('#stage canvas').length,task_training_updates:d.manifest.task_optimizer_updates}})()`);
 assert(checked.bodies>=44);assert(checked.error_m<1e-6);assert.equal(checked.canvases,1);assert.equal(checked.task_training_updates,0);checks.push(checked);
}
await run(`(async()=>{document.querySelector('#attempt').value=__mochiTasks24.manifest.default_case;await __mochiTasks24.select();const s=document.querySelector('#seek');s.value=325;s.dispatchEvent(new Event('input',{bubbles:true}))})()`);await new Promise(r=>setTimeout(r,200));
const screenshot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync('mochi/evidence/navigation-tasks-v24/preflight.png',Buffer.from(screenshot.data,'base64'));
assert.equal(errors.length,0,errors.join('\n'));fs.writeFileSync('mochi/evidence/navigation-tasks-v24/browser-qa.json',JSON.stringify({url,checks,errors},null,2)+'\n');console.log(JSON.stringify({verified:true,continuous_recordings:checks.length}));ws.close();
