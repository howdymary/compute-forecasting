import fs from 'node:fs';
import assert from 'node:assert/strict';
const tabs=await(await fetch('http://127.0.0.1:9344/json/list')).json();
const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let serial=0;const pending=new Map();
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}});
function call(method,params={}){const id=++serial;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))})}
async function run(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result.value}
const url='https://howdymary--mochi-visual-motion-v22-demo-web.us-east.modal.run/?mode=motion&t=0';
await call('Page.navigate',{url});
let ready=false;for(let i=0;i<240;i++){if(await run('!!window.__mochiV22&&__mochiV22.mode==="motion"&&__mochiV22.selected.id==="recovery-component"')){ready=true;break}await new Promise(r=>setTimeout(r,250))}assert(ready);
const capture=`(()=>{const o=__mochiV22.stages[1].bindings.left_wrist_yaw_link;return {physical_seconds:__mochiV22.time,quaternion:o.quaternion.toArray(),position:o.position.toArray(),hidden:document.hidden}})()`;
const before=await run(capture);await run('document.querySelector("#restart").click()');
await new Promise(r=>setTimeout(r,1200));const after=await run(capture);await run('document.querySelector("#play").click()');
assert(after.physical_seconds-before.physical_seconds>.4);assert(after.physical_seconds<2.36);
const difference=Math.max(...after.quaternion.map((v,i)=>Math.abs(v-before.quaternion[i])));assert(difference>.01);
fs.writeFileSync('mochi/evidence/visual-motion-v22/live-playback-qa.json',JSON.stringify({verified:true,url,before,after,max_quaternion_component_change:difference,scope:'Continuous 1x playback advanced physical time and the recorded wrist pose.'},null,2)+'\n');
console.log(JSON.stringify({verified:true,physical_seconds_advanced:after.physical_seconds-before.physical_seconds,measured_pose_changed:true}));ws.close();
