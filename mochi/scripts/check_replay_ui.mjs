import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';import {performance} from 'node:perf_hooks';
const archived=process.argv.includes('--archive-v7');const manifest=JSON.parse(fs.readFileSync('mochi/web/desk/curriculum/'+(archived?'manifest-v7.json':'manifest.json'),'utf8'));
const html=fs.readFileSync('mochi/web/desk/curriculum.html','utf8'),nodes=new Map(),created=[],stages=[];
class El{constructor(tag='div'){this.tagName=tag;this.children=[];this.style={};this.dataset={};this.value='';this.textContent='';this.classList={toggle(){}};created.push(this)}append(...els){this.children.push(...els);if(this.tagName==='select'&&!this.value&&els[0])this.value=els[0].value}replaceChildren(...els){this.children=els}setAttribute(k,v){this[k]=v}}
for(const [,tag,id]of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g))nodes.set('#'+id,new El(tag));
for(const q of ['.viewport','.mode','.evidence article:first-child a'])nodes.set(q,new El());
for(const [,task]of html.matchAll(/data-task="([^"]+)"/g)){const e=new El('li');e.dataset.task=task}
nodes.get('#speed').value='1';
const document={querySelector(q){assert(nodes.has(q),'Missing DOM element '+q);return nodes.get(q)},querySelectorAll(q){return created.filter(e=>q==='[data-update]'?e.dataset.update!==undefined:q==='[data-task]'?e.dataset.task!==undefined:false)},createElement(tag){return new El(tag)}};
const context=vm.createContext({location:{search:archived?'?study=v7':''},document,console,performance,URL,setInterval(){},requestAnimationFrame(fn){context.nextFrame=fn},fetch:async path=>({ok:true,json:async()=>path.startsWith('/api/')?{status:'running',phase:'Test harness'}:JSON.parse(fs.readFileSync('mochi/web/desk/'+path,'utf8'))}),createCurriculumStage(){const s={ready:Promise.resolve(),setEpisode(e){this.episode=e},view(){},inspect(kind){this.inspection=kind},frame(t){return this.episode?.trajectory.frames.findLast(f=>f.t<=t)||this.episode?.trajectory.frames[0]}};stages.push(s);return s}});
vm.runInContext(fs.readFileSync('mochi/web/desk/curriculum.js','utf8').replace(/^import[^\n]+\n/,''),context);
const settle=async()=>{for(let i=0;i<100;i++){await new Promise(r=>setImmediate(r));if(stages[0]?.episode&&!vm.runInContext('loading',context))return}throw Error('UI did not finish loading')};
await settle();
assert.equal(stages[0].episode.scenario.seed,manifest.default_view==='checkpoints'?manifest.development_seed:(manifest.showcase?.seed??manifest.development_seed));
assert.equal(nodes.get('#checkpoints').children.length,manifest.checkpoints.length);
assert.equal(nodes.get('#case-results').children.length,manifest.fresh.cases.length);
assert.equal(nodes.get('#evaluation-rows').children.length,3+(manifest.study==='mochi-control-v8'?2:0)+(manifest.held_out_isolated_contact?4:0)+(manifest.held_out_isolated_walking?1:0)+(manifest.isolated_control?1:0));
assert.equal(nodes.get('#memory-handoffs').children.length,manifest.memory_handoffs?.length??0);
context.nextFrame(performance.now()+100);assert(nodes.get('#live-phase').textContent.length>0);
for(const cp of manifest.checkpoints){
 nodes.get('#checkpoints').children.find(b=>b.dataset.update===cp.update).onclick();await settle();
 assert.equal(stages[0].episode.scenario.seed,manifest.development_seed);
 assert.match(nodes.get('#candidate-label').textContent,new RegExp('UPDATE '+cp.update+'$'));
 const expected=JSON.parse(fs.readFileSync('mochi/web/desk/curriculum/'+cp.file,'utf8'));
 assert.equal(stages[0].episode.duration,expected.duration);
 if(cp.trace_file)assert.equal(nodes.get('#model-trace').href,'curriculum/'+cp.trace_file);
}
for(const pair of manifest.fresh.cases){
 nodes.get('#scenario').value=String(pair.seed);nodes.get('#fresh').onclick();await settle();
 assert.equal(stages[0].episode.scenario.seed,pair.seed);
 assert.equal(stages[1].episode.scenario.seed,pair.seed);
 if(pair.after_trace)assert.equal(nodes.get('#model-trace').href,'curriculum/'+pair.after_trace);
 assert.deepEqual(stages[0].episode.trajectory.frames[0],stages[1].episode.trajectory.frames[0]);
}
nodes.get('#gait').onclick();assert(stages.every(s=>s.inspection==='gait'));
nodes.get('#feet').onclick();assert(stages.every(s=>s.inspection==='feet'));
if(manifest.showcase){nodes.get('#showcase').onclick();await settle();assert.equal(stages[0].episode.scenario.seed,manifest.showcase.seed);if(manifest.study==='mochi-curriculum-v7')assert.equal(stages[0].episode.full_sequence_verified,true)}
console.log('Passed: '+manifest.checkpoints.length+' actual checkpoints, '+manifest.fresh.cases.length+' paired test scenarios, measured table, verified-memory display, and shared side/foot camera controls. WebGL rendering is checked separately.');
