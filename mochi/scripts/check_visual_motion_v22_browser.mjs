import fs from 'node:fs';
import assert from 'node:assert/strict';
const url=process.argv[2]||'http://127.0.0.1:4122/visual-motion-v22.html',port=process.env.MOCHI_QA_PORT||9344;
const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();const tab=tabs.find(t=>t.type==='page');const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));let serial=0;const pending=new Map(),exceptions=[],errors=[];
ws.addEventListener('message',event=>{const d=JSON.parse(event.data);if(d.id){const p=pending.get(d.id);if(p){pending.delete(d.id);clearTimeout(p.timer);d.error?p.reject(Error(JSON.stringify(d.error))):p.resolve(d.result)}}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params.exceptionDetails.exception?.description||d.params.exceptionDetails.text);else if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')errors.push(d.params.args.map(x=>x.value||x.description).join(' '))});
function call(method,params={}){const id=++serial;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error(method+' timeout')),45000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})}
async function run(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
async function until(expression){for(let i=0;i<240;i++){if(await run(expression))return;await new Promise(r=>setTimeout(r,250))}throw Error('Readiness timeout')}
await call('Page.enable');await call('Runtime.enable');await call('Network.enable');await call('Network.setCacheDisabled',{cacheDisabled:true});await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1300,deviceScaleFactor:1,mobile:false});await call('Page.navigate',{url});await until(`!!window.__mochiV22`);
const state=await run(`({mode:__mochiV22.mode,scenarios:__mochiV22.data.scenarios.length,summary:document.querySelector('#summary').textContent,bindings:Object.keys(__mochiV22.stages[1].bindings||{}).length,before:__mochiV22.selected.before_meta.sha256,after:__mochiV22.selected.after_meta.sha256})`);if(state.mode==='appearance')assert.equal(state.before,state.after);assert(state.bindings>=44);
await run(`(()=>{const s=document.querySelector('#scrub');s.value=__mochiV22.mode==='motion'&&__mochiV22.selected.before_meta.component?+s.max/2:Math.min(245,+s.max);s.dispatchEvent(new Event('input',{bubbles:true}))})()`);await new Promise(r=>setTimeout(r,1200));
const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync('mochi/.cache/visual-motion-v22/'+state.mode+'-comparison.png',Buffer.from(shot.data,'base64'));
const cases=[];
if(process.argv.includes('--all')){
 const scenarios=await run(`__mochiV22.data.scenarios.map(s=>({id:s.id,scope:s.scope}))`);
 for(const s of scenarios){
  await run(`(()=>{const s=document.querySelector('#scenario');s.value=${JSON.stringify(s.id)};s.dispatchEvent(new Event('change',{bubbles:true}))})()`);
  await until(`__mochiV22.selected.id===${JSON.stringify(s.id)}&&document.querySelector('#scope').textContent===${JSON.stringify(s.scope)}&&!document.querySelector('#scope').textContent.startsWith('Loading')`);
  await run(`(()=>{const s=document.querySelector('#scrub');s.value=+s.max*.6;s.dispatchEvent(new Event('input',{bubbles:true}))})()`);
  await new Promise(r=>setTimeout(r,300));
  const check=await run(`(()=>{const d=__mochiV22,e=d.episodes[1],t=Math.min(d.time,e.duration),frames=e.trajectory.frames;let i=0;while(i+1<frames.length&&frames[i+1].t<=t)i++;const a=frames[i],b=frames[Math.min(i+1,frames.length-1)],u=Math.min(1,Math.max(0,(t-a.t)/Math.max(.0001,b.t-a.t))),names=e.trajectory.body_names;let error=0,n=0;for(let k=0;k<names.length;k++){const o=d.stages[1].bindings[names[k]];if(!o)continue;o.updateWorldMatrix(true,false);const p=o.matrixWorld.elements;for(let j=0;j<3;j++)error=Math.max(error,Math.abs(p[12+j]-(a.positions[k][j]+u*(b.positions[k][j]-a.positions[k][j]))));n++;}return {id:d.selected.id,bodies:n,max_body_position_error_m:error,before_frames:d.episodes[0].trajectory.frames.length,after_frames:e.trajectory.frames.length,scope:document.querySelector('#scope').textContent}})()`);
  assert(check.bodies>=44);assert(check.max_body_position_error_m<1e-6,JSON.stringify(check));assert(check.before_frames>1&&check.after_frames>1);cases.push(check);
 }
}
assert.equal(exceptions.length,0,exceptions.join('\n'));assert.equal(errors.length,0,errors.join('\n'));fs.writeFileSync('mochi/.cache/visual-motion-v22/'+state.mode+'-browser-qa.json',JSON.stringify({url,...state,cases,exceptions,errors},null,2)+'\n');console.log(JSON.stringify({verified:true,...state,cases_checked:cases.length}));ws.close();
