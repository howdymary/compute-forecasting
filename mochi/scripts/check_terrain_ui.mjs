import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {createHash} from 'node:crypto';
const base='mochi/web/desk/',manifest=JSON.parse(fs.readFileSync(base+'terrain-engineering/manifest.json'));
const nodes=new Map();let stage;
class El{constructor(){this.children=[];this.value='';this.style={}}append(...x){this.children.push(...x)}}
for(const [,id]of fs.readFileSync(base+'terrain.html','utf8').matchAll(/\bid="([^"]+)"/g))nodes.set('#'+id,new El());
nodes.get('#speed').value='1';
const context=vm.createContext({console,performance,Response,DecompressionStream,
 requestAnimationFrame(fn){context.tick=fn;context.renderScheduled=true},setInterval(){},
 document:{querySelector(q){assert(nodes.has(q),q);return nodes.get(q)},createElement(){return new El()}},
 fetch:async path=>path.startsWith('api/')?Response.json({optimizer_updates_completed:0,phase:'Physical reference passed; queued for training'}):new Response(fs.readFileSync(base+path)),
 createCurriculumStage(){stage={ready:Promise.resolve(),setEpisode(e){this.episode=e},view(){},inspect(){},frame(t){return this.episode.trajectory.frames.findLast(f=>f.t<=t)||this.episode.trajectory.frames[0]}};return stage}
});
vm.runInContext(fs.readFileSync(base+'terrain.js','utf8').replace(/^import[^\n]+\n/,''),context);
for(let i=0;!context.renderScheduled&&i<1000;i++)await new Promise(r=>setTimeout(r,10));
assert(context.renderScheduled,'Viewer did not load');
const e=stage.episode;
assert(manifest.complete);assert.equal(e.maximum_applied_base_force,0);assert(!e.invalid_contact&&!e.fall);
assert.equal(Object.values(e.results).filter(r=>r.success).length,4);assert.equal(e.recoveries.filter(r=>r.success).length,4);
assert(e.events.some(x=>x.label==='book-ascent'&&x.success&&x.dwell_s>=.4));
assert(e.events.some(x=>x.label==='book-descent'&&x.success&&x.dwell_s>=.4));
assert.equal(createHash('sha256').update(fs.readFileSync(base+'terrain-engineering/'+manifest.file)).digest('hex'),manifest.sha256);
assert.equal(nodes.get('#jumps').children.length,5);
nodes.get('#scrub').oninput({target:{value:e.duration}});context.tick(performance.now());
assert.equal(nodes.get('#outcome').textContent,'All four tasks verified');
assert(nodes.get('#tasks').children.every(n=>n.textContent.startsWith('✓')));
assert.match(nodes.get('#training-updates').textContent,/0 completed/);
console.log('Passed: real full sequence, book dwell, four tasks and recoveries, gzip provenance, timeline, task outcomes and separate training status. WebGL rendering is not covered.');
