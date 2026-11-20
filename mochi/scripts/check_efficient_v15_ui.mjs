import {stepCountAt,taskStatesAt,comparisonEvidence,taskNames,activityAt} from '../web/desk/efficient-evidence.mjs';
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {gunzipSync} from 'node:zlib';

const base='mochi/web/desk/',folder='efficient-v15/',page='efficient-trained',m=JSON.parse(fs.readFileSync(base+folder+'manifest.json'));
const nodes=new Map(),stages=[];
class El{constructor(){this.children=[];this.value='';this.style={}}append(...x){this.children.push(...x)}}
for(const [,id]of fs.readFileSync(base+page+'.html','utf8').matchAll(/\bid="([^"]+)"/g))nodes.set('#'+id,new El());
nodes.get('#speed').value='1';
const context=vm.createContext({stepCountAt,taskStatesAt,comparisonEvidence,taskNames,activityAt,console,performance,Response,Blob,DecompressionStream,TextDecoder,Uint8Array,URLSearchParams,location:{search:''},
 requestAnimationFrame(fn){context.tick=fn;context.renderScheduled=true},document:{querySelector(q){assert(nodes.has(q),q);return nodes.get(q)},createElement(){return new El()}},
 fetch:async path=>fs.existsSync(base+path)?new Response(fs.readFileSync(base+path)):new Response('',{status:404}),
 createCurriculumStage(el,options){let stage={options,ready:Promise.resolve(),setEpisode(e){this.episode=e},view(){},inspect(){},frame(t){this.time=t;return this.episode.trajectory.frames.findLast(f=>f.t<=t)||this.episode.trajectory.frames[0]}};stages.push(stage);return stage}
});
vm.runInContext(fs.readFileSync(base+page+'.js','utf8').replace(/^import[^\n]+\n/gm,''),context);
async function settle(){for(let i=0;i<1000;i++){await new Promise(r=>setTimeout(r,10));if(context.renderScheduled&&!vm.runInContext('loading',context))return}throw Error('Checkpoint viewer did not load')}
await settle();
assert.equal(stages.length,2);
context.tick(performance.now()-1000);
assert(parseFloat(nodes.get('#time').textContent)>=0,'A stale animation timestamp must not reverse the replay clock');
for(const scenario of m.scenarios){
 if(scenario.partition==='held_out_pending')assert.equal(m.selection_finalized,true);
 await nodes.get('#scenario').onchange({target:{value:scenario.id}});await settle();
 for(let i=0;i<scenario.versions.length;i++){
  nodes.get('#checkpoint').value=i;await nodes.get('#checkpoint').oninput();await settle();
  const [a,b]=stages.map(s=>s.episode),v=scenario.versions[i],meta=m.recordings[v.file];
  assert.equal(a.scenario.seed,b.scenario.seed);assert.deepEqual(a.trajectory.frames[0],b.trajectory.frames[0]);
  assert.equal(a.maximum_applied_base_force,0);assert.equal(b.maximum_applied_base_force,0);assert.equal(a.steps.attempts,a.step_events.length);assert.equal(b.steps.attempts,b.step_events.length);
  assert.match(meta.checkpoint_id,/^[0-9a-f]{64}$/);assert.equal(meta.checkpoint_update,v.update);
  assert.equal(nodes.get('#right-id').textContent,meta.checkpoint_id.slice(0,12));
  const nativeEnd=Math.floor(+nodes.get('#scrub').max/.02)*.02;
  nodes.get('#scrub').oninput({target:{value:nativeEnd}});context.tick(performance.now()+100);
  assert.equal(stages[0].time,a.duration);assert.equal(stages[1].time,b.duration);
  assert.equal(+nodes.get('#left-steps').textContent,a.steps.attempts);assert.equal(+nodes.get('#right-steps').textContent,b.steps.attempts);
  assert.equal(+nodes.get('#right-elapsed').textContent,+b.duration.toFixed(1));
  for(const state of taskStatesAt(b,b.duration))assert.equal(nodes.get('#right-task-'+state.task).className,'task-state '+state.status);
 }
}
assert.equal(nodes.get('#scenario').children.length,m.scenarios.length);
assert(m.optimizer_updates_completed>0);if(m.held_out)assert.equal(m.held_out.parent.n,m.held_out.selected.n);else{assert.equal(m.evaluation_status,'development_preview');assert.equal(m.selection_finalized,Boolean(JSON.parse(fs.readFileSync(base+folder+'report.json')).selected_checkpoint));assert.match(nodes.get('#test-table').children[0].textContent,/pending/)}
for(const file of Object.keys(m.recordings))assert(gunzipSync(fs.readFileSync(base+folder+file)).length>0);
console.log('V15 passed: actual checkpoint IDs, every available recorded version and scenario, gzip loading, synchronized full episodes, identical initial states and preserved failures. WebGL rendering is not tested.');
