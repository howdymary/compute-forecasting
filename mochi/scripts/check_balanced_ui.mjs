import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';

const base='mochi/web/desk/',manifest=JSON.parse(fs.readFileSync(base+'balanced-v11/manifest.json'));
const nodes=new Map(),stages=[];
class El{
 constructor(){this.children=[];this.value='';this.style={}}
 append(...items){this.children.push(...items)}
 replaceChildren(...items){this.children=items}
}
for(const [,id] of fs.readFileSync(base+'balanced.html','utf8').matchAll(/\bid="([^"]+)"/g))nodes.set('#'+id,new El());
nodes.get('#speed').value='1';
const context=vm.createContext({console,performance,setInterval(){},requestAnimationFrame(fn){context.tick=fn},
 document:{querySelector(q){assert(nodes.has(q),q);return nodes.get(q)},createElement(){return new El()}},
 fetch:async path=>({ok:fs.existsSync(base+path),json:async()=>JSON.parse(fs.readFileSync(base+path))}),
 createCurriculumStage(element,options){const stage={options,ready:Promise.resolve(),setEpisode(e){this.episode=e},view(){},frame(t){this.last=t;return this.episode.trajectory.frames.findLast(f=>f.t<=t)||this.episode.trajectory.frames[0]}};stages.push(stage);return stage}
});
vm.runInContext(fs.readFileSync(base+'balanced.js','utf8').replace(/^import[^\n]+\n/,''),context);
async function settle(){for(let i=0;i<200;i++){await new Promise(r=>setImmediate(r));if(context.tick&&!vm.runInContext('loading',context))return}throw Error('UI did not finish loading')}
await settle();
assert.equal(stages.length,2);assert(stages.every(s=>s.options.fullBody));
for(const entry of manifest.attempts.slice(1)){
 await nodes.get('#candidate').onchange({target:{value:entry.id}});await settle();
 const [a,b]=stages.map(s=>s.episode);
 assert.deepEqual(a.trajectory.frames[0],b.trajectory.frames[0]);
 assert.equal(a.maximum_applied_base_force,0);assert.equal(b.maximum_applied_base_force,0);
 nodes.get('#scrub').oninput({target:{value:nodes.get('#scrub').max}});context.tick(performance.now()+100);
 assert.equal(stages[0].last,a.duration);assert.equal(stages[1].last,b.duration);
 assert.match(nodes.get('#scope').textContent,/Controller revisions differ/);
 assert.equal(entry.optimizer_updates_completed,0);
}
assert.equal(manifest.optimizer_updates_completed,0);assert.equal(manifest.training_gate_open,false);
assert.equal(nodes.get('#candidate').children.length,manifest.attempts.length-1);
console.log('Passed: synchronized full recordings, identical initial frames, evidence links, failure endings, original/trained distinction and camera opt-in. WebGL rendering is not tested.');
