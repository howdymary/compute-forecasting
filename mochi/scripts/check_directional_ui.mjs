import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const base='mochi/web/desk/',folder='directional-v14/',manifest=JSON.parse(fs.readFileSync(base+folder+'manifest.json'));
const nodes=new Map(),stages=[];
class El{constructor(){this.children=[];this.value='';this.style={}}append(...x){this.children.push(...x)}replaceChildren(...x){this.children=[...x]}}
for(const [,id]of fs.readFileSync(base+'directional.html','utf8').matchAll(/\bid="([^"]+)"/g))nodes.set('#'+id,new El());
nodes.get('#speed').value='1';
const context=vm.createContext({console,performance,Response,DecompressionStream,URLSearchParams,location:{search:''},
 requestAnimationFrame(fn){context.tick=fn;context.scheduled=true},document:{querySelector(q){assert(nodes.has(q),q);return nodes.get(q)},createElement(){return new El()}},
 fetch:async path=>fs.existsSync(base+path)?new Response(fs.readFileSync(base+path)):new Response('',{status:404}),
 createCurriculumStage(el,options){const stage={options,ready:Promise.resolve(),setEpisode(e){this.episode=e},view(){},topDown(){},frame(t){this.time=t;return this.episode.trajectory.frames.findLast(f=>f.t<=t)||this.episode.trajectory.frames[0]}};stages.push(stage);return stage}
});
vm.runInContext(fs.readFileSync(base+'directional.js','utf8').replace(/^import[^\n]+\n/,''),context);
async function settle(){for(let i=0;i<1000;i++){await new Promise(r=>setTimeout(r,10));if(context.scheduled&&!vm.runInContext('loading',context))return}throw Error('Navigation viewer did not load')}
await settle();
assert.equal(stages.length,2);
for(const row of manifest.cases){
 await nodes.get('#case').onchange({target:{value:row.id}});await settle();
 const [a,b]=stages.map(s=>s.episode);
 assert.equal(a.scenario.seed,b.scenario.seed);assert.deepEqual(a.scene,b.scene);
 assert.deepEqual(a.trajectory.frames[0].positions,b.trajectory.frames[0].positions);
 assert.deepEqual(a.trajectory.frames[0].quaternions,b.trajectory.frames[0].quaternions);
 for(const [i,side]of ['before','after'].entries()){
  const bytes=fs.readFileSync(base+folder+row[side].file),e=JSON.parse(gunzipSync(bytes));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),row[side].sha256);
  assert.equal(e.maximum_applied_base_force,0);assert.equal(e.fall,false);assert.equal(e.invalid_contact,false);
  if(row.id==='four-tasks')for(const task of ['alarm','drawer','laptop','globe'])assert.equal(e.results[task].success,true);
  nodes.get('#scrub').oninput({target:{value:3}});context.tick(performance.now()+50);assert.equal(stages[i].time,3);
 }
 nodes.get('#scrub').oninput({target:{value:nodes.get('#scrub').max}});context.tick(performance.now()+100);
 assert.equal(stages[0].time,a.duration);assert.equal(stages[1].time,b.duration);
 assert(nodes.get('#jumps').children.length>1,'Missing recorded physical turn');
}
assert.equal(nodes.get('#case').children.length,manifest.cases.length);
console.log('Passed: actual gzip recordings and hashes, identical physical starts, zero base support, verified outcomes, recorded turns, scenario switching and synchronized playback. WebGL rendering requires separate visual inspection.');
